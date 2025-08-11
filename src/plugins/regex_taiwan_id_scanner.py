"""
RegexTaiwanIdScanner 插件

使用正規表示式來初步偵測符合台灣身分證字號格式的字串，
並結合驗證演算法來大幅提升準確率。
"""

import re
from typing import ClassVar

# 從專案的其他部分匯入我們需要的工具和資料結構
from src.shared_data_model import FileContext, ScanReport, ScanResult, ValidationStatus
from src.plugins.base import ScannerPlugin
from src.validators import is_valid_taiwan_id # <-- 匯入我們剛剛建立的驗證器

# 定義常數，提高可讀性
CONTEXT_WINDOW_SIZE = 10
_TAIWAN_ID_REGEX_PATTERN = r'\b[A-Z][12]\d{8}\b'


class RegexTaiwanIdScanner(ScannerPlugin):
    """
    一個專門掃描台灣身分證字號的具體插件實作。
    """
    # 1. 遵循契約：定義 pii_type
    pii_type: ClassVar[str] = "TAIWAN_ID_CARD"

    def __init__(self, **kwargs):
        """
        初始化時，預先編譯好 Regex 以提升效能。
        """
        super().__init__(**kwargs)
        self.regex = re.compile(_TAIWAN_ID_REGEX_PATTERN)

    def scan(self, text: str, file_context: FileContext) -> ScanReport:
        """
        掃描文字，找出所有符合格式的字串，並透過演算法驗證它們。
        """
        results: ScanReport = []
        
        for match in self.regex.finditer(text):
            matched_text = match.group(0)
            
            # 2. 呼叫驗證器：將找到的字串送入驗證演算法
            is_valid = is_valid_taiwan_id(matched_text)
            
            # 3. 根據驗證結果決定信賴分數
            if is_valid:
                # 如果通過檢查碼驗證，這幾乎 100% 是真的身分證號，給予最高分。
                confidence = 1.0
                validation_status = ValidationStatus.VALID
            else:
                # 如果未通過驗證，它只是一個「長得像」的字串（例如訂單編號）。
                # 在這個案例中，我們選擇直接忽略它，以達到最低的誤報率。
                continue

            # 4. 提取上下文
            start_index = match.start()
            end_index = match.end()
            context_start = max(0, start_index - CONTEXT_WINDOW_SIZE)
            context_end = min(len(text), end_index + CONTEXT_WINDOW_SIZE)
            context = text[context_start:context_end]

            # 5. 建立標準化的 ScanResult 物件
            result = ScanResult(
                file_context=file_context,
                pii_type=self.pii_type,
                matched_value=matched_text,
                confidence_score=confidence,
                scanner_source=self.name,
                validation_status=validation_status,
                context=context,
                location=f"附近 (char ~{start_index})"
            )
            results.append(result)

        return results