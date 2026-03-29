#!/usr/bin/env python3
"""SFN task-token wrapper.

Runs the given command, then sends its stdout as the Step Functions task
success payload (or sends task failure on non-zero exit).

When SFN_TASK_TOKEN is not set the script is a transparent passthrough —
stdout, stderr, and exit code are forwarded unchanged.  This makes local
development identical to the SFN-managed path without any extra flags.

Usage (in Step Functions ContainerOverrides):
    Command: ["sfn-run", "sidekick-process", "extract-pdf", <artifact_id>, "--output-json"]

The wrapped command must write valid JSON to stdout when --output-json is
passed.  sfn-run captures that JSON and sends it verbatim as the task output.
"""

from __future__ import annotations

import boto3  # imported lazily — not available in all local envs
import os
import subprocess
import sys


def main() -> None:
    token = os.environ.get("SFN_TASK_TOKEN")
    next_arn = os.environ.get("SFN_NEXT_EXECUTION_ARN")
    cmd = sys.argv[1:]

    if not cmd:
        print("Usage: sfn-run <command> [args...]", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run(cmd, capture_output=True, text=True)

    if token:
        sfn = boto3.client("stepfunctions")
        if result.returncode == 0:
            sfn.send_task_success(
                taskToken=token, output=result.stdout.strip())
        else:
            cause = (result.stderr or result.stdout)[:1024].strip()
            sfn.send_task_failure(
                taskToken=token, error="TaskFailed", cause=cause)
    elif next_arn and result.returncode == 0:
        sfn = boto3.client("stepfunctions")
        sfn.start_execution(StateMachineArn=next_arn,
                            input=result.stdout.strip())

    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
