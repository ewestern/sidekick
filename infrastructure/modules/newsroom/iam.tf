data "aws_caller_identity" "current" {}

# ECS task execution role (pull images, write logs)
resource "aws_iam_role" "ecs_task_execution" {
  name_prefix = "${var.name_prefix}-ecs-exec-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS task role (runtime: app secrets, S3, etc. — extend as services need)
resource "aws_iam_role" "ecs_task" {
  name_prefix = "${var.name_prefix}-ecs-task-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
  tags = local.tags
}

# Artifact object store (S3_BUCKET on task definitions)
resource "aws_iam_role_policy" "ecs_task_artifact_store" {
  name_prefix = "${var.name_prefix}-s3-artifacts-"
  role        = aws_iam_role.ecs_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ArtifactStoreObjects"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
        ]
        Resource = "${aws_s3_bucket.artifacts.arn}/*"
      },
      {
        Sid      = "ArtifactStoreList"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = aws_s3_bucket.artifacts.arn
      },
    ]
  })
}

resource "aws_iam_role_policy" "ecs_task_extract_pdf_efs" {
  count = var.enable_extract_pdf_efs ? 1 : 0

  name_prefix = "${var.name_prefix}-efs-extract-pdf-"
  role        = aws_iam_role.ecs_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "AllowMarkerCacheEfsMount"
      Effect = "Allow"
      Action = [
        "elasticfilesystem:ClientMount",
        "elasticfilesystem:ClientWrite",
      ]
      Resource = [
        aws_efs_file_system.extract_pdf[0].arn,
        aws_efs_access_point.extract_pdf[0].arn,
      ]
    }]
  })
}

# Allow ECS task containers to call sfn:SendTaskSuccess/Failure (waitForTaskToken pattern)
# and StartExecution (sfn-run SFN_NEXT_EXECUTION_ARN pattern used by transcription Batch jobs).
resource "aws_iam_role_policy" "ecs_task_sfn_callback" {
  name_prefix = "${var.name_prefix}-sfn-callback-"
  role        = aws_iam_role.ecs_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowSfnTaskCallback"
        Effect = "Allow"
        Action = [
          "states:SendTaskSuccess",
          "states:SendTaskFailure",
          "states:SendTaskHeartbeat",
        ]
        Resource = "*"
      },
      {
        Sid      = "AllowSfnStartExecution"
        Effect   = "Allow"
        Action   = ["states:StartExecution"]
        Resource = "arn:aws:states:*:*:stateMachine:${var.name_prefix}-processing"
      }
    ]
  })
}

# Step Functions invokes ECS RunTask
resource "aws_iam_role" "step_functions" {
  name_prefix = "${var.name_prefix}-sfn-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "states.amazonaws.com" }
    }]
  })
  tags = local.tags
}

resource "aws_iam_role_policy" "step_functions_ecs" {
  name_prefix = "${var.name_prefix}-sfn-ecs-"
  role        = aws_iam_role.step_functions.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecs:RunTask",
          "ecs:StopTask",
          "ecs:DescribeTasks",
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = "iam:PassRole"
        Resource = [
          aws_iam_role.ecs_task_execution.arn,
          aws_iam_role.ecs_task.arn,
        ]
      },
      # ECS RunTask.sync and states:startExecution.sync each use a managed EventBridge rule
      # (see AWS docs: connect ECS / connect Step Functions — synchronous integrations).
      {
        Effect = "Allow"
        Action = [
          "events:PutTargets",
          "events:PutRule",
          "events:DescribeRule",
        ]
        Resource = "arn:aws:events:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:rule/StepFunctions*"
      },
      # Nested state machines (StartExecution.sync on ingestion + processing).
      # Use name_prefix patterns — not aws_sfn_state_machine.*.arn — to avoid IAM ↔ SFN cycles.
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution",
          "states:DescribeExecution",
          "states:StopExecution",
        ]
        Resource = [
          "arn:aws:states:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:stateMachine:${var.name_prefix}-ingestion",
          "arn:aws:states:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:stateMachine:${var.name_prefix}-processing",
          "arn:aws:states:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:execution:*:*",
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups",
        ]
        Resource = "*"
      },
      {
        Sid      = "AllowInvokeListDueLambda"
        Effect   = "Allow"
        Action   = ["lambda:InvokeFunction"]
        Resource = aws_lambda_function.list_due_spiders.arn
      },
      {
        Sid      = "AllowInvokeAnalysisCoordinatorLambdas"
        Effect   = "Allow"
        Action   = ["lambda:InvokeFunction"]
        Resource = [for fn in aws_lambda_function.analysis_lambdas : fn.arn]
      },
      {
        Sid    = "AllowBatchTranscription"
        Effect = "Allow"
        Action = [
          "batch:SubmitJob",
          "batch:DescribeJobs",
          "batch:TerminateJob",
        ]
        Resource = "*"
      }
    ]
  })
}

# EventBridge Scheduler role — triggers the pipeline state machine on a cron
resource "aws_iam_role" "scheduler" {
  name_prefix = "${var.name_prefix}-scheduler-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
    }]
  })
  tags = local.tags
}

resource "aws_iam_role_policy" "scheduler_sfn" {
  name_prefix = "${var.name_prefix}-scheduler-sfn-"
  role        = aws_iam_role.scheduler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "AllowStartExecution"
      Effect   = "Allow"
      Action   = ["states:StartExecution"]
      Resource = aws_sfn_state_machine.ingestion.arn
    }]
  })
}

resource "aws_iam_role" "eventbridge_analysis" {
  name_prefix = "${var.name_prefix}-events-analysis-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
    }]
  })
  tags = local.tags
}

resource "aws_iam_role_policy" "eventbridge_analysis_sfn" {
  name_prefix = "${var.name_prefix}-events-analysis-sfn-"
  role        = aws_iam_role.eventbridge_analysis.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "AllowStartAnalysisExecution"
      Effect   = "Allow"
      Action   = ["states:StartExecution"]
      Resource = aws_sfn_state_machine.analysis.arn
    }]
  })
}

resource "aws_iam_role" "eventbridge_editorial" {
  name_prefix = "${var.name_prefix}-events-editorial-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
    }]
  })
  tags = local.tags
}

resource "aws_iam_role_policy" "eventbridge_editorial_sfn" {
  name_prefix = "${var.name_prefix}-events-editorial-sfn-"
  role        = aws_iam_role.eventbridge_editorial.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "AllowStartEditorialExecution"
      Effect   = "Allow"
      Action   = ["states:StartExecution"]
      Resource = aws_sfn_state_machine.editorial.arn
    }]
  })
}
