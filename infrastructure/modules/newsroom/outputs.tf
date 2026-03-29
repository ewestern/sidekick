output "ecs_task_execution_role_arn" {
  description = "IAM role ARN for ECS task execution (image pull, logs)."
  value       = aws_iam_role.ecs_task_execution.arn
}

output "ecs_task_role_arn" {
  description = "IAM role ARN assumed by application containers."
  value       = aws_iam_role.ecs_task.arn
}

output "ecs_task_role_name" {
  description = "IAM role name assumed by application containers."
  value       = aws_iam_role.ecs_task.name
}

output "ecs_security_group_id" {
  description = "Security group for Fargate tasks (ingress to RDS allowed from here)."
  value       = aws_security_group.ecs_tasks.id
}

output "extract_pdf_ecs_security_group_id" {
  description = "Security group for dedicated Marker PDF extraction Fargate tasks."
  value       = aws_security_group.processing_pdf_tasks.id
}

output "ecs_task_definition_arns" {
  description = "Map of workload class to task definition ARN (Fargate). Transcription uses AWS Batch; see batch_job_definition_transcription_arn."
  value = {
    ingestion      = aws_ecs_task_definition.ingestion.arn
    processing     = aws_ecs_task_definition.processing.arn
    processing_pdf = aws_ecs_task_definition.processing_pdf.arn
    analysis       = aws_ecs_task_definition.analysis.arn
    editor         = aws_ecs_task_definition.editor.arn
  }
}

output "ecs_task_definition_families" {
  description = "Map of workload class to task definition family name."
  value       = local.workload_families
}

output "cloudwatch_log_group_name" {
  description = "Log group for ECS task stdout/stderr."
  value       = aws_cloudwatch_log_group.ecs.name
}


output "step_functions_ingestion_state_machine_arn" {
  description = "ARN of the ingestion-only state machine (list-due → spiders → collated artifacts)."
  value       = aws_sfn_state_machine.ingestion.arn
}

output "step_functions_processing_state_machine_arn" {
  description = "ARN of the per-artifact processing state machine (acquire? → process → entity-extract → summary)."
  value       = aws_sfn_state_machine.processing.arn
}

output "step_functions_analysis_state_machine_arn" {
  description = "ARN of the scope-oriented analysis state machine (debounce → beat run → quiet-period release)."
  value       = aws_sfn_state_machine.analysis.arn
}

output "step_functions_editorial_state_machine_arn" {
  description = "ARN of the event-driven editorial state machine (candidate gate → editor run → record result)."
  value       = aws_sfn_state_machine.editorial.arn
}

output "ecr_repository_urls" {
  description = "ECR repository URLs keyed by workload name (ingestion, processing, transcription, analysis, editor)."
  value       = { for k, v in aws_ecr_repository.workloads : k => v.repository_url }
}

output "lambda_list_due_ecr_repository_url" {
  description = "ECR repository URL for the list-due Lambda image (sidekick/lambda-list-due)."
  value       = aws_ecr_repository.lambda_handlers.repository_url
}

output "artifact_store_bucket_name" {
  description = "S3 bucket name for artifact bodies (same value as S3_BUCKET on ECS tasks)."
  value       = aws_s3_bucket.artifacts.bucket
}

output "artifact_store_bucket_arn" {
  description = "S3 bucket ARN for artifact bodies."
  value       = aws_s3_bucket.artifacts.arn
}

output "lambda_list_due_spiders_function_arn" {
  description = "ARN of the list-due Lambda (source registry query for ingestion Step Functions)."
  value       = aws_lambda_function.list_due_spiders.arn
}

output "lambda_analysis_function_arns" {
  description = "ARNs for coordination Lambda functions keyed by handler name."
  value       = { for k, v in aws_lambda_function.analysis_lambdas : k => v.arn }
}

output "lambda_handlers_security_group_id" {
  description = "Security group for Lambda handlers (RDS ingress from this SG)."
  value       = aws_security_group.lambda_handlers.id
}

output "batch_compute_security_group_id" {
  description = "Security group for transcription Batch GPU instances (allow RDS ingress from this SG)."
  value       = aws_security_group.batch_compute.id
}

output "extract_pdf_efs_file_system_id" {
  description = "EFS file system ID for Marker model cache, if enabled."
  value       = var.enable_extract_pdf_efs ? aws_efs_file_system.extract_pdf[0].id : null
}


output "batch_job_queue_transcription_name" {
  description = "AWS Batch job queue name for transcription workers."
  value       = aws_batch_job_queue.transcription.name
}

output "batch_job_definition_transcription_arn" {
  description = "AWS Batch job definition ARN for GPU transcription (sidekick-transcribe worker)."
  value       = aws_batch_job_definition.transcription.arn
}
