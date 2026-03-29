# Chunking Proposal

> **Status**: proposed
> **Scope**: Handling full-length documents and transcripts in the processing pipeline without semantically incorrect prefix truncation
> **Last updated**: 2026-03-29

---

## Problem statement

The current enrichment processors truncate large text inputs before passing them to the model:

- [`services/processing/src/sidekick/processing/processors/entity_extract.py`](../services/processing/src/sidekick/processing/processors/entity_extract.py)
- [`services/processing/src/sidekick/processing/processors/summary.py`](../services/processing/src/sidekick/processing/processors/summary.py)

This is operationally reasonable because a single LLM call cannot safely accept arbitrarily large documents. However, prefix truncation is semantically incorrect:

- It overweights the beginning of the document.
- It can miss decisions, votes, appendices, or late-breaking context near the end.
- It makes extraction quality depend on source ordering rather than document importance.
- It creates silent failure modes that downstream agents cannot reliably detect.

The goal of this proposal is to replace one-pass truncation with a structure-aware, multi-pass pipeline that can process the full document while keeping model calls bounded.

## Current behavior

The current processing path is effectively:

1. Raw source becomes `document-text`.
2. `entity-extract` reads the full text artifact and truncates to a fixed max character count.
3. `summary` reads the same text artifact, truncates it again, then reads sibling `entity-extract`.

Relevant code:

- [`services/processing/src/sidekick/processing/processors/pdf.py`](../services/processing/src/sidekick/processing/processors/pdf.py)
- [`services/processing/src/sidekick/processing/processors/entity_extract.py`](../services/processing/src/sidekick/processing/processors/entity_extract.py)
- [`services/processing/src/sidekick/processing/processors/summary.py`](../services/processing/src/sidekick/processing/processors/summary.py)

Separately, the artifact store truncates text used for embeddings:

- [`packages/core/src/sidekick/core/artifact_store.py`](../packages/core/src/sidekick/core/artifact_store.py)

That embedding truncation is a retrieval-quality concern rather than the direct cause of summarization loss, but long-document retrieval should be considered as part of the same redesign.

## Proposed architecture

Replace single-pass enrichment over one large text blob with a hierarchical pipeline:

1. Normalize raw bytes to canonical text artifacts.
2. Split the text artifact into bounded chunks.
3. Run chunk-local enrichment in parallel.
4. Run reducer passes that merge chunk outputs into the existing top-level artifacts.

Target flow:

1. `document-text`
2. chunk artifacts
3. chunk-local `entity-extract`
4. chunk-local `summary`
5. reduced global `entity-extract`
6. reduced global `summary`

This keeps the current top-level outputs intact for downstream consumers while changing how they are produced.

## Design principles

- Full source text remains the canonical source of truth.
- Model calls should operate on bounded chunks, not arbitrarily truncated documents.
- Chunk boundaries should follow document structure where possible.
- Reducers should consume structured chunk outputs whenever possible, not raw text.
- Every intermediate output should preserve provenance back to the source chunk.
- Downstream agents should continue to read standard document-level artifacts by default.

## Proposed artifact stages and content types

This proposal assumes the existing artifact and lineage model remains the system of record.

Suggested new content types:

- `document-chunk`
- `transcript-chunk`
- `chunk-entity-extract`
- `chunk-summary`

These should be distinct from document-level `entity-extract` and `summary`. Using separate content types makes orchestration, lineage traversal, and retrieval simpler and avoids ambiguity between chunk-local and document-global outputs.

Each chunk artifact should include:

- `derived_from=[parent_text_artifact_id]`
- stable chunk ordering metadata such as `chunk_index`
- offset metadata such as `char_start` and `char_end`
- optional structure metadata such as `heading_path`, `page_start`, `page_end`
- transcript-specific metadata such as `speaker`, `time_start`, `time_end` when available

The goal is to make chunk provenance explicit enough that a reducer or downstream agent can trace claims back to the relevant section of the source.

## Chunking strategy

### PDFs and Markdown-like text

For `document-text` produced by the PDF processor:

- split on Markdown headings first
- keep lists and tables attached to their containing section
- if a section remains too large, subdivide by paragraph groups
- include small overlap between adjacent chunks

This works well with the current PDF normalization path because [`pdf.py`](../services/processing/src/sidekick/processing/processors/pdf.py) already emits Markdown-like text.

### Transcripts

For audio/video-derived `document-text`:

- split by speaker turn groups where possible
- preserve contiguous discussion around the same agenda item
- prefer time-window chunks when turn structure is weak
- keep a small overlap between adjacent windows

### Chunk sizing

The pipeline should target chunk sizes that are comfortably within model limits with room for prompts and structured output. The exact token target can be tuned later, but the architecture should assume:

- bounded chunk size
- bounded overlap
- deterministic chunking for reproducibility

## Processing passes

### Pass 1: chunk-local extraction

Each chunk is processed independently.

`chunk-entity-extract` should produce:

- entities
- topics
- financial figures
- motions or votes
- optional evidence metadata or local references

`chunk-summary` should produce:

- a concise summary of only that chunk
- local salience signals
- optional references to the chunk’s most important facts

Chunk-local prompts should explicitly forbid document-wide inference. They should ask the model to analyze only the supplied chunk and return local facts.

### Pass 2: global reduction

After all chunk-local outputs exist, reducers create the document-level outputs.

Document-level `entity-extract` reducer responsibilities:

- deduplicate repeated entities across chunks
- merge roles and contexts conservatively
- aggregate topics
- aggregate financial figures
- aggregate motions and votes
- preserve provenance to source chunks

Document-level `summary` reducer responsibilities:

- combine chunk summaries into a coherent whole-document narrative
- rank facts by document-level significance
- ensure coverage across the document rather than only the opening chunks
- promote formal actions, dates, dollar figures, and named officials
- preserve uncertainty when chunk outputs conflict

The summary reducer should rely primarily on structured chunk outputs and only reread raw chunk text when necessary.

## Reducer behavior

### Entity reducer

Entity reduction should be union-and-deduplicate rather than summarize-and-compress.

Expected behaviors:

- normalize entity names before merge
- use entity type as part of merge identity
- preserve multiple contexts when they differ materially
- avoid collapsing weakly similar entities without evidence
- attach references to all source chunks that mention the entity

### Summary reducer

Summary reduction is not a simple concatenation task.

Expected behaviors:

- rank chunk outputs by salience
- enforce whole-document coverage
- prefer explicit actions and numbers over generic narrative filler
- identify ambiguity instead of silently selecting one conflicting fact
- optionally trigger targeted rereads of a small number of raw chunks when conflicts matter

Targeted rereads are preferable to rereading the whole source. They keep token usage bounded while allowing the reducer to verify specific conflicts.

## Retrieval implications

Long-document handling also affects retrieval quality.

Today, the artifact store truncates text for embeddings in:

- [`packages/core/src/sidekick/core/artifact_store.py`](../packages/core/src/sidekick/core/artifact_store.py)

With chunk artifacts, retrieval can improve substantially:

- embed chunks instead of only the first section of the parent document
- retrieve matching chunks for deeper evidence
- keep document-level summary and entity-extract as default beat inputs
- use chunk retrieval only when a downstream agent needs detail or verification

This is especially relevant for beat analysis in:

- [`services/beat/src/sidekick/beat/tools.py`](../services/beat/src/sidekick/beat/tools.py)

The beat agent should continue to use document-level summaries by default, then selectively pull chunk-level evidence when needed.

## Orchestration sketch

Suggested processing graph:

1. Raw artifact becomes `document-text`.
2. Splitter creates chunk artifacts.
3. Fan out chunk-local processors in parallel.
4. Wait for all chunk outputs for the parent text artifact.
5. Run document-level reducers.
6. Publish standard document-level `entity-extract` and `summary`.

This preserves the existing concept that `summary` depends on `entity-extract`, but the sibling relationship moves from single-pass extraction to reduced extraction.

## Prompt and schema implications

Prompt contracts should clearly separate local analysis from global synthesis.

Chunk-local prompts:

- focus only on the supplied chunk
- prohibit document-wide conclusions
- prefer precise factual extraction
- require provenance-friendly outputs

Reducer prompts:

- combine structured outputs from multiple chunks
- deduplicate repeated facts
- resolve only well-supported conflicts
- surface ambiguity when resolution is uncertain

Reducer output schemas should stay close to the current document-level contracts so downstream consumers do not need to change immediately.

## Rollout plan

### Phase 1: infrastructure and chunk artifacts

- introduce chunk content types
- add deterministic chunker for `document-text`
- write chunk artifacts with lineage and ordering metadata

### Phase 2: chunk-local entity extraction

- add `chunk-entity-extract`
- add document-level reducer for `entity-extract`
- keep current summary flow temporarily if needed

### Phase 3: chunk-local summarization

- add `chunk-summary`
- add document-level summary reducer
- remove direct truncation from document-level summary processor

### Phase 4: retrieval upgrades

- embed chunk artifacts
- adjust semantic retrieval to prefer chunk-level evidence for long sources
- keep document-level summary artifacts as the default retrieval surface

This phased rollout reduces migration risk and allows long-document extraction quality to improve before summary reduction is introduced.

## Minimal viable version

If a smaller first implementation is preferred, start with:

1. chunking
2. chunk-local entity extraction
3. reduced document-level entity extraction
4. summary built from reduced extraction plus selected high-salience chunks

This would remove the worst semantic failure mode for long documents without requiring the entire summary stack to change at once.

## Risks and tradeoffs

- Too many small chunks will increase orchestration overhead and reducer noise.
- Naive fixed-size chunking will split tables, votes, and agenda items badly.
- Weak provenance metadata will make conflict resolution and debugging difficult.
- If reducers consume free-form text instead of structured chunk outputs, token pressure will return.
- Deduplication quality becomes a core correctness problem, especially for people, ordinances, and repeated budget figures.

Despite these risks, the chunk-and-reduce design is significantly more correct than prefix truncation for long government documents and transcripts.

## Recommendation

Adopt structure-aware chunking plus task-specific reducers as the default long-document strategy.

Specifically:

- keep `document-text` as the canonical source artifact
- introduce explicit chunk artifacts as a new processed stage
- move `entity-extract` and `summary` to reducer-style document-level outputs
- preserve document-level contracts for downstream agents
- upgrade semantic retrieval to operate on chunk artifacts for long sources

This design addresses the context window problem without discarding large portions of source material and fits the current artifact-oriented architecture of the pipeline.
