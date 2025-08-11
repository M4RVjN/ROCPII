import re
from typing import ClassVar

from src.shared_data_model import FileContext, ScanReport, ScanResult, ValidationStatus
from src.plugins.base import ScannerPlugin

CONTEXT_WINDOW_SIZE = 10
# 台灣健保卡號格式：12個數字
_NHI_REGEX_PATTERN = r'(?<!\d)\d{12}(?!\d)'

# 使用關鍵字來輔助判斷，提升準確率
POSITIVE_KEYWORDS = ["健保卡", "健保號", "NHI No"]
NEGATIVE_KEYWORDS = ["訂單號", "會員編號", "快遞單號", "案件編號"]

class RegexHealthInsuranceScanner(ScannerPlugin):
    pii_type: ClassVar[str] = "NHI_NUMBER"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.regex = re.compile(_NHI_REGEX_PATTERN)

    def scan(self, text: str, file_context: FileContext) -> ScanReport:
        results: ScanReport = []
        for match in self.regex.finditer(text):
            confidence = 0.5  # 基礎信賴分數
            
            # 提取上下文進行關鍵字分析
            context_start = max(0, match.start() - CONTEXT_WINDOW_SIZE)
            context_end = min(len(text), match.end() + CONTEXT_WINDOW_SIZE)
            context = text[context_start:context_end]
            
            # 檢查正面關鍵字
            if any(kw in context for kw in POSITIVE_KEYWORDS):
                confidence = 0.6
            # 檢查負面關鍵字
            elif any(kw in context for kw in NEGATIVE_KEYWORDS):
                confidence = 0.4
            
            # 只有當信賴度高於某個閾值時，才將其視為個資
            if confidence > 0:
                result = ScanResult(
                    file_context=file_context,
                    pii_type=self.pii_type,
                    matched_value=match.group(0),
                    confidence_score=confidence,
                    scanner_source=self.name,
                    validation_status=ValidationStatus.NOT_APPLICABLE,
                    context=context,
                    location=f"附近 (char ~{match.start()})"
                )
                results.append(result)
        return results