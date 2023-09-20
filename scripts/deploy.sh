#!/bin/bash
# Build and deploy the docker image to the lambda function
set -e

if [ -z "$1" ]; then
    echo "No AWS_PROFILE supplied"
    exit 1
fi

if [ -z "$2" ]; then
    echo "No AWS_REGION supplied"
    exit 1
fi

AWS_PROFILE=$1
AWS_REGION=$2

ACCOUNT_ID=$(aws sts get-caller-identity --profile $AWS_PROFILE --query Account | tr -d '"')
ECR_REPO=$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/clockify-sync-lambda:latest

echo "Building and pusing image to ECR..."
aws ecr get-login-password --profile $AWS_PROFILE --region $AWS_REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

docker buildx build --platform=linux/arm64 -t clockify-sync-lambda .

docker tag clockify-sync-lambda:latest $ECR_REPO

docker push $ECR_REPO
echo "Done building and pushing image to ECR"

echo "Updating lambda function..."
aws lambda update-function-code --profile $AWS_PROFILE --function-name clockify-sync-lambda --image-uri $ECR_REPO
echo "Done updating lambda function"
