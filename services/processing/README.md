# Processing service (Phase 3)

Acquisition workers complete `pending_acquisition` raw artifacts (e.g. HLS via **ffmpeg**). Processors write UTF-8 text to **object storage** via `ArtifactStore.write_with_bytes` — **`document-text`** (PDF text layer; OCR not implemented yet — see `entities` on the row) and **`transcript-clean`** (audio/video; optional **faster-whisper**).

## CLI

From repo root (with `DATABASE_URL`, `S3_BUCKET`, etc. set — same as ingestion):

```bash
cd services/processing
uv run sidekick-process acquire ARTIFACT_ID
uv run sidekick-process process ARTIFACT_ID
```

- **acquire** — HLS stubs only (`.m3u8` / `.m3u` on `acquisition_url`). Requires `ffmpeg` on `PATH`.
- **process** — active raw PDFs → `document-text`; active raw audio/video → `transcript-clean`.

### Speech-to-text optional extra

```bash
uv sync --extra stt
```

Production target remains **WhisperX** per `docs/IMPLEMENTATION_PLAN.md`; local dev uses **faster-whisper** when the extra is installed.

## Architecture

- `router.py` — `can_acquire_hls_stub`, `resolve_active_raw_processor`
- `acquisition/hls.py` — ffmpeg capture + `ArtifactStore.complete_acquisition`
- `processors/pdf.py`, `processors/transcript.py` — `ArtifactStore.write` processed rows

Processors MUST only run on **`stage=raw`** and **`status=active`**. See `docs/ARTIFACT_STORE.md`.
