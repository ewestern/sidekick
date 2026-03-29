# List-due Lambda: image is built/pushed outside Terraform (see repo Justfile).
# Image: packages/lambda-handlers/Dockerfile — https://docs.astral.sh/uv/guides/integration/aws-lambda/
#
# `image_uri` uses the digest from `aws_ecr_image` so each apply tracks the current
# `latest` manifest in ECR (see registry docs: data source `aws_ecr_image`).
# Bootstrap: create the ECR repo (e.g. targeted apply), run `just push lambda-list-due`, then apply.

data "aws_ecr_image" "lambda_handlers" {
  repository_name = aws_ecr_repository.lambda_handlers.name
  most_recent     = true
}

locals {
  coordination_lambda_handlers = {
    analysis_upsert_scope    = "sidekick_lambda.handlers.analysis_upsert_scope.handler"
    analysis_claim_scope     = "sidekick_lambda.handlers.analysis_claim_scope.handler"
    analysis_record_run      = "sidekick_lambda.handlers.analysis_record_run.handler"
    analysis_check_scope     = "sidekick_lambda.handlers.analysis_check_scope.handler"
    analysis_release_scope   = "sidekick_lambda.handlers.analysis_release_scope.handler"
    editor_prepare_candidate = "sidekick_lambda.handlers.editor_prepare_candidate.handler"
    editor_record_run        = "sidekick_lambda.handlers.editor_record_run.handler"
  }
}

resource "aws_cloudwatch_log_group" "lambda_handlers" {
  name              = "/aws/lambda/${var.name_prefix}-lambda-handlers"
  retention_in_days = 30
  tags              = local.tags
}

resource "aws_security_group" "lambda_handlers" {
  name_prefix = "${var.name_prefix}-lambda-handlers-"
  description = "Lambda handlers (Postgres egress to RDS)"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, { Name = "${var.name_prefix}-lambda-handlers" })
}

resource "aws_iam_role" "lambda_handlers" {
  name_prefix = "${var.name_prefix}-lambda-handlers-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "lambda_handlers_basic" {
  role       = aws_iam_role.lambda_handlers.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_handlers_vpc" {
  role       = aws_iam_role.lambda_handlers.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy" "lambda_handlers_ecr" {
  name = "${var.name_prefix}-lambda-handlers"
  role = aws_iam_role.lambda_handlers.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "LambdaPullListDueImage"
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
        ]
        Resource = aws_ecr_repository.lambda_handlers.arn
      },
      {
        Sid      = "LambdaEcrAuthToken"
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      }
    ]
  })
}

resource "aws_lambda_function" "list_due_spiders" {
  function_name = "${var.name_prefix}-list-due-spiders"
  role          = aws_iam_role.lambda_handlers.arn
  package_type  = "Image"
  image_uri     = data.aws_ecr_image.lambda_handlers.image_uri
  architectures = ["x86_64"]
  timeout       = 60
  memory_size   = 512

  vpc_config {
    subnet_ids         = var.ecs_task_subnet_ids
    security_group_ids = [aws_security_group.lambda_handlers.id]
  }

  environment {
    variables = local.task_environment
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_handlers,
    aws_iam_role_policy_attachment.lambda_handlers_basic,
    aws_iam_role_policy_attachment.lambda_handlers_vpc,
    aws_iam_role_policy.lambda_handlers_ecr,
  ]

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "analysis_lambdas" {
  for_each          = local.coordination_lambda_handlers
  name              = "/aws/lambda/${var.name_prefix}-${replace(each.key, "_", "-")}"
  retention_in_days = 30
  tags              = local.tags
}

resource "aws_lambda_function" "analysis_lambdas" {
  for_each      = local.coordination_lambda_handlers
  function_name = "${var.name_prefix}-${replace(each.key, "_", "-")}"
  role          = aws_iam_role.lambda_handlers.arn
  package_type  = "Image"
  image_uri     = data.aws_ecr_image.lambda_handlers.image_uri
  architectures = ["x86_64"]
  timeout       = 60
  memory_size   = 512

  image_config {
    command = [each.value]
  }

  vpc_config {
    subnet_ids         = var.ecs_task_subnet_ids
    security_group_ids = [aws_security_group.lambda_handlers.id]
  }

  environment {
    variables = local.task_environment
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_handlers_basic,
    aws_iam_role_policy_attachment.lambda_handlers_vpc,
    aws_iam_role_policy.lambda_handlers_ecr,
    aws_cloudwatch_log_group.analysis_lambdas,
  ]

  tags = local.tags
}
