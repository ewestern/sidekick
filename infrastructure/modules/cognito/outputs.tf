output "user_pool_id" {
  description = "Cognito user pool ID for API users."
  value       = aws_cognito_user_pool.api.id
}

output "user_pool_issuer" {
  description = "JWT issuer URL for Cognito tokens."
  value       = "https://cognito-idp.${data.aws_region.current.name}.amazonaws.com/${aws_cognito_user_pool.api.id}"
}

output "public_client_id" {
  description = "Cognito app client ID used by public API consumers."
  value       = aws_cognito_user_pool_client.public_api.id
}
