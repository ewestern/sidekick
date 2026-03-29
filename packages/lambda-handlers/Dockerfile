# Multi-stage image for AWS Lambda (Python), following:
# https://docs.astral.sh/uv/guides/integration/aws-lambda/
#
# Build from the repository root:
#   docker buildx build --platform linux/amd64 -f packages/lambda-handlers/Dockerfile -t list-due-lambda .

FROM ghcr.io/astral-sh/uv:0.11.0 AS uv

FROM public.ecr.aws/lambda/python:3.13 AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_INSTALLER_METADATA=1
ENV UV_LINK_MODE=copy

WORKDIR /workspace

COPY pyproject.toml uv.lock ./
COPY packages/core/pyproject.toml packages/core/pyproject.toml
COPY packages/core/src packages/core/src
COPY packages/lambda-handlers/pyproject.toml packages/lambda-handlers/pyproject.toml
COPY packages/lambda-handlers/src packages/lambda-handlers/src

RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    uv export --package sidekick-lambda-handlers --frozen --no-dev --no-editable --no-hashes -o requirements.txt && \
    uv pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}" && \
    uv pip install packages/core packages/lambda-handlers --no-deps --target "${LAMBDA_TASK_ROOT}"

FROM public.ecr.aws/lambda/python:3.13

COPY --from=builder ${LAMBDA_TASK_ROOT} ${LAMBDA_TASK_ROOT}

CMD ["sidekick_lambda.handlers.list_due.handler"]
