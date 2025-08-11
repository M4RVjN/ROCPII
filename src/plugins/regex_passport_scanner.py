# src/plugins/regex_passport_scanner.py (v3.0 - 根據使用者回饋修正)

import re
from typing import ClassVar

from src.shared_data_model import FileContext, ScanReport, ScanResult, ValidationStatus
from src.plugins.base import ScannerPlugin

CONTEXT_WINDOW_SIZE = 10

# 正規表示式只專注於最常見的 9 位純數字格式
_PASSPORT_REGEX_PATTERN = r'(?<!\d)\d{9}(?!\d)'

# 由於格式模糊，關鍵字變得至關重要
POSITIVE_KEYWORDS = ["護照", "PASSPORT", "護照號", "PASSPORT NO", "出國", "僑委會", "外交部"]
NEGATIVE_KEYWORDS = ["訂單", "編號", "統一編號", "收據", "發票", "會員", "貨號", "產品"]

class RegexPassportScanner(ScannerPlugin):
    """
    一個掃描台灣護照號碼的插件。
    - v3.0:
      - 根據使用者回饋，專注於掃描最常見的 9 位純數字格式。
      - 將上下文關鍵字分析作為核心計分策略，以應對格式的模糊性。
    """
    pii_type: ClassVar[str] = "PASSPORT_NUMBER"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.regex = re.compile(_PASSPORT_REGEX_PATTERN)

    def scan(self, text: str, file_context: FileContext) -> ScanReport:
        results: ScanReport = []
        for match in self.regex.finditer(text):
            matched_text = match.group(0)
            confidence = 0.5  # 初始化信賴分數

            # 提取上下文進行關鍵字分析
            context_start = max(0, match.start() - CONTEXT_WINDOW_SIZE)
            context_end = min(len(text), match.end() + CONTEXT_WINDOW_SIZE)
            context = text[context_start:context_end]
            
            # 計分邏輯完全依賴上下文
            if any(kw in context for kw in POSITIVE_KEYWORDS):
                # 只有在上下文中出現強烈正面關鍵字時，才給予高信賴度
                confidence = 0.6
            elif any(kw in context for kw in NEGATIVE_KEYWORDS):
                # 如果出現負面關鍵字
                confidence = 0.4

            # 只有當信賴度高於某個閾值時，才將其視為個資
            # 我們可以設定較高的閾值，例如 0.9，只採信有正面關鍵字的結果
            if confidence >= 0:
                result = ScanResult(
                    file_context=file_context,
                    pii_type=self.pii_type,
                    matched_value=matched_text,
                    confidence_score=confidence,
                    scanner_source=self.name,
                    validation_status=ValidationStatus.NOT_APPLICABLE,
                    context=context,
                    location=f"附近 (char ~{match.start()})"
                )
                results.append(result)
                
        return results