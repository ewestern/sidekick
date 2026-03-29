# Processing service (Phase 3)

Acquisition workers complete `pending_acquisition` raw artifacts (e.g. HLS via **ffmpeg**). Processors write UTF-8 text to **object storage** via `ArtifactStore.write_with_bytes` — **`document-text`** (Markdown from Marker OCR / PDF extraction) and enrichment outputs such as **`entity-extract`** (JSON) and **`summary`** (Markdown). Audio/video transcription also writes **`document-text`** and lives in **`services/transcription`** (`sidekick-transcribe`).

## CLI

From repo root (with `DATABASE_URL`, `S3_BUCKET`, etc. set — same as ingestion):

```bash
cd services/processing
uv run sidekick-process acquire ARTIFACT_ID
uv run sidekick-process extract-pdf ARTIFACT_ID
uv run sidekick-process entity-extract ARTIFACT_ID
uv run sidekick-process summary ARTIFACT_ID
uv run sidekick-process seed-configs
```

- **acquire** — HLS stubs only (`.m3u8` / `.m3u` on `acquisition_url`). Requires `ffmpeg` on `PATH`.
- **extract-pdf** — active raw PDFs → `document-text`.
- **entity-extract** — enriches normalized text into the canonical extraction/index artifact.
- **summary** — enriches normalized text into Markdown synthesis, using the sibling `entity-extract` artifact as support context.
- **seed-configs** — seeds the processing agent config rows.
- For audio/video normalization use **`sidekick-transcribe`** from `services/transcription`.

## Architecture

- `router.py` — small eligibility helpers for raw acquisition/normalization routing: `can_acquire_hls_stub`, `resolve_active_raw_processor`
- `acquisition/hls.py` — ffmpeg capture + `ArtifactStore.complete_acquisition`
- `processors/pdf.py`, `processors/summary.py`, `processors/entity_extract.py`, `processors/structured_data.py` — write processed rows via `ArtifactStore.write_with_bytes`

Normalization (PDF / STT) MUST only run on **`stage=raw`** and **`status=active`**. Enrichment is orchestrated by Step Functions from **`document-text`** according to `processing_profile`. Spiders may also write **`stage=processed`** + **`document-text`** directly when they already have canonical plain text.

In the normal `full` flow:

1. `entity-extract` runs first on the normalized text artifact.
2. `summary` runs second on the same normalized text artifact.
3. `summary` looks up the sibling `entity-extract` artifact, uses it as support context in the prompt, and writes a summary artifact whose `derived_from` includes both the normalized text artifact and the sibling extraction artifact.

The enrichment commands themselves should not be treated as authoritative validators of enrichable `content_type`; orchestration is responsible for sending the correct artifact into each node. See [docs/ARTIFACT_STORE.md](../docs/ARTIFACT_STORE.md).
