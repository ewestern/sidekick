from enum import Enum


class ArtifactStatus(str, Enum):
    ACTIVE = "active"
    PENDING_ACQUISITION = "pending_acquisition"
    RETRACTED = "retracted"
    SUPERSEDED = "superseded"

    def __str__(self) -> str:
        return str(self.value)
