resource "aws_cloudwatch_log_group" "ecs" {
  name              = local.log_group_name
  retention_in_days = 30
  tags              = local.tags
}

resource "aws_security_group" "processing_pdf_tasks" {
  name_prefix = "${var.name_prefix}-processing-pdf-"
  description = "Sidekick Marker PDF extraction tasks"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, { Name = "${var.name_prefix}-processing-pdf-tasks" })
}

resource "aws_ecs_task_definition" "ingestion" {
  family                   = local.workload_families.ingestion
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "worker"
      image     = "${aws_ecr_repository.workloads["ingestion"].repository_url}:latest"
      essential = true
      command   = ["sleep", "3600"]
      environment = [
        for k, v in local.task_environment : { name = k, value = v }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = "ingestion"
        }
      }
    }
  ])

  tags = local.tags
}

resource "aws_ecs_task_definition" "processing" {
  family                   = local.workload_families.processing
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "worker"
      image     = "${aws_ecr_repository.workloads["processing"].repository_url}:latest"
      essential = true
      command   = ["sidekick-process", "process"]
      #merge
      environment = concat(
        [for k, v in local.task_environment : { name = k, value = v }],
        [{ name = "OPENAI_API_KEY", value = var.openai_api_key }]
      )
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = "processing"
        }
      }
    }
  ])

  tags = local.tags
}

resource "aws_ecs_task_definition" "processing_pdf" {
  family                   = local.workload_families.processing_pdf
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.extract_pdf_task_cpu
  memory                   = var.extract_pdf_task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  dynamic "volume" {
    for_each = var.enable_extract_pdf_efs ? [1] : []
    content {
      name = "marker-model-cache"

      efs_volume_configuration {
        file_system_id     = aws_efs_file_system.extract_pdf[0].id
        root_directory     = "/"
        transit_encryption = "ENABLED"

        authorization_config {
          access_point_id = aws_efs_access_point.extract_pdf[0].id
          iam             = "ENABLED"
        }
      }
    }
  }

  container_definitions = jsonencode([
    {
      name      = "worker"
      image     = "${aws_ecr_repository.workloads["processing"].repository_url}:latest"
      essential = true
      command   = ["sidekick-process", "process"]
      environment = concat(
        [for k, v in local.task_environment : { name = k, value = v }],
        [{ name = "OPENAI_API_KEY", value = var.openai_api_key }],
        var.enable_extract_pdf_efs ? [
          { name = "HF_HOME", value = "/mnt/models/hf" },
          { name = "HUGGINGFACE_HUB_CACHE", value = "/mnt/models/hf/hub" },
          { name = "TORCH_HOME", value = "/mnt/models/torch" },
          { name = "TRANSFORMERS_CACHE", value = "/mnt/models/transformers" },
        ] : []
      )
      mountPoints = var.enable_extract_pdf_efs ? [{
        sourceVolume  = "marker-model-cache"
        containerPath = "/mnt/models"
        readOnly      = false
      }] : []
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = "processing-pdf"
        }
      }
    }
  ])

  tags = local.tags
}

resource "aws_ecs_task_definition" "analysis" {
  family                   = local.workload_families.analysis
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "worker"
      image     = "${aws_ecr_repository.workloads["analysis"].repository_url}:latest"
      essential = true
      command   = ["sleep", "3600"]
      environment = concat(
        [for k, v in local.task_environment : { name = k, value = v }],
        [{ name = "OPENAI_API_KEY", value = var.openai_api_key }]
      )
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = "analysis"
        }
      }
    }
  ])

  tags = local.tags
}

resource "aws_ecs_task_definition" "editor" {
  family                   = local.workload_families.editor
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "worker"
      image     = "${aws_ecr_repository.workloads["editor"].repository_url}:latest"
      essential = true
      command   = ["sleep", "3600"]
      environment = concat(
        [for k, v in local.task_environment : { name = k, value = v }],
        [{ name = "OPENAI_API_KEY", value = var.openai_api_key }]
      )
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = "editor"
        }
      }
    }
  ])

  tags = local.tags
}
