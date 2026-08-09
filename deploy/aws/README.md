# Minimal AWS deployment blueprint

The application already builds as one OCI container. A small AWS deployment
needs managed equivalents for the two Compose services:

```text
Internet
   |
Application Load Balancer
   |
ECS Fargate service ---- CloudWatch Logs
   |
RDS PostgreSQL

Secrets Manager --> ECS environment secrets
```

## Recommended resources

1. **ECR repository** for the image built by `Dockerfile`.
2. **ECS Fargate service** with one task for a demo and port `8000`.
3. **Application Load Balancer** using `/health` for liveness and `/ready` for
   target readiness.
4. **RDS PostgreSQL** in private subnets.
5. **Secrets Manager** values for `CIR_DATABASE_URL`, `CIR_API_KEY`,
   `CIR_JWT_SECRET`, and optionally `CIR_OPENAI_API_KEY`.
6. **CloudWatch Logs** for Uvicorn request and application logs.

## Deployment sequence

```bash
# Build and test locally.
docker build -t incident-response-api .
docker run --rm incident-response-api uv run python -c "from app.main import app"

# Authenticate Docker to your ECR registry, then tag and push.
docker tag incident-response-api:latest \
  ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/incident-response-api:VERSION
docker push \
  ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/incident-response-api:VERSION
```

Run `uv run alembic upgrade head` as a one-off ECS task before updating the
service. The normal container command starts only the API, which avoids
multiple replicas racing to apply migrations.

## Security-group rules

- ALB accepts HTTPS from the internet.
- ECS accepts port `8000` only from the ALB security group.
- RDS accepts port `5432` only from the ECS security group.
- ECS tasks use private subnets with outbound HTTPS for optional AI requests.

## Production settings

Set `CIR_ENVIRONMENT=production`. Startup then rejects the documented local
API and JWT secrets. Use at least 32 random bytes for `CIR_JWT_SECRET`.

This blueprint stays account-neutral: VPC IDs, certificates, DNS names, image
versions, and sizing are deployment inputs rather than hard-coded repository
values.
