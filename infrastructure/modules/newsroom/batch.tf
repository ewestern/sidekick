# Transcription: AWS Batch (GPU). Processing Step Functions submits jobs directly;
# sfn-run handles the SFN callback by starting a new processing execution.

# ── Batch service + EC2 instance + Spot Fleet roles ──────────────────────────
resource "aws_iam_role" "batch_service" {
  name_prefix = "${var.name_prefix}-batch-svc-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "batch.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "batch_service" {
  role       = aws_iam_role.batch_service.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
}

resource "aws_iam_role" "batch_ec2" {
  name_prefix = "${var.name_prefix}-batch-ec2-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "batch_ec2_ecs" {
  role       = aws_iam_role.batch_ec2.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_role_policy_attachment" "batch_ec2_ecr" {
  role       = aws_iam_role.batch_ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_instance_profile" "batch_ec2" {
  name_prefix = "${var.name_prefix}-batch-inst-"
  role        = aws_iam_role.batch_ec2.name
  tags        = local.tags
}

resource "aws_iam_role" "spot_fleet" {
  name_prefix = "${var.name_prefix}-batch-spot-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "spotfleet.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "spot_fleet" {
  role       = aws_iam_role.spot_fleet.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2SpotFleetTaggingRole"
}

# ── Security group for Batch EC2 instances ───────────────────────────────────
resource "aws_security_group" "batch_compute" {
  name_prefix = "${var.name_prefix}-batch-"
  description = "Sidekick transcription Batch GPU instances"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, { Name = "${var.name_prefix}-batch-compute" })
}

# ── Compute environment + job queue ──────────────────────────────────────────
resource "aws_batch_compute_environment" "transcription" {
  type         = "MANAGED"
  state        = "ENABLED"
  service_role = aws_iam_role.batch_service.arn

  compute_resources {
    type = "SPOT"
    #allocation_strategy = "SPOT_CAPACITY_OPTIMIZED"
    #bid_percentage      = 100
    spot_iam_fleet_role = aws_iam_role.spot_fleet.arn
    instance_role       = aws_iam_instance_profile.batch_ec2.arn
    instance_type       = ["g4dn.xlarge"]
    #min_vcpus           = 0
    max_vcpus = 16
    #desired_vcpus       = 0
    subnets            = var.ecs_task_subnet_ids
    security_group_ids = [aws_security_group.batch_compute.id]
    #tags = merge(local.tags, {
    #  Name = "${var.name_prefix}-batch-transcription"
    #})
  }

  tags = local.tags

  depends_on = [
    aws_iam_role_policy_attachment.batch_service,
    aws_iam_role_policy_attachment.spot_fleet,
  ]
}

resource "aws_batch_job_queue" "transcription" {
  name     = "${var.name_prefix}-transcription"
  state    = "ENABLED"
  priority = 1

  compute_environment_order {
    order               = 1
    compute_environment = aws_batch_compute_environment.transcription.arn
  }

  tags = local.tags
}

# ── CloudWatch Logs for Batch jobs ───────────────────────────────────────────
resource "aws_cloudwatch_log_group" "batch_transcription" {
  name              = "/aws/batch/${var.name_prefix}-transcription"
  retention_in_days = 30
  tags              = local.tags
}

resource "aws_iam_role_policy" "ecs_task_batch_transcription_logs" {
  name_prefix = "${var.name_prefix}-batch-logs-"
  role        = aws_iam_role.ecs_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "BatchTranscriptionLogs"
      Effect = "Allow"
      Action = [
        "logs:CreateLogStream",
        "logs:PutLogEvents",
      ]
      Resource = "${aws_cloudwatch_log_group.batch_transcription.arn}:*"
    }]
  })
}

# ── Job definition (GPU) ───────────────────────────────────────────────────
resource "aws_batch_job_definition" "transcription" {
  name                  = "${var.name_prefix}-transcription-gpu"
  type                  = "container"
  platform_capabilities = ["EC2"]

  container_properties = jsonencode({
    image      = "${aws_ecr_repository.workloads["transcription"].repository_url}:latest"
    jobRoleArn = aws_iam_role.ecs_task.arn
    resourceRequirements = [
      { type = "VCPU", value = "4" },
      { type = "MEMORY", value = "15000" },
      { type = "GPU", value = "1" },
    ]
    environment = concat(
      [
        { name = "WHISPER_MODEL", value = var.whisper_model },
        { name = "HF_TOKEN", value = var.hf_token },
        { name = "OPENAI_API_KEY", value = var.openai_api_key },
      ],
      [for k, v in local.task_environment : { name = k, value = v }]
    )
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.batch_transcription.name
        awslogs-region        = data.aws_region.current.name
        awslogs-stream-prefix = "transcription"
      }
    }
  })

  tags = local.tags
}
