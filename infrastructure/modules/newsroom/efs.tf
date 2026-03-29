resource "aws_security_group" "efs_extract_pdf" {
  count = var.enable_extract_pdf_efs ? 1 : 0

  name_prefix = "${var.name_prefix}-efs-"
  description = "EFS for Marker model cache"
  vpc_id      = var.vpc_id

  tags = merge(local.tags, { Name = "${var.name_prefix}-efs-extract-pdf" })
}

resource "aws_security_group_rule" "efs_extract_pdf_ingress" {
  count = var.enable_extract_pdf_efs ? 1 : 0

  type                     = "ingress"
  from_port                = 2049
  to_port                  = 2049
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.processing_pdf_tasks.id
  security_group_id        = aws_security_group.efs_extract_pdf[0].id
  description              = "NFS from Marker PDF extraction tasks"
}

resource "aws_efs_file_system" "extract_pdf" {
  count = var.enable_extract_pdf_efs ? 1 : 0

  creation_token = "${var.name_prefix}-extract-pdf"
  encrypted      = true

  tags = merge(local.tags, { Name = "${var.name_prefix}-extract-pdf" })
}

resource "aws_efs_mount_target" "extract_pdf" {
  for_each = var.enable_extract_pdf_efs ? toset(var.ecs_task_subnet_ids) : toset([])

  file_system_id  = aws_efs_file_system.extract_pdf[0].id
  subnet_id       = each.value
  security_groups = [aws_security_group.efs_extract_pdf[0].id]
}

resource "aws_efs_access_point" "extract_pdf" {
  count = var.enable_extract_pdf_efs ? 1 : 0

  file_system_id = aws_efs_file_system.extract_pdf[0].id

  posix_user {
    gid = 1000
    uid = 1000
  }

  root_directory {
    path = var.extract_pdf_model_cache_path

    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "0755"
    }
  }

  tags = merge(local.tags, { Name = "${var.name_prefix}-extract-pdf-cache" })
}
