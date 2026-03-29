# Transcription service (Phase 3 STT)

Runs **WhisperX** on **active** raw `audio/*` and `video/*` artifacts and writes **`document-text`** processed rows (plain dialog text in object storage).

## CLI

From repo root (with `DATABASE_URL`, object-store env vars, and **`HF_TOKEN`** for pyannote diarization):

```bash
cd services/transcription
uv run sidekick-transcribe transcribe ARTIFACT_ID
```

Options:

- `--whisper-model` — model size (default `base`; production often `large-v3`).
- Device is chosen automatically: **CUDA** when available, else **CPU** (`processor.get_backend()`).

### Batch worker (SQS + Step Functions task tokens)

Used by **AWS Batch** on GPU instances: loads the Whisper model once, long-polls SQS, transcribes each message, and calls `states:SendTaskSuccess` / `SendTaskFailure` with the Step Functions task token from the message body.

```bash
sidekick-transcribe worker --queue-url "$TRANSCRIPTION_QUEUE_URL"
```

Environment variables: `TRANSCRIPTION_QUEUE_URL`, `WHISPER_MODEL`, `TRANSCRIPTION_IDLE_TIMEOUT` (seconds idle before exit; default 300).

## Docker

Build GPU image from repo root (see [`Dockerfile`](Dockerfile)). Use with **AWS Batch** on GPU instances, not Fargate.

WhisperX model assets are preloaded at build time. Pass the Hugging Face token as a BuildKit secret so token values are not written into layers:

```bash
DOCKER_BUILDKIT=1 docker build \
  --secret id=hf_token,env=HF_TOKEN \
  --build-arg WHISPER_MODEL_PRELOAD=base \
  --build-arg WHISPER_ALIGN_LANG=en \
  -f services/transcription/Dockerfile .
```

- `WHISPER_MODEL_PRELOAD` should match your expected runtime `--whisper-model`.
- `WHISPER_ALIGN_LANG` preloads one alignment model (WhisperX alignment is language-specific).
- Diarization weights are also preloaded during build.

## Architecture

- `router.py` — raw+active+audio/video validation
- `processor.py` — `load_transcription_model`, `transcribe_audio_file`, `process_audio_to_transcript` (callers supply a loaded model)
- `runtime.py` — `ArtifactStore` / `ObjectStore` / Step Functions client wiring

Downstream enrichment (`summary`, `entity-extract`) stays in **`services/processing`**.
