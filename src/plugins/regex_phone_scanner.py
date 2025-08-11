# src/plugins/regex_phone_scanner.py (最終版 - 處理 Unicode)
import re
from typing import ClassVar
from src.shared_data_model import FileContext, ScanReport, ScanResult, ValidationStatus
from src.plugins.base import ScannerPlugin

CONTEXT_WINDOW_SIZE = 10
# 加入全形括號、多種破折號和點作為分隔符
_PHONE_REGEX_PATTERN = re.compile(r"""
    (?<![\d\w])
    (
        # =================================================================
        # 手機 (Mobile) - 10 digits
        # =================================================================
        (?:
            # 國際: +886 9...
            \+886[-. –—\s]?9\d{2}
            |
            # 國內: 09...
            09\d{2}
        )
        [-. –—\s]?\d{3}[-. –—\s]?\d{3}
        |
        # =================================================================
        # 市話 (Landline) - 依用戶號碼長度分組
        # =================================================================
        (?:
            # 8碼用戶號碼 (台北, 台中)
            (?:(?:\+886[-. –—\s]?[24]|[\(（]0[24][\)）]|0[24]))
            [-. –—\s]?\d{4}[-. –—\s]?\d{4}
            |
            # 7碼用戶號碼 (桃園, 高雄, 屏東, 南投...)
            (?:(?:\+886[-. –—\s]?(?:3|49|[5-8])|[\(（]0(?:3|49|[5-8])[\)）]|0(?:3|49|[5-8])))
            [-. –—\s]?\d{3}[-. –—\s]?\d{4}
            |
            # 6碼用戶號碼 (苗栗, 台東, 金門)
            (?:(?:\+886[-. –—\s]?(?:37|89|82)|[\(（]0(?:37|89|82)[\)）]|0(?:37|89|82)))
            [-. –—\s]?\d{3}[-. –—\s]?\d{3}
            |
            # 5碼用戶號碼 (馬祖)
            (?:(?:\+886[-. –—\s]?836|[\(（]0836[\)）]|0836))
            [-. –—\s]?\d{2}[-. –—\s]?\d{3}
        )
        |
        # =================================================================
        # 免付費 (Toll-Free) - 10或11碼
        # =================================================================
        (?:
            080[09]
            [-. –—\s]?
            (?:
                \d{3}[-. –—\s]?\d{3}  # 6碼用戶號碼
                |
                \d{3}[-. –—\s]?\d{4}  # 7碼用戶號碼
            )
        )
    )
    (?![=\d\w])
""", re.VERBOSE)

# 增設正面詞與負面詞以減少誤判
POSITIVE_KEYWORDS = ["電話", "手機", "市話", "專線", "致電", "TEL", "Phone", "Cell"] # 新增正面詞
NEGATIVE_KEYWORDS = ["訂單", "編號", "發票", "貨號", "郵遞區號"] # 新增負面詞

class RegexPhoneScanner(ScannerPlugin):
    pii_type: ClassVar[str] = "PHONE_NUMBER"
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.regex = _PHONE_REGEX_PATTERN
    def scan(self, text: str, file_context: FileContext) -> ScanReport:
        results: ScanReport = []
        for match in self.regex.finditer(text):
            confidence = 0.5
            context_start = max(0, match.start() - CONTEXT_WINDOW_SIZE)
            context_end = min(len(text), match.end() + CONTEXT_WINDOW_SIZE)
            context = text[context_start:context_end]
            if any(kw.lower() in context.lower() for kw in NEGATIVE_KEYWORDS): confidence = 0.4
            if any(kw.lower() in context.lower() for kw in POSITIVE_KEYWORDS): confidence = 0.6
            if confidence > 0.:
                results.append(ScanResult(
                    file_context=file_context, pii_type=self.pii_type, matched_value=match.group(0),
                    confidence_score=confidence, scanner_source=self.name,
                    validation_status=ValidationStatus.NOT_APPLICABLE, context=context,
                    location=f"附近 (char ~{match.start()})"
                ))
        return results