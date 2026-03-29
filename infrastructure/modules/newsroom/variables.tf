variable "env" {
  type        = string
  description = "Environment name (e.g. production, staging, development)."
}

variable "openai_api_key" {
  type        = string
  description = "OpenAI API key for Sidekick services."
}

variable "name_prefix" {
  type        = string
  description = "Prefix for resource names (e.g. sidekick-production-newsroom)."
}

variable "vpc_id" {
  type        = string
  description = "VPC ID where ECS tasks and RDS run."
}

variable "ecs_cluster_arn" {
  type        = string
  description = "Existing ECS cluster ARN for RunTask and task definitions."
}

variable "ecs_task_subnet_ids" {
  type        = list(string)
  description = "Subnets for Fargate tasks (typically private shared subnets)."
}

#variable "ingestion_container_command" {
#  type        = list(string)
#  description = "Default container command for ingestion task definition (override per RunTask)."
#  default     = ["sleep", "3600"]
#}

#variable "processing_container_command" {
#  type        = list(string)
#  description = "Default container command for processing task definition."
#  default     = ["sleep", "3600"]
#}
#
#variable "transcription_container_command" {
#  type        = list(string)
#  description = "Default container command for transcription task definition (e.g. sidekick-transcribe <artifact_id>)."
#  default     = ["sleep", "3600"]
#}
#
#variable "analysis_container_command" {
#  type        = list(string)
#  description = "Default container command for analysis task definition."
#  default     = ["sleep", "3600"]
#}

variable "task_cpu" {
  type        = number
  description = "Fargate task CPU units (256, 512, 1024, ...)."
  default     = 512
}

variable "task_memory" {
  type        = number
  description = "Fargate task memory (MiB), must be valid for chosen CPU."
  default     = 1024
}

variable "extract_pdf_task_cpu" {
  type        = number
  description = "Dedicated Fargate CPU units for Marker PDF extraction tasks."
  default     = 2048
}

variable "extract_pdf_task_memory" {
  type        = number
  description = "Dedicated Fargate memory (MiB) for Marker PDF extraction tasks."
  default     = 8192
}

variable "extract_pdf_timeout_seconds" {
  type        = number
  description = "Timeout in seconds for the ExtractPdf Step Functions task."
  default     = 1800
}

variable "enable_extract_pdf_efs" {
  type        = bool
  description = "Enable EFS-backed shared model cache for Marker PDF extraction tasks."
  default     = true
}

variable "extract_pdf_model_cache_path" {
  type        = string
  description = "EFS access point path and mount location root for Marker model cache."
  default     = "/marker-cache"
}

variable "sfn_max_concurrency_spiders" {
  type        = number
  description = "Max parallel spider runs in the SpiderMap state (0 = unlimited)."
  default     = 5
}

variable "sfn_max_concurrency_artifacts" {
  type        = number
  description = "Max parallel processing state machine executions in the orchestration Map state (0 = unlimited)."
  default     = 10
}

variable "sfn_schedule_expression" {
  type        = string
  description = "EventBridge Scheduler expression for the pipeline (e.g. 'rate(1 hour)' or 'cron(0 * * * ? *)')."
  default     = "rate(1 hour)"
}

variable "analysis_scope_debounce_seconds" {
  type        = number
  description = "Initial debounce window before running beat analysis for a scope."
  default     = 180
}

variable "analysis_scope_followup_seconds" {
  type        = number
  description = "Short wait before rerunning beat analysis when new inputs arrive during a run."
  default     = 120
}

variable "analysis_scope_quiet_period_seconds" {
  type        = number
  description = "Quiet-period wait before releasing an analysis scope after a stable run."
  default     = 43200
}

variable "enable_step_functions_logging" {
  type        = bool
  description = "Enable CloudWatch logging on the orchestration state machine."
  default     = false
}

variable "step_functions_log_level" {
  type        = string
  description = "Log level for Step Functions (ALL, ERROR, FATAL, OFF)."
  default     = "ERROR"
}

variable "common_environment" {
  type        = map(string)
  description = "Environment variables applied to all workload containers (e.g. DATABASE_URL)."
  default     = {}
}

variable "hf_token" {
  type        = string
  sensitive   = true
  description = "Hugging Face token for WhisperX diarization (pyannote) on Batch transcription jobs."
}

variable "whisper_model" {
  type        = string
  description = "WhisperX model size passed to Batch transcription workers (e.g. base, large-v3)."
  default     = "base"
}

variable "tags" {
  type        = map(string)
  description = "Additional tags for module-created resources."
  default     = {}
}
