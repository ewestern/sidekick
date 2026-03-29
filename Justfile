aws_region  := "us-west-2"
aws_profile := "sidekick"
ecs_cluster := "sidekick-production"
api_service := "api-production-service"

# Resolve ECR registry from AWS account ID at recipe-invocation time
ecr_registry := `aws sts get-caller-identity --profile sidekick --query Account --output text | tr -d '[:space:]'` + ".dkr.ecr.us-west-2.amazonaws.com"

# List available recipes
default:
    @just --list

# --- ECR auth ---

# Authenticate Docker to ECR
ecr-login:
    aws ecr get-login-password --region {{aws_region}} --profile {{aws_profile}} \
        | docker login --username AWS --password-stdin {{ecr_registry}}

# --- Build ---

# Build a single service image: just build <service>
# Services: ingestion | processing | transcription | api | lambda | beat | editor
build service:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ "{{service}}" = "lambda" ]; then
      docker build \
        --platform linux/amd64 \
        -f packages/lambda-handlers/Dockerfile \
        -t sidekick/lambda-handlers:latest \
        .
    elif [ "{{service}}" = "transcription" ]; then
      : "${HF_TOKEN:?HF_TOKEN must be set for transcription image build}"
      DOCKER_BUILDKIT=1 docker build \
        --secret id=hf_token,env=HF_TOKEN \
        --build-arg WHISPER_MODEL_PRELOAD=base \
        --build-arg WHISPER_ALIGN_LANG=en \
        --platform linux/amd64 \
        -f services/transcription/Dockerfile \
        -t sidekick/transcription:latest \
        .
    else
      docker build \
        --platform linux/amd64 \
        -f services/{{service}}/Dockerfile \
        -t sidekick/{{service}}:latest \
        .
    fi

# Build all services with Dockerfiles
build-all:
    just build ingestion
    just build processing
    just build transcription
    just build api
    just build lambda
    just build beat
    just build editor

# --- Push ---

# Tag and push a single service image to ECR: just push <service>
push service: ecr-login
    #!/usr/bin/env bash
    set -euo pipefail
    if [ "{{service}}" = "lambda" ]; then
      docker tag sidekick/lambda-handlers:latest {{ecr_registry}}/sidekick/lambda-handlers:latest
      docker push {{ecr_registry}}/sidekick/lambda-handlers:latest
    else
      docker tag sidekick/{{service}}:latest {{ecr_registry}}/sidekick/{{service}}:latest
      docker push {{ecr_registry}}/sidekick/{{service}}:latest
    fi

# Push all services to ECR
push-all: ecr-login
    just push ingestion
    just push processing
    just push transcription
    just push api
    just push beat
    just push editor
    just push lambda

# --- Deploy ---

# Build, push, and (for API) force a new ECS deployment: just deploy <service>
deploy service: (build service) (push service)
    #!/usr/bin/env bash
    set -euo pipefail
    if [ "{{service}}" = "api" ]; then
        echo "Forcing new deployment of ECS service {{api_service}}..."
        aws ecs update-service \
            --cluster {{ecs_cluster}} \
            --service {{api_service}} \
            --force-new-deployment \
            --region {{aws_region}} \
            --profile {{aws_profile}} \
            --output text --query 'service.serviceName'
        echo "Deployment triggered."
    elif [ "{{service}}" = "lambda-handlers" ]; then
        echo "lambda-handlers image pushed. Run terraform apply so the Lambda picks up the new digest (aws_ecr_image)."
    else
        echo "{{service}} image pushed; Step Functions will use it on next RunTask."
    fi

# Build and push all services
deploy-all:
    just deploy ingestion
    just deploy processing
    just deploy transcription
    just deploy api
    just deploy lambda
    just deploy beat
    just deploy editor

# --- Terraform ---

# Run terraform plan in the production environment
tf-plan *args:
    cd infrastructure/environments/production && \
        terraform plan {{args}}

# Run terraform apply in the production environment
tf-apply *args:
    cd infrastructure/environments/production && \
        terraform apply {{args}}

# Run terraform init in the production environment
tf-init:
    cd infrastructure/environments/production && \
        terraform init
