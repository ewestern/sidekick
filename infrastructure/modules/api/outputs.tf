output "service_arn" {
  description = "ECS service ARN for the API workload."
  value       = aws_ecs_service.api.id
}

output "service_name" {
  description = "ECS service name."
  value       = aws_ecs_service.api.name
}

output "task_definition_arn" {
  description = "Task definition ARN used by the API service."
  value       = aws_ecs_task_definition.api.arn
}

output "task_execution_role_arn" {
  description = "IAM task execution role ARN."
  value       = aws_iam_role.ecs_task_execution.arn
}

output "task_role_arn" {
  description = "IAM task role ARN."
  value       = aws_iam_role.ecs_task.arn
}

output "target_group_arn" {
  description = "ALB target group ARN for API tasks."
  value       = aws_lb_target_group.api.arn
}

output "ecs_security_group_id" {
  description = "Security group attached to API ECS tasks."
  value       = aws_security_group.ecs_service.id
}

output "listener_rule_arn" {
  description = "ALB listener rule ARN routing API traffic."
  value       = aws_lb_listener_rule.api.arn
}

output "ecr_repository_url" {
  description = "ECR repository URL for the API image."
  value       = aws_ecr_repository.api.repository_url
}
