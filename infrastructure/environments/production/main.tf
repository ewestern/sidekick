terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
  backend "s3" {
    bucket  = "sidekick-tf-state"
    key     = "prod/terraform.tfstate"
    region  = "us-west-2"
    profile = "sidekick"
  }
}

# Configure the default AWS Provider (us-west-2)
provider "aws" {
  region  = "us-west-2"
  profile = "sidekick"
  default_tags {
    tags = {
      Environment = "production"
      Project     = "sidekick"
      ManagedBy   = "terraform"
    }
  }
}

data "aws_vpc" "selected" {
  id = "vpc-0426e8fb181cef8ef"
}

data "aws_route53_zone" "sidekick_news" {
  name = "sidekick.news."
}
resource "aws_route53_record" "api" {
  zone_id = data.aws_route53_zone.sidekick_news.zone_id
  type    = "A"
  name    = "api.${data.aws_route53_zone.sidekick_news.name}"
  alias {
    name                   = aws_lb.shared.dns_name
    zone_id                = aws_lb.shared.zone_id
    evaluate_target_health = true
  }
}
resource "aws_acm_certificate" "cert" {
  domain_name       = "*.sidekick.news"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}


resource "aws_ecs_cluster" "shared" {
  name = var.shared_ecs_cluster_name
}

resource "aws_security_group" "shared_alb" {
  name_prefix = "sidekick-shared-alb-"
  description = "Ingress for shared Sidekick ALB"
  vpc_id      = data.aws_vpc.selected.id

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_lb" "shared" {
  name               = var.shared_alb_name
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.shared_alb.id]
  subnets            = local.shared_alb_subnets
}

resource "aws_lb_listener" "shared_http" {
  load_balancer_arn = aws_lb.shared.arn
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = aws_acm_certificate.cert.arn

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "No matching service route"
      status_code  = "404"
    }
  }
}

resource "aws_security_group" "shared_rds" {
  name_prefix = "sidekick-shared-rds-"
  description = "Ingress for shared Sidekick PostgreSQL"
  vpc_id      = data.aws_vpc.selected.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_subnet_group" "shared" {
  name_prefix = "${var.shared_rds_identifier}-"
  subnet_ids  = var.private_subnet_ids
}

resource "aws_db_instance" "shared" {
  identifier     = var.shared_rds_identifier
  engine         = "postgres"
  engine_version = var.shared_rds_engine_version
  instance_class = var.shared_rds_instance_class

  allocated_storage     = var.shared_rds_allocated_storage
  max_allocated_storage = var.shared_rds_allocated_storage * 2
  storage_encrypted     = true

  db_name  = var.shared_rds_database_name
  username = var.shared_rds_master_username

  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.shared.name
  vpc_security_group_ids = [aws_security_group.shared_rds.id]

  backup_retention_period   = var.shared_rds_backup_retention_period
  deletion_protection       = var.shared_rds_deletion_protection
  skip_final_snapshot       = var.shared_rds_skip_final_snapshot
  final_snapshot_identifier = var.shared_rds_skip_final_snapshot ? null : "${var.shared_rds_identifier}-final"

  publicly_accessible = false
  multi_az            = false
}

data "aws_region" "current" {}

module "newsroom" {
  source          = "../../modules/newsroom"
  env             = "production"
  name_prefix     = var.newsroom_name_prefix
  vpc_id          = data.aws_vpc.selected.id
  ecs_cluster_arn = aws_ecs_cluster.shared.arn
  openai_api_key  = jsondecode(data.aws_secretsmanager_secret_version.openai_api_key.secret_string)["api_key"]

  ecs_task_subnet_ids = var.private_subnet_ids
  common_environment = {
    DATABASE_URL = local.api_database_url
  }
  enable_step_functions_logging = false
  hf_token                      = jsondecode(data.aws_secretsmanager_secret_version.hf_token.secret_string)["token"]
  enable_extract_pdf_efs        = true
  extract_pdf_task_cpu          = 2048
  extract_pdf_task_memory       = 8192
  extract_pdf_timeout_seconds   = 1800
}

module "cognito" {
  source = "../../modules/cognito"

  name_prefix   = "sidekick"
  domain_prefix = "sidekick-news"
  callback_urls = [
    "https://admin.sidekick.news/callback",
    "http://localhost:5173/callback",
  ]
  logout_urls = [
    "https://admin.sidekick.news/logout",
    "http://localhost:5173/logout",
  ]
}

resource "random_password" "api_key_pepper" {
  length  = 64
  special = false
}

data "aws_secretsmanager_secret_version" "newsroom_rds_master" {
  secret_id = aws_db_instance.shared.master_user_secret[0].secret_arn
}

locals {
  newsroom_db_secret = jsondecode(data.aws_secretsmanager_secret_version.newsroom_rds_master.secret_string)
  api_database_url   = "postgresql://${local.newsroom_db_secret["username"]}:${local.newsroom_db_secret["password"]}@${aws_db_instance.shared.address}:${aws_db_instance.shared.port}/${aws_db_instance.shared.db_name}"
  #format(
  #  "postgresql://%s:%s@%s:%s/%s",
  #  urlencode(local.newsroom_db_secret["username"]),
  #  urlencode(local.newsroom_db_secret["password"]),
  #  aws_db_instance.shared.address,
  #  tostring(aws_db_instance.shared.port),
  #  aws_db_instance.shared.db_name
  #)
  shared_alb_subnets = length(var.public_subnet_ids) > 0 ? var.public_subnet_ids : var.private_subnet_ids
}

resource "aws_security_group_rule" "newsroom_rds_ingress_from_newsroom" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = module.newsroom.ecs_security_group_id
  security_group_id        = aws_security_group.shared_rds.id
  description              = "PostgreSQL from newsroom ECS tasks"
}

resource "aws_security_group_rule" "newsroom_rds_ingress_from_extract_pdf" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = module.newsroom.extract_pdf_ecs_security_group_id
  security_group_id        = aws_security_group.shared_rds.id
  description              = "PostgreSQL from dedicated Marker PDF extraction tasks"
}

resource "aws_security_group_rule" "newsroom_rds_ingress_from_lambda_handlers" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = module.newsroom.lambda_handlers_security_group_id
  security_group_id        = aws_security_group.shared_rds.id
  description              = "PostgreSQL from newsroom Lambda handlers (VPC)"
}

resource "aws_security_group_rule" "newsroom_rds_ingress_from_batch_transcription" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = module.newsroom.batch_compute_security_group_id
  security_group_id        = aws_security_group.shared_rds.id
  description              = "PostgreSQL from newsroom transcription Batch GPU workers"
}

resource "aws_security_group_rule" "newsroom_rds_ingress_from_api" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = module.api.ecs_security_group_id
  security_group_id        = aws_security_group.shared_rds.id
  description              = "PostgreSQL from Sidekick API ECS tasks"
}

resource "aws_iam_role_policy" "newsroom_task_rds_secret" {
  name_prefix = "${var.newsroom_name_prefix}-rds-secret-"
  role        = module.newsroom.ecs_task_role_name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "AllowReadRdsMasterSecret"
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = aws_db_instance.shared.master_user_secret[0].secret_arn
      }
    ]
  })
}

module "api" {
  source = "../../modules/api"

  name_prefix     = var.api_name_prefix
  vpc_id          = data.aws_vpc.selected.id
  ecs_cluster_arn = aws_ecs_cluster.shared.arn

  ecs_subnet_ids        = var.private_subnet_ids
  alb_listener_arn      = aws_lb_listener.shared_http.arn
  alb_security_group_id = aws_security_group.shared_alb.id
  rds_url               = local.api_database_url

  assign_public_ip = var.api_assign_public_ip

  api_key_pepper = random_password.api_key_pepper.result
  cognito = {
    user_pool_id = module.cognito.user_pool_id
    issuer       = module.cognito.user_pool_issuer
    audience     = module.cognito.public_client_id
  }
  cors_allowed_origins = join(",", [
    "https://sidekick-admin.vercel.app",
    "https://admin.sidekick.news",
  ])

  common_environment = var.api_extra_environment

  tags = {
    Workload = "api"
  }
}

output "newsroom_ecs_task_definition_arns" {
  description = "Newsroom ECS task definitions by workload class."
  value       = module.newsroom.ecs_task_definition_arns
}

output "newsroom_ecs_security_group_id" {
  description = "Security group for newsroom Fargate tasks."
  value       = module.newsroom.ecs_security_group_id
}

output "newsroom_rds_endpoint" {
  description = "Newsroom PostgreSQL endpoint."
  value       = aws_db_instance.shared.endpoint
}

output "newsroom_cognito_user_pool_id" {
  description = "Cognito user pool ID for API auth."
  value       = module.cognito.user_pool_id
}

output "newsroom_cognito_issuer" {
  description = "Cognito JWT issuer for API validation."
  value       = module.cognito.user_pool_issuer
}

output "newsroom_cognito_public_client_id" {
  description = "Cognito public app client ID."
  value       = module.cognito.public_client_id
}

output "api_alb_dns_name" {
  description = "DNS name of the shared load balancer used by API routes."
  value       = aws_lb.shared.dns_name
}

output "api_service_name" {
  description = "ECS service name for the API."
  value       = module.api.service_name
}

output "api_ecs_security_group_id" {
  description = "Security group for API ECS tasks."
  value       = module.api.ecs_security_group_id
}

output "newsroom_ecr_repository_urls" {
  description = "ECR repository URLs for newsroom workloads (ingestion, processing, transcription, analysis)."
  value       = module.newsroom.ecr_repository_urls
}

output "api_ecr_repository_url" {
  description = "ECR repository URL for the API image."
  value       = module.api.ecr_repository_url
}
