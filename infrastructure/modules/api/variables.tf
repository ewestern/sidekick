variable "name_prefix" {
  type        = string
  description = "Prefix for resource names (e.g. sidekick-production-api)."
}

variable "vpc_id" {
  type        = string
  description = "VPC ID for API load balancer, ECS service, and security groups."
}

variable "ecs_cluster_arn" {
  type        = string
  description = "ECS cluster ARN where API tasks run."
}

variable "ecs_subnet_ids" {
  type        = list(string)
  description = "Subnets for ECS tasks."
}

variable "alb_listener_arn" {
  type        = string
  description = "Shared ALB listener ARN used to route API traffic."
}

variable "alb_security_group_id" {
  type        = string
  description = "Security group ID attached to the shared ALB."
}

variable "rds_url" {
  type        = string
  description = "Database URL injected as DATABASE_URL into the API container."
  sensitive   = true
}

variable "api_key_pepper" {
  type        = string
  description = "Secret pepper for API key hashing (API_KEY_PEPPER)."
  sensitive   = true
}

variable "cognito" {
  type = object({
    user_pool_id = string
    issuer       = string
    audience     = string
  })
  description = <<-EOT
    Cognito JWT settings for the API container. Pass user_pool_id, issuer, and audience
    from the cognito module outputs (user_pool_id, user_pool_issuer, public_client_id).
    Required; omitting this argument is a Terraform error.
  EOT

  validation {
    condition = (
      var.cognito.user_pool_id != "" &&
      var.cognito.issuer != "" &&
      var.cognito.audience != ""
    )
    error_message = "cognito.user_pool_id, cognito.issuer, and cognito.audience must be non-empty strings."
  }
}

variable "cors_allowed_origins" {
  type        = string
  default     = null
  description = "Optional comma-separated CORS_ALLOWED_ORIGINS; omit to use the application default."
}

variable "container_port" {
  type        = number
  description = "Container/listener port exposed by the API."
  default     = 8080
}

variable "health_check_path" {
  type        = string
  description = "ALB target group health check path."
  default     = "/docs"
}

variable "task_cpu" {
  type        = number
  description = "Fargate task CPU units."
  default     = 512
}

variable "task_memory" {
  type        = number
  description = "Fargate task memory in MiB."
  default     = 1024
}

variable "desired_count" {
  type        = number
  description = "Desired running task count for the ECS service."
  default     = 1
}

variable "assign_public_ip" {
  type        = bool
  description = "Whether ECS task ENIs should receive public IPs."
  default     = false
}

variable "listener_rule_priority" {
  type        = number
  description = "Priority for the API listener rule on the shared ALB listener."
  default     = 100
}

variable "listener_rule_path_patterns" {
  type        = list(string)
  description = "Path patterns that should route from the shared listener to the API target group."
  default     = ["/*"]
}

variable "common_environment" {
  type        = map(string)
  description = "Additional environment variables added to the API container."
  default     = {}
}

variable "tags" {
  type        = map(string)
  description = "Additional tags for module resources."
  default     = {}
}
