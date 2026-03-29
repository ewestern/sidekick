locals {
  ecr_workloads = toset(["ingestion", "processing", "transcription", "analysis", "editor"])
}

resource "aws_ecr_repository" "workloads" {
  for_each = local.ecr_workloads

  name                 = "sidekick/${each.key}"
  image_tag_mutability = "MUTABLE"
  force_delete         = false

  tags = local.tags
}

resource "aws_ecr_lifecycle_policy" "workloads" {
  for_each   = local.ecr_workloads
  repository = aws_ecr_repository.workloads[each.key].name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = { type = "expire" }
      }
    ]
  })
}

resource "aws_ecr_repository" "lambda_handlers" {
  name                 = "sidekick/lambda-handlers"
  image_tag_mutability = "MUTABLE"
  force_delete         = false

  tags = local.tags
}

resource "aws_ecr_lifecycle_policy" "lambda_handlers" {
  repository = aws_ecr_repository.lambda_handlers.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = { type = "expire" }
      }
    ]
  })
}
