import re
from typing import ClassVar

from src.shared_data_model import FileContext, ScanReport, ScanResult, ValidationStatus
from src.plugins.base import ScannerPlugin
from src.validators import is_valid_luhn

CONTEXT_WINDOW_SIZE = 10
# 這個 Regex 用於匹配常見的 13-16 位信用卡號格式，可以包含空格或破折號
_CREDIT_CARD_REGEX_PATTERN = r'\b(?:(?:\d[ -]?){13,16})\b'

class RegexCreditCardScanner(ScannerPlugin):
    pii_type: ClassVar[str] = "CREDIT_CARD"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.regex = re.compile(_CREDIT_CARD_REGEX_PATTERN)

    def scan(self, text: str, file_context: FileContext) -> ScanReport:
        results: ScanReport = []
        for match in self.regex.finditer(text):
            matched_text = match.group(0)
            
            # 先過濾掉明顯不是信用卡號的（例如，超過19個字元含分隔符）
            if len(matched_text.replace(" ", "").replace("-", "")) > 16:
                continue

            # 關鍵步驟：呼叫 Luhn 演算法進行驗證
            if is_valid_luhn(matched_text):
                context_start = max(0, match.start() - CONTEXT_WINDOW_SIZE)
                context_end = min(len(text), match.end() + CONTEXT_WINDOW_SIZE)
                
                result = ScanResult(
                    file_context=file_context,
                    pii_type=self.pii_type,
                    matched_value=matched_text,
                    confidence_score=1.0, # 通過 Luhn 驗證，給予最高信賴度
                    scanner_source=self.name,
                    validation_status=ValidationStatus.VALID,
                    context=text[context_start:context_end],
                    location=f"附近 (char ~{match.start()})"
                )
                results.append(result)
        return results