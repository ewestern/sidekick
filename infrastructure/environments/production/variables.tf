variable "public_subnet_ids" {
  type        = list(string)
  description = "Public subnet IDs shared by internet-facing resources like the ALB."
  default     = ["subnet-07ba7ca70d6683498", "subnet-05e68fde34010eeec"]
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs shared by ECS tasks and internal data-plane resources."
  default     = ["subnet-0c834cac2d8dbacdc", "subnet-077c9efc066d3c059"]
}

variable "shared_ecs_cluster_name" {
  type        = string
  description = "Name for the shared ECS cluster used by services."
  default     = "sidekick-production"
}

variable "newsroom_name_prefix" {
  type        = string
  description = "Resource name prefix for the newsroom module."
  default     = "newsroom-production"
}

# --- Public API (ECS + ALB) -------------------------------------------------

variable "api_name_prefix" {
  type        = string
  description = "Resource name prefix for the API module."
  default     = "api-production"
}

variable "shared_alb_internal" {
  type        = bool
  description = "If true, the shared ALB is internal-only."
  default     = true
}

variable "api_assign_public_ip" {
  type        = bool
  description = "Whether API Fargate tasks get public IPs (usually false in private subnets)."
  default     = false
}

variable "shared_alb_name" {
  type        = string
  description = "Name for the shared application load balancer."
  default     = "sidekick-production-shared-alb"
}

variable "shared_rds_identifier" {
  type        = string
  description = "DB instance identifier for the shared PostgreSQL database."
  default     = "sidekick-production-postgres"
}

variable "shared_rds_instance_class" {
  type        = string
  description = "RDS instance class for shared PostgreSQL."
  default     = "db.t4g.micro"
}

variable "shared_rds_allocated_storage" {
  type        = number
  description = "Allocated storage in GB for shared PostgreSQL."
  default     = 20
}

variable "shared_rds_engine_version" {
  type        = string
  description = "PostgreSQL engine version for shared database."
  default     = "16"
}

variable "shared_rds_database_name" {
  type        = string
  description = "Initial database name for shared PostgreSQL."
  default     = "sidekick"
}

variable "shared_rds_master_username" {
  type        = string
  description = "Master username for shared PostgreSQL."
  default     = "sidekick"
}

variable "shared_rds_skip_final_snapshot" {
  type        = bool
  description = "If true, no final snapshot is taken on destroy."
  default     = false
}

variable "shared_rds_deletion_protection" {
  type        = bool
  description = "Enable deletion protection on shared PostgreSQL."
  default     = true
}

variable "shared_rds_backup_retention_period" {
  type        = number
  description = "Backup retention period in days for shared PostgreSQL."
  default     = 7
}

variable "api_extra_environment" {
  type        = map(string)
  description = "Extra env vars merged into the API task definition."
  default     = {}
}