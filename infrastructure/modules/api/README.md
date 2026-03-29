# `api` Terraform module

Deploys the Sidekick public API as an ECS/Fargate service that attaches to a
shared ALB listener and supporting runtime infrastructure.

## What this module creates

- CloudWatch log group for API container logs
- IAM task execution role + task role
- Security group for ECS service
- API target group + listener rule on a shared ALB listener
- ECS task definition
- ECS service (Fargate) wired to the API target group

## Required inputs

- `name_prefix`
- `vpc_id`
- `ecs_cluster_arn`
- `ecs_subnet_ids`
- `alb_listener_arn`
- `alb_security_group_id`
- `rds_url` (injected as `DATABASE_URL`)

## Example

```hcl
module "api" {
  source = "../../modules/api"

  name_prefix     = "sidekick-production-api"
  vpc_id          = data.aws_vpc.selected.id
  ecs_cluster_arn = aws_ecs_cluster.shared.arn
  ecs_subnet_ids  = var.private_subnet_ids
  alb_listener_arn      = aws_lb_listener.shared_http.arn
  alb_security_group_id = aws_security_group.shared_alb.id
  rds_url         = var.api_rds_url

  api_container_image = "123456789012.dkr.ecr.us-west-2.amazonaws.com/sidekick/api:latest"
  common_environment = {
    COGNITO_REGION       = "us-west-2"
    COGNITO_USER_POOL_ID = "us-west-2_abc123"
    COGNITO_ISSUER       = "https://cognito-idp.us-west-2.amazonaws.com/us-west-2_abc123"
    COGNITO_AUDIENCE     = "abc123clientid"
  }
}
```

## Notes

- The caller owns the shared ALB + listener (for example in the environment
  root) and passes listener/SG references into this module.
- `rds_url` may reference a direct URL or a value rendered from Secrets Manager.
