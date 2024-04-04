"""Entry point for the clockify-sync interactive CLI."""

import datetime
import os
import sys

from src.api import main as clockify_api
from src.util.setup_logger import setup_logger
from src.util import cli

logger = setup_logger()


def get_config(src_auth_token, dest_auth_token):
    """Get configuration for syncing projects and time entries between two Clockify workspaces."""

    src_auth_header = clockify_api.get_auth_header(src_auth_token)
    dest_auth_header = clockify_api.get_auth_header(dest_auth_token)
    src_user = clockify_api.get_currently_logged_in_user(src_auth_header)
    dest_user = clockify_api.get_currently_logged_in_user(dest_auth_header)

    src_workspaces = clockify_api.get_workspaces(src_auth_header)
    src_workspace = cli.select_named_item(src_workspaces, "Select a source workspace: ")

    src_clients = clockify_api.get_clients(src_auth_header, src_workspace["id"])
    src_client = cli.select_named_item(src_clients, "Select a source client: ")

    dest_workspaces = clockify_api.get_workspaces(dest_auth_header)
    dest_workspace = cli.select_named_item(
        dest_workspaces, "Select a destination workspace: "
    )

    if dest_workspace["id"] == src_workspace["id"]:
        logger.error("Source and destination workspaces must be different.")
        sys.exit(1)

    return {
        "src_user": src_user,
        "dest_user": dest_user,
        "src_workspace": src_workspace,
        "src_client": src_client,
        "dest_workspace": dest_workspace,
        "src_auth_header": src_auth_header,
        "dest_auth_header": dest_auth_header,
    }


def main():
    """Sync projects and time entries between two Clockify workspaces interactively."""

    src_auth_token = os.getenv("SRC_CLOCKIFY_API_KEY")
    dest_auth_token = os.getenv("DEST_CLOCKIFY_API_KEY")

    if not src_auth_token:
        logger.error(
            "Source auth token is required."
            + " Specify it with the environment variable SRC_CLOCKIFY_API_KEY"
        )
        return

    if not dest_auth_token:
        logger.info(
            "Destination auth token not specified."
            + " Using source auth token as destination auth token."
        )
        dest_auth_token = src_auth_token

    config = get_config(src_auth_token, dest_auth_token)

    if cli.prompt_yes_no(
        f"Sync projects from workspace {config['dest_workspace']['name']}"
        + f" to client {config['src_client']['name']} in {config['src_workspace']['name']}?"
    ):
        clockify_api.sync_projects(
            src_auth_header=config["dest_auth_header"],
            dest_auth_header=config["src_auth_header"],
            src_workspace_id=config["dest_workspace"]["id"],
            dest_workspace_id=config["src_workspace"]["id"],
            dest_workspace_client_id=config["src_client"]["id"],
        )

    if cli.prompt_yes_no(
        f"Sync time entries for user {config['src_user']['name']}"
        + f" and client {config['src_client']['name']}"
        + f" in {config['src_workspace']['name']} to {config['dest_workspace']['name']}?"
    ):
        default_start_date = (
            datetime.datetime.now() - datetime.timedelta(days=1)
        ).isoformat(timespec="seconds") + "Z"
        default_end_date = datetime.datetime.now().isoformat(timespec="seconds") + "Z"

        start_date = cli.prompt_date(default_start_date, "Enter a start date")
        end_date = cli.prompt_date(default_end_date, "Enter an end date")

        logger.info("Syncing time entries from %s to %s...", start_date, end_date)

        clockify_api.sync_time_entries(
            src_auth_header=config["src_auth_header"],
            dest_auth_header=config["dest_auth_header"],
            src_workspace_id=config["src_workspace"]["id"],
            src_workspace_client_id=config["src_client"]["id"],
            src_user_id=config["src_user"]["id"],
            dest_user_id=config["dest_user"]["id"],
            dest_workspace_id=config["dest_workspace"]["id"],
            start_date=start_date,
            end_date=end_date,
        )


if __name__ == "__main__":
    main()
