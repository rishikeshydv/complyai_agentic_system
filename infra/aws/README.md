# AWS Deployment (ECR + ECS Fargate + ALB)

This repo has 5 deployable ECS tasks:

- `web` (Next.js) on `:3000`
- `core-api` (FastAPI) on `:8000`
- `core-worker` (Celery worker) no port
- `core-beat` (Celery beat) no port
- `connector` (Bank Connector API) on `:8100` (typically internal-only)

## 0) Prereqs

- AWS CLI configured (`aws sts get-caller-identity` works)
- A VPC with:
  - 2 public subnets (ALB)
  - 2 private subnets (ECS tasks)
  - NAT for private subnets (tasks must reach ECR + CloudWatch)
- CloudWatch Logs available

## 1) Decide networking model

Recommended layout:

- Public ALB routes:
  - `/*` -> `web` target group (`:3000`)
  - `/v1/*` (and optionally `/docs*`) -> `core-api` target group (`:8000`)
- `connector` is **not** public:
  - either runs in same VPC and is reachable only from `core-api` security group
  - or (more realistic) runs in a separate bank-side environment/account and is reachable via private networking + mTLS/signed requests

## 2) Secrets/config (don’t ship `.env` in images)

For ECS:

- Put DB/Redis/ES creds in **Secrets Manager** or **SSM Parameter Store**
- Inject them into each task definition as env vars / secrets

Important: `NEXT_PUBLIC_*` variables are baked into the browser bundle at build-time.
In this repo, prefer routing browser calls through Next.js `/api/...` proxies for runtime flexibility.

## 3) Create ECR repos + push images

Use `infra/aws/scripts/ecr_push.sh`. It builds `Dockerfile.prod` images:

- `apps/web/Dockerfile.prod`
- `apps/core-api/Dockerfile.prod`
- `apps/core-worker/Dockerfile` (already production-safe)
- `apps/connector/Dockerfile.prod`

## 4) ECS task definitions

Templates live under `infra/aws/taskdefs/`:

- `core-api.json`
- `core-worker.json`
- `core-beat.json`
- `connector.json`
- `web.json`

You will replace placeholders like:

- `<AWS_ACCOUNT_ID>`
- `<AWS_REGION>`
- `<IMAGE_TAG>`
- `<EXECUTION_ROLE_ARN>`
- `<TASK_ROLE_ARN>`
- `<LOG_GROUP>`
- `<SUBNET_IDS>`
- `<SECURITY_GROUP_ID>`
- `<ALB_TARGET_GROUP_ARN>`

## 5) IAM

Create:

- Task execution role:
  - `AmazonECSTaskExecutionRolePolicy`
  - permission to pull from ECR + write CloudWatch logs
- Task role (app role) least-privilege for:
  - reading Secrets Manager / SSM parameters (if used)
  - S3 access (if you enable exports)

## 6) Security groups (minimum)

- `alb-sg`: inbound `80/443` from internet
- `web-sg`: inbound `3000` from `alb-sg`
- `coreapi-sg`: inbound `8000` from `alb-sg` (or only from `web-sg` if you don’t expose API publicly)
- `connector-sg`: inbound `8100` from `coreapi-sg`
- `rds-sg`: inbound `5432` from `coreapi-sg`, `worker-sg`, `connector-sg`
- `redis-sg`: inbound `6379` (or TLS port) from `coreapi-sg`, `worker-sg`

## 7) ALB target groups and health checks

- `web` health: `GET /`
- `core-api` health: `GET /health`

Path rules:

- `/v1/*` -> core-api TG
- `/docs*` -> core-api TG (optional)
- default -> web TG

## 8) One-time bootstrap jobs (recommended)

These images can create tables automatically, but for production you typically run one-time jobs:

- DB schema bootstrap / migrations
- optional seed of baseline configuration

In this repo:

- `core-api` prod entrypoint runs `core.db.bootstrap` always.
- Demo seeding is opt-in via `CORE_RUN_SEED=true`.
- Connector mock seeding is opt-in via `CONNECTOR_RUN_SEED=true`.

