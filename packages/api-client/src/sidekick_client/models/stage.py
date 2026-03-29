from enum import Enum


class Stage(str, Enum):
    ANALYSIS = "analysis"
    CONNECTIONS = "connections"
    DRAFT = "draft"
    PROCESSED = "processed"
    RAW = "raw"

    def __str__(self) -> str:
        return str(self.value)
