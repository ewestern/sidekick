locals {
  tags = merge(
    {
      Module = "cognito"
    },
    var.tags,
  )
}

data "aws_region" "current" {}

resource "aws_cognito_user_pool" "api" {
  name = "${var.name_prefix}-api-users"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  mfa_configuration        = "OFF"

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = false
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
  }

  tags = local.tags
}

resource "aws_cognito_user_pool_client" "public_api" {
  name                                 = "${var.name_prefix}-public-api"
  user_pool_id                         = aws_cognito_user_pool.api.id
  generate_secret                      = false
  refresh_token_validity               = 7
  access_token_validity                = 60
  id_token_validity                    = 60
  prevent_user_existence_errors        = "ENABLED"
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["email", "openid", "profile"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = var.callback_urls
  logout_urls                          = var.logout_urls

  explicit_auth_flows = [
    "ALLOW_ADMIN_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_PASSWORD_AUTH",
  ]

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }
}

resource "aws_cognito_user_group" "reader" {
  name         = "reader"
  user_pool_id = aws_cognito_user_pool.api.id
}

resource "aws_cognito_user_group" "editor" {
  name         = "editor"
  user_pool_id = aws_cognito_user_pool.api.id
}

resource "aws_cognito_user_group" "admin" {
  name         = "admin"
  user_pool_id = aws_cognito_user_pool.api.id
}

resource "aws_cognito_user_pool_domain" "api" {
  domain       = var.domain_prefix
  user_pool_id = aws_cognito_user_pool.api.id
}
