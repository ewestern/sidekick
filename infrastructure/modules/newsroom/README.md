# `newsroom` Terraform module

Core execution and orchestration primitives for the Sidekick pipeline on AWS:

- **ECS Fargate** — three task definition families (`ingestion`, `processing`, `analysis`) with per-run overrides via `RunTask` parameters.
- **AWS Batch (GPU)** — **transcription** uses the **sidekick-transcription** ECR image on **g4dn.xlarge** SPOT: the processing Step Functions state machine calls `batch:submitJob`, then `sqs:sendMessage.waitForTaskToken`; a long-running `sidekick-transcribe worker` drains the queue and calls Step Functions `SendTaskSuccess` / `SendTaskFailure` per message.
- **Lambda (list-due)** — Container image from `packages/lambda-handlers/Dockerfile`; build and push with the repo **Justfile** (`just push lambda-list-due`) to ECR `sidekick/lambda-list-due:latest`. Terraform does **not** run Docker; it uses the [`aws_ecr_image`](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ecr_image) data source (tag `latest`) and sets `aws_lambda_function.image_uri` to the resolved **`image_uri`** (digest-pinned) so applies pick up new pushes. **Bootstrap:** ensure at least one image exists in that repository before a plan that includes the Lambda (e.g. create the ECR repo, push once, then apply). The ingestion Step Functions `ListDueSpiders` state invokes this function (DB-backed due list via `sidekick-core`).
- **Step Functions** — scheduled ingestion/orchestration, per-artifact `processing`, and scope-oriented `analysis` for event-group beat runs.

Current workflow shape:

- `processing` is per artifact:
  - raw acquisition / normalization
  - direct-ingested `processed/document-text` artifacts skip normalization and enter enrichment immediately
  - `full` profile enrichment runs `entity-extract` then `summary`
  - `index` runs `entity-extract` only
  - `structured` runs `structured-data`
  - `evidence` stops after raw preservation
- `analysis` is per scope:
  - triggered by processed `summary` / `entity-extract` writes
  - keyed by event-group scope
  - debounces bursts of upstream artifacts
  - runs the beat agent on ECS
  - reruns if new inputs arrive during execution
  - performs one quiet-period reevaluation before releasing the scope

## v1 assumptions

- You already have a **VPC** and **ECS cluster**; the module does not create them.
- You supply **subnet IDs** (typically the same private subnets) for Fargate tasks when you wire `RunTask` from Step Functions or EventBridge.
- Default container images are **BusyBox** placeholders so Terraform can apply before real service images exist; replace with your ECR URIs.
- Step Functions **CloudWatch logging** is **off** by default (`enable_step_functions_logging = false`) to keep first applies simple; set `true` for execution logs (requires the created log resource policy + IAM policy in this module).

## Usage

```hcl
module "newsroom" {
  source = "../../modules/newsroom"

  name_prefix       = "griffin-production-newsroom"
  vpc_id            = data.aws_vpc.selected.id
  ecs_cluster_arn   = data.aws_ecs_cluster.shared.arn
  ecs_task_subnet_ids = ["subnet-aaa", "subnet-bbb"] # Fargate awsvpc

  processing_container_image    = "123456789012.dkr.ecr.us-west-2.amazonaws.com/sidekick/processing:latest"
  transcription_container_image = "123456789012.dkr.ecr.us-west-2.amazonaws.com/sidekick/transcription:latest"

  tags = {
    Workload = "newsroom"
  }
}
```

## Inputs (summary)

| Name | Description |
|------|-------------|
| `name_prefix` | Prefix for named resources in the newsroom module. |
| `vpc_id` | VPC for ECS task ENIs and module security groups. |
| `ecs_cluster_arn` | Target cluster for `ecs:RunTask`. |
| `ecs_task_subnet_ids` | Subnets for Fargate tasks. |
| `*_container_image` / `*_container_command` | Per–workload-class defaults. |
| `task_cpu` / `task_memory` | Fargate sizing. |
| `enable_step_functions_logging` | Toggle Step Functions → CloudWatch Logs. |

See `variables.tf` for defaults and validation.

## Outputs

- Task definition ARNs / families by workload class (Fargate only; transcription is Batch — see `batch_job_definition_transcription_arn`).
- ECS task and execution role ARNs.
- ECS tasks security group ID (attach to `RunTask` ENIs).
- Step Functions state machine ARNs and names for processing and analysis.
- List-due Lambda function ARN and its security group ID (for RDS ingress rules).

## Next steps (not in this module)

- Wire additional **EventBridge** rules to Step Functions or ECS using your `artifact_written` event contract as new workloads are added.
- Add **S3**, **SQS**, and **Secrets Manager** ARNs to the ECS task role policy as services need them.
