from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class Issue:
    severity: Severity
    code: str
    message: str
    row: int | None = None      # zero-based row index in the input table
    field: str | None = None

    def __str__(self) -> str:
        loc = f" (row {self.row})" if self.row is not None else ""
        return f"{self.severity.value}: {self.message}{loc}"
