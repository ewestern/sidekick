locals {
  tags = merge(
    {
      Module = "api"
    },
    var.tags,
  )

  core_environment = merge(
    {
      DATABASE_URL   = var.rds_url
      API_KEY_PEPPER = var.api_key_pepper
    },
    {
      COGNITO_REGION       = data.aws_region.current.name
      COGNITO_USER_POOL_ID = var.cognito.user_pool_id
      COGNITO_ISSUER       = var.cognito.issuer
      COGNITO_AUDIENCE     = var.cognito.audience
    },
    var.cors_allowed_origins != null && var.cors_allowed_origins != "" ? {
      CORS_ALLOWED_ORIGINS = var.cors_allowed_origins
    } : {},
  )

  api_environment_map = merge(var.common_environment, local.core_environment)
  api_environment     = [for k, v in local.api_environment_map : { name = k, value = v }]

  service_name        = "${var.name_prefix}-service"
  task_family         = "${var.name_prefix}-task"
  log_group_name      = "/ecs/${var.name_prefix}-api"
  target_group_name   = "${var.name_prefix}-tg"
  execution_role_name = "${var.name_prefix}-api-exec-role"
  task_role_name      = "${var.name_prefix}-api-task-role"
}
