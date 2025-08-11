# src/shared_data_model.py
from __future__ import annotations
import dataclasses
import pathlib
import enum
from datetime import datetime, timezone
from typing import Optional, TypeAlias, List

ScanReport: TypeAlias = List["ScanResult"]

class FileStatus(str, enum.Enum):
    PENDING = "待處理"; PARSING = "解析中"; COMPLETED = "處理完成"
    SKIPPED = "已跳過"; ERROR = "處理錯誤"

class ValidationStatus(str, enum.Enum):
    VALID = "驗證通過"; INVALID = "驗證失敗"; NOT_APPLICABLE = "不適用"

@dataclasses.dataclass(frozen=True, slots=True)
class FileContext:
    file_path: pathlib.Path; mime_type: str; file_size_bytes: int; status: FileStatus
    error_message: Optional[str] = None
    timestamp_utc: datetime = dataclasses.field(default_factory=lambda: datetime.now(timezone.utc))
    def is_successful(self) -> bool: return self.status == FileStatus.COMPLETED

@dataclasses.dataclass(frozen=True, slots=True)
class ScanResult:
    file_context: FileContext; pii_type: str; matched_value: str
    confidence_score: float; scanner_source: str; validation_status: ValidationStatus
    context: str; location: Optional[str] = None
    timestamp_utc: datetime = dataclasses.field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(f"Confidence score 必須介於 0.0 和 1.0 之間，但收到了 {self.confidence_score}")

    def __repr__(self) -> str:
        def mask_value(value: str) -> str:
            if len(value) < 4: return "***"
            quarter = len(value) // 4
            return f"{value[:quarter]}...{value[-quarter:]}"
        return (f"ScanResult(pii_type='{self.pii_type}', matched_value='{mask_value(self.matched_value)}', "
                f"confidence_score={self.confidence_score}, file_path='{self.file_context.file_path.name}')")