"""CLI for speech-to-text — ``sidekick-transcribe``."""

from __future__ import annotations

import json
import logging
import sys
import time

import boto3
import typer

from sidekick.transcription.processor import (
    get_backend,
    load_transcription_model,
    process_audio_to_transcript,
)
from sidekick.transcription.router import UnsupportedTranscriptionError
from sidekick.transcription.runtime import build_transcription_runtime

app = typer.Typer(
    no_args_is_help=True, help="Speech-to-text — raw audio/video to document-text"
)
logger = logging.getLogger(__name__)


def _artifact_descriptor_json(store, artifact_id: str) -> str:
    row = store.read_row(artifact_id)
    return json.dumps(
        {
            "artifact_id": artifact_id,
            "stage": row.stage,
            "content_type": row.content_type,
            "media_type": row.media_type,
            "status": row.status,
            "processing_profile": row.processing_profile,
        }
    )


@app.command("transcribe")
def cmd_transcribe(
    artifact_id: str,
    whisper_model: str = typer.Option(
        "base",
        "--whisper-model",
        help="WhisperX model size (e.g. base, large-v3).",
    ),
    output_json: bool = typer.Option(False, "--output-json"),
) -> None:
    """Transcribe an **active** raw audio/video artifact to ``document-text``."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    store, _, _, _ = build_transcription_runtime()
    device = get_backend()
    model = load_transcription_model(whisper_model, device=device)
    try:
        new_id = process_audio_to_transcript(artifact_id, store, model=model)
    except UnsupportedTranscriptionError as exc:
        print(str(exc), file=sys.stderr)
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # pragma: no cover
        logger.exception("Transcription failed")
        print(str(exc), file=sys.stderr)
        raise typer.Exit(code=1) from exc
    if output_json:
        print(_artifact_descriptor_json(store, new_id))
    else:
        typer.echo(
            typer.style(
                f"Wrote document-text artifact {new_id}", fg=typer.colors.GREEN
            )
        )


@app.command("worker")
def cmd_worker(
    queue_url: str = typer.Option(
        ...,
        "--queue-url",
        envvar="TRANSCRIPTION_QUEUE_URL",
        help="SQS queue URL for transcription jobs (artifact_id + task_token).",
    ),
    whisper_model: str = typer.Option(
        "base",
        "--whisper-model",
        envvar="WHISPER_MODEL",
        help="WhisperX model size (e.g. base, large-v3).",
    ),
    idle_timeout: int = typer.Option(
        300,
        "--idle-timeout",
        envvar="TRANSCRIPTION_IDLE_TIMEOUT",
        help="Exit after this many seconds with no messages received.",
    ),
) -> None:
    """Poll SQS, transcribe with one loaded model, callback Step Functions per job."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    store, _, _, sfn = build_transcription_runtime()
    sqs = boto3.client("sqs")
    device = get_backend()
    model = load_transcription_model(whisper_model, device=device)

    idle_since: float | None = None
    logger.info(
        "Transcription worker started model=%s device=%s queue=%s",
        whisper_model,
        device,
        queue_url,
    )

    while True:
        resp = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
            AttributeNames=["ApproximateReceiveCount"],
        )
        messages = resp.get("Messages", [])
        if not messages:
            if idle_since is None:
                idle_since = time.time()
            elif time.time() - idle_since > idle_timeout:
                logger.info("Idle for %s s — exiting", idle_timeout)
                break
            continue

        idle_since = None
        msg = messages[0]
        receipt = msg["ReceiptHandle"]
        try:
            body = json.loads(msg["Body"])
        except json.JSONDecodeError:
            logger.exception("Invalid SQS message body: %s", msg.get("Body"))
            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
            continue

        artifact_id = body.get("artifact_id")
        task_token = body.get("task_token")
        if not artifact_id or not task_token:
            logger.error(
                "Missing artifact_id or task_token in message: %s", body)
            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
            continue

        try:
            sfn.send_task_heartbeat(taskToken=task_token)
        except Exception as exc:  # pragma: no cover
            logger.warning("Heartbeat failed (continuing): %s", exc)

        try:
            new_id = process_audio_to_transcript(
                artifact_id, store, model=model)
            out = _artifact_descriptor_json(store, new_id)
            sfn.send_task_success(taskToken=task_token, output=out)
            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
            logger.info("Transcribed %s -> %s", artifact_id, new_id)
        except UnsupportedTranscriptionError as exc:
            sfn.send_task_failure(
                taskToken=task_token,
                error="UnsupportedTranscriptionError",
                cause=str(exc)[:1024],
            )
            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
        except ValueError as exc:
            sfn.send_task_failure(
                taskToken=task_token,
                error="ValueError",
                cause=str(exc)[:1024],
            )
            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
        except Exception as exc:  # pragma: no cover
            logger.exception("Transcription failed for %s", artifact_id)
            sfn.send_task_failure(
                taskToken=task_token,
                error="TranscriptionError",
                cause=str(exc)[:1024],
            )
            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
