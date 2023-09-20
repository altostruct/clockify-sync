#!/bin/bash
# Create the ECR repo stack and the lambda stack
set -e

if [ -z "$1" ]; then
    echo "No AWS_PROFILE supplied"
    exit 1
fi

if [ -z "$2" ]; then
    echo "No AWS_REGION supplied"
    exit 1
fi

if [ -z "$3" ]; then
    echo "No STACK_NAME supplied"
    exit 1
fi

if [ -z "$4" ]; then
    echo "No SECRET_NAMES supplied"
    exit 1
fi

AWS_PROFILE=$1
AWS_REGION=$2
STACK_NAME=$3
SECRET_NAMES=$4

S3_CODE_BUCKET="clockify-sync-cloudformation"

ECR_FILE="ecr"
ECR_STACK_NAME="$STACK_NAME-ecr"

echo "Deploying $ECR_STACK_NAME..."
aws cloudformation package --template ./$ECR_FILE.yml --s3-prefix stacks --profile $AWS_PROFILE --s3-bucket $S3_CODE_BUCKET >./$ECR_FILE.g.yml

aws cloudformation deploy --region $AWS_REGION \
    --template-file ./$ECR_FILE.g.yml \
    --stack-name $ECR_STACK_NAME \
    --profile $AWS_PROFILE \
    --s3-bucket $S3_CODE_BUCKET \
    --parameter-overrides secretNames=$SECRET_NAMES \
    --capabilities CAPABILITY_NAMED_IAM
echo "Deployed $ECR_STACK_NAME"

# Push empty image to ECR, so that we can create the lambda function pointing to it
ACCOUNT_ID=$(aws sts get-caller-identity --profile $AWS_PROFILE --query Account | tr -d '"')
ECR_REPO=$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/clockify-sync-lambda:latest

if [ -z $(docker image inspect $ECR_REPO | grep $ECR_REPO) ]; then
    echo "Image not found in ECR, creating empty image..."
    aws ecr get-login-password --profile $AWS_PROFILE --region $AWS_REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

    docker buildx build --platform=linux/arm64 -t clockify-sync-lambda ./empty-docker-image

    docker tag clockify-sync-lambda:latest $ECR_REPO

    docker push $ECR_REPO
    echo "Done building and pushing empty image to ECR"
else
    echo "Image found in ECR, skipping build"
fi

echo "Deploying $STACK_NAME..."
LAMBDA_FILE="lambda"
aws cloudformation package --template ./$LAMBDA_FILE.yml --s3-prefix stacks --profile $AWS_PROFILE --s3-bucket $S3_CODE_BUCKET >./$LAMBDA_FILE.g.yml

aws cloudformation deploy --region $AWS_REGION \
    --template-file ./$LAMBDA_FILE.g.yml \
    --stack-name $STACK_NAME \
    --profile $AWS_PROFILE \
    --s3-bucket $S3_CODE_BUCKET \
    --parameter-overrides secretNames=$SECRET_NAMES \
    --capabilities CAPABILITY_NAMED_IAM
echo "Deployed $STACK_NAME"
