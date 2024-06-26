"""
Main module for the Clockify API.

Simple library for interacting with the Clockify API.
"""

from typing import Optional, Dict, List
from copy import deepcopy
import json
import logging

import requests

logger = logging.getLogger(__name__)


def get_auth_header(api_key):
    """Create an auth header for the Clockify API."""

    return {"X-Api-Key": api_key}


def get_workspaces(auth_header):
    """Get all workspaces for the currently logged in user."""

    url = "https://api.clockify.me/api/v1/workspaces"

    return get_request(url=url, auth_header=auth_header)


def get_clients(auth_header, workspace_id):
    """Get all clients in a workspace."""

    url = f"https://api.clockify.me/api/v1/workspaces/{workspace_id}/clients"

    return get_request(url=url, auth_header=auth_header)


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
    src_workspace_id,
    src_auth_header,
    dest_auth_header,
    dest_workspace_id,
    dest_workspace_client_id,
):
    """Get projects that are missing in the destination workspace."""

    dest_projects_for_client = get_all_projects(
        dest_workspace_id, dest_auth_header, dest_workspace_client_id
    )

    dest_projects_for_client_names = [
        project["name"] for project in dest_projects_for_client
    ]

    all_src_projects = get_all_projects(src_workspace_id, src_auth_header)

    return [
        project
        for project in all_src_projects
        if project["name"] not in dest_projects_for_client_names
    ]


def sync_projects(
    src_auth_header,
    src_workspace_id,
    dest_workspace_id,
    dest_workspace_client_id,
    dest_auth_header=None,
    project_options: Optional[Dict] = None,
):
    """Sync projects from one workspace to another."""

    if not dest_auth_header:
        dest_auth_header = src_auth_header

    dest_workspace_missing_projects = get_missing_projects(
        src_auth_header=src_auth_header,
        src_workspace_id=src_workspace_id,
        dest_auth_header=dest_auth_header,
        dest_workspace_id=dest_workspace_id,
        dest_workspace_client_id=dest_workspace_client_id,
    )

    if len(dest_workspace_missing_projects) == 0:
        logger.info("All projects are already synced!")
        return

    for project in dest_workspace_missing_projects:
        new_project = copy_dict_keys(src_dict=project, dest_dict={}, keys=["name"])
        new_project["clientId"] = dest_workspace_client_id

        if project_options:
            new_project = copy_dict_keys(
                src_dict=project_options,
                dest_dict=new_project,
                keys=["color"],
            )

        add_new_project(
            dest_workspace_id,
            new_project,
            dest_auth_header,
        )

    dest_projects_for_client_updated = get_all_projects(
        dest_workspace_id, dest_auth_header, dest_workspace_client_id
    )

    dest_projects_for_client_updated_names = [
        project["name"] for project in dest_projects_for_client_updated
    ]

    for project in dest_workspace_missing_projects:
        if project["name"] not in dest_projects_for_client_updated_names:
            raise RuntimeError(
                f"Project \"{project['name']}\" was not added correctly!"
            )


def sync_time_entries(
    src_auth_header,
    src_user_id,
    src_workspace_id,
    src_workspace_client_id,
    start_date,
    end_date,
    dest_workspace_id,
    dest_user_id=None,
    dest_auth_header=None,
):
    """Sync time entries from one workspace to another."""

    if not dest_auth_header:
        dest_auth_header = src_auth_header
    if not dest_user_id:
        dest_user_id = src_user_id

    src_time_entries = get_user_time_entries(
        src_user_id, src_workspace_id, start_date, end_date, src_auth_header
    )

    src_client_projects = get_all_projects(
        workspace_id=src_workspace_id,
        client_id=src_workspace_client_id,
        auth_header=src_auth_header,
    )

    src_project_ids_for_client = [project["id"] for project in src_client_projects]

    dest_current_time_entries = get_user_time_entries(
        user_id=dest_user_id,
        workspace_id=dest_workspace_id,
        start_date=start_date,
        end_date=end_date,
        auth_header=dest_auth_header,
    )

    hashed_dest_time_entries = [
        hash_time_entry(entry) for entry in dest_current_time_entries
    ]

    # Filter out time entries that are not for the client
    # or already in the destination workspace
    missing_time_entries = [
        entry
        for entry in src_time_entries
        if entry["projectId"] in src_project_ids_for_client
        and hash_time_entry(entry) not in hashed_dest_time_entries
    ]

    logger.info("Found %i missing time entries!", len(missing_time_entries))

    if len(missing_time_entries) == 0:
        logger.info("All time entries are already synced!")
        return

    dest_projects = get_all_projects(
        workspace_id=dest_workspace_id, auth_header=dest_auth_header
    )

    src_to_dest_project_map = map_src_to_dest_project_ids(
        src_client_projects=src_client_projects,
        dest_projects=dest_projects,
    )

    for entry in missing_time_entries:
        try:
            formatted_entry = {
                "projectId": src_to_dest_project_map[entry["projectId"]],
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
        add_new_time_entry(formatted_entry, dest_workspace_id, dest_auth_header)


def map_src_to_dest_project_ids(src_client_projects, dest_projects):
    """Map source project ids to destination project ids."""

    dest_project_map = {}
    for project in dest_projects:
        dest_project_map[project["name"]] = project["id"]

    src_to_dest_project_map = {}
    for project in src_client_projects:
        try:
            src_to_dest_project_map[project["id"]] = dest_project_map[project["name"]]
        except KeyError:
            logger.error(
                "Project '%s' was not found in the destination workspace!",
                project["name"],
            )
            continue

    return src_to_dest_project_map


def hash_time_entry(entry):
    """Hash a time entry."""

    return hash(
        (
            entry["timeInterval"]["start"],
            entry["timeInterval"]["end"],
            entry["description"],
        )
    )


def copy_dict_keys(src_dict: Dict, dest_dict, keys: List[str]):
    """Copy keys from one dict to another."""
    for key in keys:
        dest_dict[key] = deepcopy(src_dict[key])

    return dest_dict
