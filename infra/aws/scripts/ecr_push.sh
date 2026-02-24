#!/usr/bin/env bash
set -euo pipefail

# Build + push images to ECR.
# Run from repo root: /Users/rishi/Desktop/comply-pivot/agentic_system

AWS_REGION="${AWS_REGION:-us-east-1}"
APP="${APP:-comply-ai}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
ECR="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${ECR}"

for r in web core-api core-worker connector; do
  aws ecr describe-repositories --region "${AWS_REGION}" --repository-names "${APP}/${r}" >/dev/null 2>&1 \
    || aws ecr create-repository \
      --region "${AWS_REGION}" \
      --repository-name "${APP}/${r}" \
      --image-scanning-configuration scanOnPush=true \
      --encryption-configuration encryptionType=AES256 >/dev/null
done

docker build -f apps/web/Dockerfile.prod -t "${APP}-web:${IMAGE_TAG}" .
docker build -f apps/core-api/Dockerfile.prod -t "${APP}-core-api:${IMAGE_TAG}" .
docker build -f apps/core-worker/Dockerfile -t "${APP}-core-worker:${IMAGE_TAG}" .
docker build -f apps/connector/Dockerfile.prod -t "${APP}-connector:${IMAGE_TAG}" .

docker tag "${APP}-web:${IMAGE_TAG}" "${ECR}/${APP}/web:${IMAGE_TAG}"
docker tag "${APP}-core-api:${IMAGE_TAG}" "${ECR}/${APP}/core-api:${IMAGE_TAG}"
docker tag "${APP}-core-worker:${IMAGE_TAG}" "${ECR}/${APP}/core-worker:${IMAGE_TAG}"
docker tag "${APP}-connector:${IMAGE_TAG}" "${ECR}/${APP}/connector:${IMAGE_TAG}"

docker push "${ECR}/${APP}/web:${IMAGE_TAG}"
docker push "${ECR}/${APP}/core-api:${IMAGE_TAG}"
docker push "${ECR}/${APP}/core-worker:${IMAGE_TAG}"
docker push "${ECR}/${APP}/connector:${IMAGE_TAG}"

echo "Pushed:"
echo "  ${ECR}/${APP}/web:${IMAGE_TAG}"
echo "  ${ECR}/${APP}/core-api:${IMAGE_TAG}"
echo "  ${ECR}/${APP}/core-worker:${IMAGE_TAG}"
echo "  ${ECR}/${APP}/connector:${IMAGE_TAG}"

