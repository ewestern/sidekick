# Private artifact object store for workload containers (aligned with S3_BUCKET / create_object_store).

resource "aws_s3_bucket" "artifacts" {
  bucket = "newsroom-artifacts-${var.env}"
  tags   = merge(local.tags, { Name = "${var.name_prefix}-artifacts" })
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
