"""Lambda handler to sync time entries and projects between workspaces"""

import datetime
import traceback
import os
import json
from typing import List, Dict

import boto3

from src.api.main import sync_projects, sync_time_entries
from src.util.setup_logger import setup_logger

ERROR_SNS_TOPIC_ARN = os.getenv("ERROR_SNS_TOPIC_ARN")

if ERROR_SNS_TOPIC_ARN:
    sns_client = boto3.client("sns")

secrets_manager_client = boto3.client("secretsmanager")

logger = setup_logger()


def handle_error(message):
    """Log error and publish to SNS if configured"""
    logger.error(message, traceback.print_exc())

    if ERROR_SNS_TOPIC_ARN:
        sns_client.publish(
            TopicArn=ERROR_SNS_TOPIC_ARN,
            Message=message,
        )


def get_secret_names() -> List[str]:
    """Get secret names from environment variable"""
    secret_names = os.getenv("SECRET_NAMES", "").split(",")

    if not secret_names:
        return []

    return secret_names


def get_secret(secret_name: str) -> Dict:
    """Get and parse secret data from AWS Secrets Manager"""
    secret = secrets_manager_client.get_secret_value(SecretId=secret_name)

    secret_data = json.loads(secret["SecretString"])

    return secret_data


SYNC_START_DATE = (datetime.datetime.utcnow() - datetime.timedelta(days=1)).isoformat(
    timespec="seconds"
) + "Z"

SYNC_END_DATE = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def handler(_event, _context):
    """Lambda handler to sync time entries and projects between workspaces"""

    logger.info("Starting sync between %s and %s", SYNC_START_DATE, SYNC_END_DATE)

    secret_names = get_secret_names()

    if not secret_names:
        raise ValueError(
            "No secret names provided in SECRET_NAMES environment variable"
        )

    for secret_name in secret_names:
        secret = get_secret(secret_name)

        if not secret:
            raise ValueError(f"Missing secret with name {secret_name}")

        time_entry_src_auth_header = {"X-Api-Key": secret["token"]}
        try:
            time_entry_dest_auth_header = {"X-Api-Key": secret["dest_token"]}
        except KeyError:
            time_entry_dest_auth_header = time_entry_src_auth_header

        project_options_string = secret.get("project_options", None)
        if project_options_string:
            project_options = json.loads(project_options_string)

        logger.info("Syncing projects for secret %s...", secret_name)
        logger.debug("Using project options: %s", project_options)
        try:
            sync_projects(
                src_auth_header=time_entry_dest_auth_header,
                dest_workspace_id=secret["time_entry_source_workspace_id"],
                dest_workspace_client_id=secret["time_entry_source_client_id"],
                src_workspace_id=secret["time_entry_destination_workspace_id"],
                project_options=project_options,
                dest_auth_header=time_entry_src_auth_header,
            )
        except Exception:
            handle_error(f"Failed to sync projects for secret {secret_name}.")
            continue

        logger.info("Done syncing projects for secret %s", secret_name)

        logger.info("Syncing time entries for secret %s...", secret_name)
        try:
            sync_time_entries(
                src_auth_header=time_entry_src_auth_header,
                src_workspace_client_id=secret["time_entry_source_client_id"],
                src_workspace_id=secret["time_entry_source_workspace_id"],
                src_user_id=secret["user_id"],
                start_date=SYNC_START_DATE,
                dest_user_id=secret.get("dest_user_id"),
                end_date=SYNC_END_DATE,
                dest_workspace_id=secret["time_entry_destination_workspace_id"],
                dest_auth_header=time_entry_dest_auth_header,
            )
        except Exception:
            handle_error(f"Failed to sync time entries for secret {secret_name}.")
            continue

        logger.info("Done syncing time entries for secret %s", secret_name)
