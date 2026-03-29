resource "aws_cloudwatch_log_group" "sfn" {
  count             = var.enable_step_functions_logging ? 1 : 0
  name              = "/aws/vendedlogs/states/${var.name_prefix}"
  retention_in_days = 30
  tags              = local.tags
}
resource "aws_security_group" "ecs_tasks" {
  name_prefix = "${var.name_prefix}-ecs-"
  description = "Sidekick newsroom ECS Fargate tasks"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, { Name = "${var.name_prefix}-ecs-tasks" })
}

resource "aws_cloudwatch_log_resource_policy" "sfn" {
  count       = var.enable_step_functions_logging ? 1 : 0
  policy_name = "${var.name_prefix}-sfn-logs"

  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "delivery.logs.amazonaws.com"
        }
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "${aws_cloudwatch_log_group.sfn[0].arn}:*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "step_functions_logs" {
  count = var.enable_step_functions_logging ? 1 : 0
  name  = "${var.name_prefix}-sfn-logs"
  role  = aws_iam_role.step_functions.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
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
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "${aws_cloudwatch_log_group.sfn[0].arn}:*"
      }
    ]
  })
}

locals {
  # Shared ECS network configuration for all RunTask states.
  sfn_network_cfg = {
    AwsvpcConfiguration = {
      Subnets        = var.ecs_task_subnet_ids
      SecurityGroups = [aws_security_group.ecs_tasks.id]
      AssignPublicIp = "DISABLED"
    }
  }

  sfn_extract_pdf_network_cfg = {
    AwsvpcConfiguration = {
      Subnets        = var.ecs_task_subnet_ids
      SecurityGroups = [aws_security_group.processing_pdf_tasks.id]
      AssignPublicIp = "DISABLED"
    }
  }

  # Ingestion: list-due → parallel spider runs → flat artifact list (no processing).
  sfn_ingestion_definition = {
    Comment = "Ingestion: list-due → spider Map → collated artifact refs"
    StartAt = "ListDueSpiders"
    States = {
      ListDueSpiders = {
        Type           = "Task"
        Resource       = "arn:aws:states:::lambda:invoke"
        TimeoutSeconds = 60
        Parameters = {
          FunctionName = aws_lambda_function.list_due_spiders.arn
          Payload      = {}
        }
        ResultSelector = {
          "spiders.$" = "$.Payload.spiders"
        }
        Next = "SpiderMap"
      }

      SpiderMap = {
        Type      = "Map"
        ItemsPath = "$.spiders"
        ItemSelector = {
          "source_id.$" = "$$.Map.Item.Value"
        }
        MaxConcurrency = var.sfn_max_concurrency_spiders
        Iterator = {
          StartAt = "RunSpider"
          States = {
            RunSpider = {
              Type           = "Task"
              Resource       = "arn:aws:states:::ecs:runTask.waitForTaskToken"
              TimeoutSeconds = 3600
              Parameters = {
                Cluster              = var.ecs_cluster_arn
                TaskDefinition       = aws_ecs_task_definition.ingestion.arn
                LaunchType           = "FARGATE"
                NetworkConfiguration = local.sfn_network_cfg
                Overrides = {
                  ContainerOverrides = [{
                    Name        = "worker"
                    "Command.$" = "States.Array('sfn-run', 'sidekick', 'spiders', 'run', $.source_id, '--output-json', '--min-date', '2026-01-01', '--max-items', '1')"
                    Environment = [{
                      Name      = "SFN_TASK_TOKEN"
                      "Value.$" = "$$.Task.Token"
                    }]
                  }]
                }
              }
              End = true
            }
          }
        }
        Next = "CollateArtifacts"
      }

      CollateArtifacts = {
        Type = "Pass"
        Parameters = {
          # Flatten [{ source_id, artifacts: [...] }, ...] → single artifacts array
          "artifacts.$" = "$[*].artifacts[*]"
        }
        End = true
      }
    }
  }

  # Processing SFN — recursive single-step design.
  #
  # Input:  { artifact_id, stage, content_type, media_type, status, processing_profile }
  # Output: { artifact_id, stage, content_type, media_type, status, processing_profile }
  #         (the last artifact produced — enrichment artifact after the full chain)
  #
  # Each execution handles exactly one transformation and, for non-terminal steps,
  # starts a child execution of itself with the new artifact. Typical paths are:
  #   raw (pending_acquisition) → acquire → raw (active) → normalize → processed → enrich
  #   processed (document-text) → enrich
  #
  # ECS tasks (and SQS transcription) use waitForTaskToken so work can return the new artifact
  # descriptor via sfn-run.  The $$SELF_ARN$$ placeholder is replaced at resource
  # creation time with the actual state machine ARN (see aws_sfn_state_machine below).
  sfn_processing_definition = {
    Comment = "Per-artifact processing: route → transform → recurse until enriched"
    StartAt = "RouteArtifact"
    States = {

      # ── routing ────────────────────────────────────────────────────────────────
      RouteArtifact = {
        Type = "Choice"
        Choices = [
          # 1. Pending acquisition (HLS/async) — must acquire before anything else
          {
            And = [
              { Variable = "$.stage", StringEquals = "raw" },
              { Variable = "$.status", StringEquals = "pending_acquisition" },
            ]
            Next = "AcquireArtifact"
          },
          # 2. Active raw evidence-only artifacts stop after preservation
          {
            And = [
              { Variable = "$.stage", StringEquals = "raw" },
              { Variable = "$.status", StringEquals = "active" },
              { Variable = "$.processing_profile", StringEquals = "evidence" },
            ]
            Next = "Done"
          },
          # 3. Active raw PDF → extract text
          {
            And = [
              { Variable = "$.stage", StringEquals = "raw" },
              { Variable = "$.status", StringEquals = "active" },
              { Variable = "$.media_type", StringEquals = "application/pdf" },
            ]
            Next = "ExtractPdf"
          },
          # 4. Active raw audio/video → transcribe to document-text
          {
            And = [
              { Variable = "$.stage", StringEquals = "raw" },
              { Variable = "$.status", StringEquals = "active" },
              {
                Or = [
                  { Variable = "$.media_type", StringMatches = "audio/*" },
                  { Variable = "$.media_type", StringMatches = "video/*" },
                ]
              },
            ]
            Next = "SubmitTranscriptionBatch"
          },
          # 5. Canonical processed text — ready for enrichment
          {
            And = [
              { Variable = "$.stage", StringEquals = "processed" },
              { Variable = "$.status", StringEquals = "active" },
              { Variable = "$.content_type", StringEquals = "document-text" },
            ]
            Next = "EnrichmentProfile"
          }
        ]
        # Already enriched or unrecognised — nothing to do
        Default = "Done"
      }

      # ── acquisition ────────────────────────────────────────────────────────────
      AcquireArtifact = {
        Type           = "Task"
        Resource       = "arn:aws:states:::ecs:runTask.waitForTaskToken"
        TimeoutSeconds = 7200
        Parameters = {
          Cluster              = var.ecs_cluster_arn
          TaskDefinition       = aws_ecs_task_definition.processing.arn
          LaunchType           = "FARGATE"
          NetworkConfiguration = local.sfn_network_cfg
          Overrides = {
            ContainerOverrides = [{
              Name        = "worker"
              "Command.$" = "States.Array('sfn-run', 'sidekick-process', 'acquire', $.artifact_id, '--output-json')"
              Environment = [{ Name = "SFN_TASK_TOKEN", "Value.$" = "$$.Task.Token" }]
            }]
          }
        }
        # acquire completes the same artifact in-place; returned descriptor has status=active
        Next = "Recurse"
      }

      # ── normalization ──────────────────────────────────────────────────────────
      ExtractPdf = {
        Type           = "Task"
        Resource       = "arn:aws:states:::ecs:runTask.waitForTaskToken"
        TimeoutSeconds = var.extract_pdf_timeout_seconds
        Parameters = {
          Cluster              = var.ecs_cluster_arn
          TaskDefinition       = aws_ecs_task_definition.processing_pdf.arn
          LaunchType           = "FARGATE"
          NetworkConfiguration = local.sfn_extract_pdf_network_cfg
          Overrides = {
            ContainerOverrides = [{
              Name        = "worker"
              "Command.$" = "States.Array('sfn-run', 'sidekick-process', 'extract-pdf', $.artifact_id, '--output-json')"
              Environment = [{ Name = "SFN_TASK_TOKEN", "Value.$" = "$$.Task.Token" }]
            }]
          }
        }
        Next = "Recurse"
      }

      SubmitTranscriptionBatch = {
        Type       = "Task"
        Resource   = "arn:aws:states:::batch:submitJob.sync"
        ResultPath = null
        Parameters = {
          JobQueue      = aws_batch_job_queue.transcription.name
          JobDefinition = aws_batch_job_definition.transcription.arn
          "JobName.$"   = "States.Format('transcription-{}', $.artifact_id)"
          ContainerOverrides = {
            "Command.$" = "States.Array('sfn-run', 'sidekick-transcribe', $.artifact_id, '--output-json')"
            Environment = [{
              Name  = "SFN_NEXT_EXECUTION_ARN"
              Value = "arn:aws:states:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:stateMachine:${var.name_prefix}-processing"
            }]
          }
        }
        Next = "Done"
      }

      # ── recursion ──────────────────────────────────────────────────────────────
      # Each normalization step returns a new artifact descriptor.  We start a child
      # execution of this same state machine with that descriptor as input.
      Recurse = {
        Type     = "Task"
        Resource = "arn:aws:states:::states:startExecution.sync:2"
        Parameters = {
          StateMachineArn = "$$SELF_ARN$$"
          Input = {
            "artifact_id.$"        = "$.artifact_id"
            "stage.$"              = "$.stage"
            "content_type.$"       = "$.content_type"
            "media_type.$"         = "$.media_type"
            "status.$"             = "$.status"
            "processing_profile.$" = "$.processing_profile"
          }
        }
        # Parse the child execution's stringified output, then surface it
        ResultSelector = { "output.$" = "States.StringToJson($.Output)" }
        OutputPath     = "$.output"
        End            = true
      }

      # ── enrichment (terminal) ─────────────────────────────────────────────────
      EnrichmentProfile = {
        Type = "Choice"
        Choices = [
          {
            Variable     = "$.processing_profile"
            StringEquals = "evidence"
            Next         = "Done"
          },
        ]
        Default = "EntityExtract"
      }

      EntityExtract = {
        Type           = "Task"
        Resource       = "arn:aws:states:::ecs:runTask.waitForTaskToken"
        TimeoutSeconds = 900
        ResultPath     = "$.entity_extract_result"
        Parameters = {
          Cluster              = var.ecs_cluster_arn
          TaskDefinition       = aws_ecs_task_definition.processing.arn
          LaunchType           = "FARGATE"
          NetworkConfiguration = local.sfn_network_cfg
          Overrides = {
            ContainerOverrides = [{
              Name        = "worker"
              "Command.$" = "States.Array('sfn-run', 'sidekick-process', 'entity-extract', $.artifact_id, '--output-json')"
              Environment = [{ Name = "SFN_TASK_TOKEN", "Value.$" = "$$.Task.Token" }]
            }]
          }
        }
        Next = "ShouldRunSummary"
      }

      ShouldRunSummary = {
        Type = "Choice"
        Choices = [
          {
            Variable     = "$.processing_profile"
            StringEquals = "index"
            Next         = "Done"
          },
        ]
        Default = "Summary"
      }

      Summary = {
        Type           = "Task"
        Resource       = "arn:aws:states:::ecs:runTask.waitForTaskToken"
        TimeoutSeconds = 900
        Parameters = {
          Cluster              = var.ecs_cluster_arn
          TaskDefinition       = aws_ecs_task_definition.processing.arn
          LaunchType           = "FARGATE"
          NetworkConfiguration = local.sfn_network_cfg
          Overrides = {
            ContainerOverrides = [{
              Name        = "worker"
              "Command.$" = "States.Array('sfn-run', 'sidekick-process', 'summary', $.artifact_id, '--output-json')"
              Environment = [{ Name = "SFN_TASK_TOKEN", "Value.$" = "$$.Task.Token" }]
            }]
          }
        }
        Next = "Done"
      }

      Done = {
        Type = "Pass"
        End  = true
      }
    }
  }

  sfn_analysis_definition = {
    Comment = "Scope-oriented beat analysis: debounce artifact events, run beat agent, rerun if needed"
    StartAt = "Initialize"
    States = {
      Initialize = {
        Type = "Pass"
        Parameters = {
          "event.$"         = "$"
          "execution_arn.$" = "$$.Execution.Id"
        }
        Next = "UpsertScopeState"
      }

      UpsertScopeState = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.analysis_lambdas["analysis_upsert_scope"].arn
          Payload = {
            "detail.$"        = "$.event.detail"
            "execution_arn.$" = "$.execution_arn"
          }
        }
        ResultSelector = {
          "scope.$" = "$.Payload"
        }
        ResultPath = "$.scope_result"
        Next       = "ShouldSkip"
      }

      ShouldSkip = {
        Type = "Choice"
        Choices = [
          {
            Variable      = "$.scope_result.scope.skip"
            BooleanEquals = true
            Next          = "Done"
          },
          {
            Variable      = "$.scope_result.scope.owned_by_other"
            BooleanEquals = true
            Next          = "Done"
          },
        ]
        Default = "WaitDebounce"
      }

      WaitDebounce = {
        Type    = "Wait"
        Seconds = var.analysis_scope_debounce_seconds
        Next    = "ClaimScope"
      }

      ClaimScope = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.analysis_lambdas["analysis_claim_scope"].arn
          Payload = {
            "scope_key.$"     = "$.scope_result.scope.scope_key"
            "execution_arn.$" = "$.execution_arn"
          }
        }
        ResultSelector = {
          "claim.$" = "$.Payload"
        }
        ResultPath = "$.claim_result"
        Next       = "ClaimedScope"
      }

      ClaimedScope = {
        Type = "Choice"
        Choices = [
          {
            Variable      = "$.claim_result.claim.claimed"
            BooleanEquals = true
            Next          = "RunBeatAgent"
          },
        ]
        Default = "Done"
      }

      RunBeatAgent = {
        Type           = "Task"
        Resource       = "arn:aws:states:::ecs:runTask.waitForTaskToken"
        TimeoutSeconds = 1800
        Parameters = {
          Cluster              = var.ecs_cluster_arn
          TaskDefinition       = aws_ecs_task_definition.analysis.arn
          LaunchType           = "FARGATE"
          NetworkConfiguration = local.sfn_network_cfg
          Overrides = {
            ContainerOverrides = [{
              Name        = "worker"
              "Command.$" = "States.Array('sfn-run', 'sidekick-beat', 'brief', '--beat', $.claim_result.claim.beat, '--geo', $.claim_result.claim.geo, '--event-group', $.claim_result.claim.event_group, '--output-json')"
              Environment = [{ Name = "SFN_TASK_TOKEN", "Value.$" = "$$.Task.Token" }]
            }]
          }
        }
        ResultPath = "$.run_result"
        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.run_error"
          Next        = "ReleaseAfterFailure"
        }]
        Next = "RecordRunResult"
      }

      RecordRunResult = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.analysis_lambdas["analysis_record_run"].arn
          Payload = {
            "scope_key.$"            = "$.claim_result.claim.scope_key"
            "execution_arn.$"        = "$.execution_arn"
            "written_artifact_ids.$" = "$.run_result.written_artifact_ids"
          }
        }
        ResultSelector = {
          "record.$" = "$.Payload"
        }
        ResultPath = "$.record_result"
        Next       = "CheckForNewInputs"
      }

      CheckForNewInputs = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.analysis_lambdas["analysis_check_scope"].arn
          Payload = {
            "scope_key.$" = "$.claim_result.claim.scope_key"
          }
        }
        ResultSelector = {
          "check.$" = "$.Payload"
        }
        ResultPath = "$.check_result"
        Next       = "NeedsFollowupRun"
      }

      NeedsFollowupRun = {
        Type = "Choice"
        Choices = [
          {
            Variable      = "$.check_result.check.rerun_required"
            BooleanEquals = true
            Next          = "ShortFollowupWait"
          },
        ]
        Default = "WaitQuietPeriod"
      }

      ShortFollowupWait = {
        Type    = "Wait"
        Seconds = var.analysis_scope_followup_seconds
        Next    = "ClaimScope"
      }

      WaitQuietPeriod = {
        Type    = "Wait"
        Seconds = var.analysis_scope_quiet_period_seconds
        Next    = "CheckQuietPeriod"
      }

      CheckQuietPeriod = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.analysis_lambdas["analysis_check_scope"].arn
          Payload = {
            "scope_key.$" = "$.claim_result.claim.scope_key"
          }
        }
        ResultSelector = {
          "check.$" = "$.Payload"
        }
        ResultPath = "$.quiet_check_result"
        Next       = "QuietPeriodStable"
      }

      QuietPeriodStable = {
        Type = "Choice"
        Choices = [
          {
            Variable      = "$.quiet_check_result.check.rerun_required"
            BooleanEquals = true
            Next          = "ClaimScope"
          },
        ]
        Default = "ReleaseScope"
      }

      ReleaseScope = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.analysis_lambdas["analysis_release_scope"].arn
          Payload = {
            "scope_key.$"     = "$.claim_result.claim.scope_key"
            "execution_arn.$" = "$.execution_arn"
          }
        }
        ResultPath = null
        Next       = "Done"
      }

      ReleaseAfterFailure = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.analysis_lambdas["analysis_release_scope"].arn
          Payload = {
            "scope_key.$"     = "$.claim_result.claim.scope_key"
            "execution_arn.$" = "$.execution_arn"
            "keep_dirty"      = true
            "error.$"         = "$.run_error.Cause"
          }
        }
        ResultPath = null
        Next       = "Done"
      }

      Done = {
        Type = "Pass"
        End  = true
      }
    }
  }

  sfn_editorial_definition = {
    Comment = "Per-candidate editorial orchestration: gate candidate → run editor agent → record result"
    StartAt = "PrepareEditorCandidate"
    States = {
      PrepareEditorCandidate = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.analysis_lambdas["editor_prepare_candidate"].arn
          Payload = {
            "detail.$" = "$.detail"
          }
        }
        ResultSelector = {
          "candidate.$" = "$.Payload"
        }
        ResultPath = "$.prepare_result"
        Next       = "ShouldRunEditor"
      }

      ShouldRunEditor = {
        Type = "Choice"
        Choices = [
          {
            Variable      = "$.prepare_result.candidate.should_run"
            BooleanEquals = true
            Next          = "RunEditorAgent"
          },
        ]
        Default = "Done"
      }

      RunEditorAgent = {
        Type           = "Task"
        Resource       = "arn:aws:states:::ecs:runTask.waitForTaskToken"
        TimeoutSeconds = 1800
        Parameters = {
          Cluster              = var.ecs_cluster_arn
          TaskDefinition       = aws_ecs_task_definition.editor.arn
          LaunchType           = "FARGATE"
          NetworkConfiguration = local.sfn_network_cfg
          Overrides = {
            ContainerOverrides = [{
              Name        = "worker"
              "Command.$" = "States.Array('sfn-run', 'sidekick-editor', 'draft', '--candidate-id', $.prepare_result.candidate.candidate_id, '--output-json')"
              Environment = [{ Name = "SFN_TASK_TOKEN", "Value.$" = "$$.Task.Token" }]
            }]
          }
        }
        ResultPath = "$.run_result"
        Next       = "RecordEditorRun"
      }

      RecordEditorRun = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.analysis_lambdas["editor_record_run"].arn
          Payload = {
            "candidate_id.$"         = "$.prepare_result.candidate.candidate_id"
            "story_key.$"            = "$.prepare_result.candidate.story_key"
            "assignment_id.$"        = "$.prepare_result.candidate.assignment_id"
            "written_artifact_ids.$" = "$.run_result.written_artifact_ids"
          }
        }
        ResultSelector = {
          "record.$" = "$.Payload"
        }
        ResultPath = "$.record_result"
        Next       = "Done"
      }

      Done = {
        Type = "Pass"
        End  = true
      }
    }
  }
}

resource "aws_sfn_state_machine" "ingestion" {
  name     = "${var.name_prefix}-ingestion"
  role_arn = aws_iam_role.step_functions.arn
  tags     = local.tags

  definition = jsonencode(local.sfn_ingestion_definition)

  dynamic "logging_configuration" {
    for_each = var.enable_step_functions_logging ? [1] : []
    content {
      log_destination        = "${aws_cloudwatch_log_group.sfn[0].arn}:*"
      include_execution_data = true
      level                  = var.step_functions_log_level
    }
  }
}

resource "aws_sfn_state_machine" "processing" {
  name     = "${var.name_prefix}-processing"
  role_arn = aws_iam_role.step_functions.arn
  tags     = local.tags

  # Replace the $$SELF_ARN$$ placeholder with this state machine's own ARN.
  # We cannot reference aws_sfn_state_machine.processing.arn inside its own
  # definition block, so we use a known ARN pattern and replace at apply time.
  definition = replace(
    jsonencode(local.sfn_processing_definition),
    "\"$$SELF_ARN$$\"",
    "\"arn:aws:states:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:stateMachine:${var.name_prefix}-processing\""
  )

  dynamic "logging_configuration" {
    for_each = var.enable_step_functions_logging ? [1] : []
    content {
      log_destination        = "${aws_cloudwatch_log_group.sfn[0].arn}:*"
      include_execution_data = true
      level                  = var.step_functions_log_level
    }
  }
}

resource "aws_sfn_state_machine" "analysis" {
  name     = "${var.name_prefix}-analysis"
  role_arn = aws_iam_role.step_functions.arn
  tags     = local.tags

  definition = jsonencode(local.sfn_analysis_definition)

  dynamic "logging_configuration" {
    for_each = var.enable_step_functions_logging ? [1] : []
    content {
      log_destination        = "${aws_cloudwatch_log_group.sfn[0].arn}:*"
      include_execution_data = true
      level                  = var.step_functions_log_level
    }
  }
}

resource "aws_sfn_state_machine" "editorial" {
  name     = "${var.name_prefix}-editorial"
  role_arn = aws_iam_role.step_functions.arn
  tags     = local.tags

  definition = jsonencode(local.sfn_editorial_definition)

  dynamic "logging_configuration" {
    for_each = var.enable_step_functions_logging ? [1] : []
    content {
      log_destination        = "${aws_cloudwatch_log_group.sfn[0].arn}:*"
      include_execution_data = true
      level                  = var.step_functions_log_level
    }
  }
}


resource "aws_cloudwatch_event_rule" "analysis_artifact_written" {
  name        = "${var.name_prefix}-analysis-artifact-written"
  description = "Start analysis scope workflow for processed summary/entity-extract artifacts."
  event_pattern = jsonencode({
    source        = ["sidekick-pipeline"]
    "detail-type" = ["artifact_written"]
    detail = {
      stage        = ["processed"]
      status       = ["active"]
      content_type = ["summary", "entity-extract"]
    }
  })
  tags = local.tags
}

resource "aws_cloudwatch_event_target" "analysis_artifact_written" {
  rule     = aws_cloudwatch_event_rule.analysis_artifact_written.name
  arn      = aws_sfn_state_machine.analysis.arn
  role_arn = aws_iam_role.eventbridge_analysis.arn
}

resource "aws_cloudwatch_event_rule" "editorial_artifact_written" {
  name        = "${var.name_prefix}-editorial-artifact-written"
  description = "Start editorial workflow for active story-candidate artifacts."
  event_pattern = jsonencode({
    source        = ["sidekick-pipeline"]
    "detail-type" = ["artifact_written"]
    detail = {
      stage        = ["analysis"]
      status       = ["active"]
      content_type = ["story-candidate"]
    }
  })
  tags = local.tags
}

resource "aws_cloudwatch_event_target" "editorial_artifact_written" {
  rule     = aws_cloudwatch_event_rule.editorial_artifact_written.name
  arn      = aws_sfn_state_machine.editorial.arn
  role_arn = aws_iam_role.eventbridge_editorial.arn
}

# EventBridge Scheduler — triggers the pipeline on a configurable schedule
resource "aws_scheduler_schedule" "pipeline" {
  name       = "${var.name_prefix}-pipeline"
  group_name = "default"

  state = "DISABLED"
  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = var.sfn_schedule_expression

  target {
    arn      = aws_sfn_state_machine.ingestion.arn
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({ workload = "processing" })
  }
}
