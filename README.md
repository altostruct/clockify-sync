# Clockify sync
This is a simple lambda function that syncs time entries bewteen two Clockify workspaces using the Clockify API.
It is designed to sync time entries from one workspace where time entries are created under a single client to another workspace where time entries can be created under multiple clients.

## How it works
1. Projects are first synced from the desitination workspace to the source workspace. Any projects that do not exist in the source workspace are created under the specified client.
2. A mapping of project IDs is created between the source and destination workspaces so that time entries can be synced to the correct project.
3. Time entries are synced from the source workspace to the destination workspace. Time entries are only synced if they have not already been synced. Time entries are synced to the project that has the same name as the project in the source workspace.

## Usage
A cloudformation template is provided in the [cloudformation](/cloudformation/) directory. The template creates a lambda function and an event rule that triggers the lambda function every day. It also creates a SNS topic that is used to send error messages from the lambda function if syncing fails.

### Confguration
The lambda function is configured using environment variables. The following environment variable is required:

`SECRET_NAMES=you_secret_name1,your_secret_name2`

The AWS secrets should contain the configuration for a sync.

This is what should be included in the secret:

```py
{
    #---Required---
    # The id of the source workspace where time entries should be synced from
    "time_entry_source_workspace_id": "your_source_workspace_id",
    # The id of the client that projects should be created under in the source workspace
    "time_entry_source_client_id": "your_client_id",
    # The id of the destination workspace where time entries should be synced to
    "time_entry_destination_workspace_id": "your_destination_workspace_id",
    # The id of the user that time entries should be synced for
    "user_id": "your_user_id",
    # The token giving access for the user whose time entries should be synced
    "token": "your_token",

    #---Optional---
    # Project options available in the clockify API. For example: {"color":"#00FFFF"}
    "project_options":"{\"color\":\"#00FFFF\"}",
    # If the time entries should be synced to a different user in the destination workspace, provide the user id and token of that user.
    # If not provided, the time entries will be synced to the user with the same id as the source user.
    "dest_token": "your_destination_token",
    "dest_user_id": "your_destination_user_id",
}
```
The token can be created on the [Clockify profile page](https://app.clockify.me/user/settings).

### Dependencies
The following dependencies are required to deploy the application:
- [AWS CLI](https://aws.amazon.com/cli/)
- [Docker](https://www.docker.com/)

### Deploying the cloudfomation template
A bash script is provided to deploy the cloudformation template, [/cloudformation/deploy.sh](/cloudformation/deploy.sh).
Two stacks are created, one for the lambda function and one for the ECR repository, which will hold the images.

The script requires some parameters to be passed in:
1. `cd cloudformation`
2. `./deploy.sh <AWS_PROFILE> <AWS_REGION> <STACK_NAME> <SECRET_NAMES>`

Parameters:
```
AWS_PROFILE: The name of the configured AWS profile to use
AWS_REGION: The AWS region to deploy the stack to
STACK_NAME: The name of the stack to create
SECRET_NAMES: A comma separated list of AWS secrets to use
```

### Deploying the application
A bash script is provided to deploy the application, [/scripts/deploy.sh](/scripts/deploy.sh).
The docker image is built and pushed to ECR and the lambda function is updated with the new image.

The script requires some parameters to be passed in:
`./scripts/deploy.sh <AWS_PROFILE> <AWS_REGION>`

## How to contribute
Read our documentation on how to contribute in our [contibution guidelines](/CONTRIBUTING.md)

## Code of conduct
[Rules and code of conduct](/CODE_OF_CONDUCT.md) must be followed.
