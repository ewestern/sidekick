#!/usr/bin/env bash
# Connect to PostgreSQL from a running API ECS task via ECS Exec.
#
# Usage:
#   scripts/connect_db.sh
#   AWS_PROFILE=sidekick AWS_REGION=us-west-2 scripts/connect_db.sh
#   ECS_CLUSTER=<cluster-name-or-arn> ECS_SERVICE=<service-name> scripts/connect_db.sh

set -euo pipefail

AWS_PROFILE="${AWS_PROFILE:-sidekick}"
AWS_REGION="${AWS_REGION:-us-west-2}"
ECS_SERVICE="${ECS_SERVICE:-api-production-service}"
ECS_CLUSTER="${ECS_CLUSTER:-sidekick-production}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd aws


TASK_ARN="$(
  aws ecs list-tasks \
    --cluster "$ECS_CLUSTER" \
    --service-name "$ECS_SERVICE" \
    --desired-status RUNNING \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE" \
    --query 'taskArns[0]' \
    --output text
)"

if [[ -z "$TASK_ARN" || "$TASK_ARN" == "None" ]]; then
  echo "No running tasks found for service '$ECS_SERVICE' in cluster '$ECS_CLUSTER'." >&2
  exit 1
fi

echo "Connecting to task: $TASK_ARN"
echo "Cluster: $ECS_CLUSTER"
echo "Service: $ECS_SERVICE"

aws --region "$AWS_REGION" --profile "$AWS_PROFILE" ecs execute-command \
  --cluster "$ECS_CLUSTER" \
  --task "$TASK_ARN" \
  --container api \
  --interactive \
  --command "sh -lc 'psql \"\$DATABASE_URL\"'"
