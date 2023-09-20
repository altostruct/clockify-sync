"""
Main module for the Clockify API.

Simple library for interacting with the Clockify API.
"""
from typing import Optional, Dict, List
import json
import logging

import requests

logger = logging.getLogger(__name__)


def get_currently_logged_in_user(auth_header):
    """Get the currently logged in user."""

    url = "https://api.clockify.me/api/v1/user"

    return get_request(url=url, auth_header=auth_header)


def get_user_time_entries(user_id, workspace_id, start_date, end_date, auth_header):
    """Get all time entries for a user in a workspace between two dates."""

    query_params = f"start={start_date}&end={end_date}&in-progress=false"
    url = (
        f"https://api.clockify.me/api/v1/workspaces/{workspace_id}/user/{user_id}/time-entries"
        + f"?{query_params}"
    )

    return get_request(url=url, auth_header=auth_header)


def add_new_time_entry(entry, workspace_id, auth_header):
    """Add a new time entry to a workspace."""

    url = f"https://api.clockify.me/api/v1/workspaces/{workspace_id}/time-entries"

    return post_request(url=url, data=entry, auth_header=auth_header)


def get_all_clients(workspace_id, auth_header):
    """Get all clients in a workspace."""

    url = f"https://api.clockify.me/api/v1/workspaces/{workspace_id}/clients"

    return get_request(url=url, auth_header=auth_header)


def get_all_projects(workspace_id, auth_header, client_id=None):
    """Get all projects in a workspace."""

    query_params = ""
    if client_id:
        query_params = f"clients={client_id}"

    url = f"https://api.clockify.me/api/v1/workspaces/{workspace_id}/projects?{query_params}"

    return get_request(url=url, auth_header=auth_header)


def add_new_project(workspace_id, project, auth_header):
    """Add a new project to a workspace."""

    url = f"https://api.clockify.me/api/v1/workspaces/{workspace_id}/projects"

    return post_request(url=url, auth_header=auth_header, data=project)


def post_request(url, data, auth_header):
    """Make a POST request to the Clockify API."""

    headers = auth_header.copy()
    headers["Content-Type"] = "application/json"

    result = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)

    if not result.ok:
        logger.error(result.json())
        raise RuntimeError(f"Request not ok: {result.status_code} {result.reason}")

    return result.json()


def get_request(url, auth_header):
    """Make a GET request to the Clockify API."""

    result = requests.get(url, headers=auth_header, timeout=30)

    if not result.ok:
        logger.error(result.json())
        raise RuntimeError(f"Request not ok: {result.status_code} {result.reason}")

    return result.json()


def get_missing_projects(
    source_workspace_id,
    destination_workspace_id,
    destination_workspace_client_id,
    auth_header,
):
    """Get projects that are missing in the destination workspace."""

    destination_projects_for_client = get_all_projects(
        destination_workspace_id, auth_header, destination_workspace_client_id
    )

    destination_projects_for_client_names = [
        project["name"] for project in destination_projects_for_client
    ]

    all_source_projects = get_all_projects(source_workspace_id, auth_header)

    return [
        project
        for project in all_source_projects
        if project["name"] not in destination_projects_for_client_names
    ]


def sync_projects(
    source_workspace_id,
    destination_workspace_id,
    destination_workspace_client_id,
    auth_header,
    project_options: Optional[Dict] = None,
):
    """Sync projects from one workspace to another."""

    destination_workspace_missing_projects = get_missing_projects(
        source_workspace_id,
        destination_workspace_id,
        destination_workspace_client_id,
        auth_header,
    )

    if len(destination_workspace_missing_projects) == 0:
        logger.info("All projects are already synced!")
        return

    for project in destination_workspace_missing_projects:
        new_project = copy_dict_keys(
            source_dict=project, destination_dict={}, keys=["name"]
        )
        new_project["clientId"] = destination_workspace_client_id

        new_project = copy_dict_keys(
            source_dict=project_options, destination_dict=new_project, keys=["color"]
        )

        add_new_project(
            destination_workspace_id,
            new_project,
            auth_header,
        )

    destination_projects_for_client_updated = get_all_projects(
        destination_workspace_id, auth_header, destination_workspace_client_id
    )

    destination_projects_for_client_updated_names = [
        project["name"] for project in destination_projects_for_client_updated
    ]

    for project in destination_workspace_missing_projects:
        if project["name"] not in destination_projects_for_client_updated_names:
            raise RuntimeError(
                f"Project \"{project['name']}\" was not added correctly!"
            )


def sync_time_entries(
    user_id,
    source_workspace_id,
    source_workspace_client_id,
    destination_workspace_id,
    start_date,
    end_date,
    auth_header,
):
    """Sync time entries from one workspace to another."""

    source_time_entries = get_user_time_entries(
        user_id, source_workspace_id, start_date, end_date, auth_header
    )

    source_client_projects = get_all_projects(
        workspace_id=source_workspace_id,
        client_id=source_workspace_client_id,
        auth_header=auth_header,
    )

    source_project_ids_for_client = [
        project["id"] for project in source_client_projects
    ]

    destination_current_time_entries = get_user_time_entries(
        user_id=user_id,
        workspace_id=destination_workspace_id,
        start_date=start_date,
        end_date=end_date,
        auth_header=auth_header,
    )

    hashed_destination_time_entries = [
        hash_time_entry(entry) for entry in destination_current_time_entries
    ]

    # Filter out time entries that are not for the client
    # or already in the destination workspace
    missing_time_entries = [
        entry
        for entry in source_time_entries
        if entry["projectId"] in source_project_ids_for_client
        and hash_time_entry(entry) not in hashed_destination_time_entries
    ]

    logger.info("Found %i missing time entries!", len(missing_time_entries))

    if len(missing_time_entries) == 0:
        logger.info("All time entries are already synced!")
        return

    destination_projects = get_all_projects(
        workspace_id=destination_workspace_id, auth_header=auth_header
    )

    source_to_destination_project_map = map_source_to_destination_project_ids(
        source_client_projects=source_client_projects,
        destination_projects=destination_projects,
    )

    for entry in missing_time_entries:
        try:
            formatted_entry = {
                "projectId": source_to_destination_project_map[entry["projectId"]],
                "start": entry["timeInterval"]["start"],
                "end": entry["timeInterval"]["end"],
                "description": entry["description"],
            }
        except KeyError:
            logger.error(
                "Project '%s' was not found in the destination workspace!"
                + " Skipping time entry...",
                entry["projectId"],
            )
            continue
        add_new_time_entry(formatted_entry, destination_workspace_id, auth_header)


def map_source_to_destination_project_ids(source_client_projects, destination_projects):
    """Map source project ids to destination project ids."""

    destination_project_map = {}
    for project in destination_projects:
        destination_project_map[project["name"]] = project["id"]

    source_to_destination_project_map = {}
    for project in source_client_projects:
        try:
            source_to_destination_project_map[project["id"]] = destination_project_map[
                project["name"]
            ]
        except KeyError:
            logger.error(
                "Project '%s' was not found in the destination workspace!",
                project["name"],
            )
            continue

    return source_to_destination_project_map


def hash_time_entry(entry):
    """Hash a time entry."""

    return hash(
        (
            entry["timeInterval"]["start"],
            entry["timeInterval"]["end"],
            entry["description"],
        )
    )


def copy_dict_keys(source_dict: Dict, destination_dict, keys: List[str]):
    """Copy keys from one dict to another."""

    for key in keys:
        destination_dict[key] = source_dict[key].copy()

    return destination_dict
