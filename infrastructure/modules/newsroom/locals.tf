locals {
  tags = merge(
    {
      Module = "newsroom"
    },
    var.tags,
  )

  log_group_name = "/ecs/${var.name_prefix}"

  workload_families = {
    ingestion      = "${var.name_prefix}-ingestion"
    processing     = "${var.name_prefix}-processing"
    processing_pdf = "${var.name_prefix}-processing-pdf"
    analysis       = "${var.name_prefix}-analysis"
    editor         = "${var.name_prefix}-editor"
  }

  # S3_BUCKET is read by sidekick.core.object_store.create_object_store()
  task_environment = merge(
    var.common_environment,
    { S3_BUCKET = aws_s3_bucket.artifacts.bucket },
  )
}

data "aws_region" "current" {}
