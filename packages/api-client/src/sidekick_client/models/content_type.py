from enum import Enum


class ContentType(str, Enum):
    AUDIO_RAW = "audio-raw"
    BEAT_BRIEF = "beat-brief"
    BUDGET_COMPARISON = "budget-comparison"
    CONNECTION_MEMO = "connection-memo"
    CROSS_BEAT_FLAG = "cross-beat-flag"
    DOCUMENT_RAW = "document-raw"
    DOCUMENT_TEXT = "document-text"
    ENTITY_EXTRACT = "entity-extract"
    POLICY_DIFF = "policy-diff"
    STORY_CANDIDATE = "story-candidate"
    STORY_DRAFT = "story-draft"
    STRUCTURED_DATA = "structured-data"
    SUMMARY = "summary"
    TREND_NOTE = "trend-note"
    VIDEO_RAW = "video-raw"

    def __str__(self) -> str:
        return str(self.value)
