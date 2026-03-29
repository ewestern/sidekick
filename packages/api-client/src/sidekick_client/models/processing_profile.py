from enum import Enum


class ProcessingProfile(str, Enum):
    EVIDENCE = "evidence"
    FULL = "full"
    INDEX = "index"
    STRUCTURED = "structured"

    def __str__(self) -> str:
        return str(self.value)
