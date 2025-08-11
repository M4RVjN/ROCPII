# src/plugins/regex_email_scanner.py

"""
RegexEmailScanner 插件

使用正規表示式來偵測文字中符合 RFC 5322 標準的電子郵件地址。
"""

# --- 匯入 ---
import re
from typing import ClassVar

# 從共享模組匯入必要的資料結構和型別別名
from src.shared_data_model import FileContext, ScanReport, ScanResult, ValidationStatus
from src.plugins.base import ScannerPlugin

# --- 常數定義 ---
# 優化 2.1 & 4.1: 將上下文視窗大小和 Regex Pattern 定義為常數，提高可維護性。
CONTEXT_WINDOW_SIZE = 10

# 優化 1.1: 這是一個廣泛使用且相對健壯的 Email Regex 模式。
# 注意：完美的 Email Regex 非常複雜，此處選用一個在效能和準確性上取得良好平衡的模式。
# 安全備註：此 Regex 模式結構簡單，可有效避免 ReDoS 風險。
_EMAIL_REGEX_PATTERN = r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b'


class RegexEmailScanner(ScannerPlugin):
    """
    一個使用正規表示式來掃描電子郵件地址的具體插件實作。
    """
    # 遵循契約，定義 pii_type
    pii_type: ClassVar[str] = "EMAIL"

    def __init__(self, **kwargs):
        """
        初始化掃描器，並預先編譯正規表示式以提升效能。
        """
        super().__init__(**kwargs)
        # 優化 1.1: 使用 re.IGNORECASE 旗標，讓模式更簡潔且不區分大小寫
        self.regex = re.compile(_EMAIL_REGEX_PATTERN, re.IGNORECASE)

    def scan(self, text: str, file_context: FileContext) -> ScanReport:
        """
        優化 1.2: 完整實作的 scan 方法。

        接收文字和檔案上下文，找出所有匹配項，
        並為每一個匹配項建立一個包含完整資訊的 ScanResult 物件。

        Args:
            text: 從檔案解析器傳來的純文字內容。
            file_context: 包含該文字來源檔案資訊的上下文物件。

        Returns:
            一個 ScanReport (即 list[ScanResult])。
        """
        results: ScanReport = []
        
        # 使用 finditer 是處理大型文字的最佳實踐，它回傳一個迭代器而非一次性載入所有結果。
        for match in self.regex.finditer(text):
            matched_text = match.group(0)
            
            # --- 提取上下文 ---
            start_index = max(0, match.start() - CONTEXT_WINDOW_SIZE)
            end_index = min(len(text), match.end() + CONTEXT_WINDOW_SIZE)
            context = text[start_index:end_index]

            # --- 建立標準化的 ScanResult 物件 ---
            # 對於簡單的 Regex 掃描，可信度給予一個固定的中間值。
            # 驗證狀態為不適用，因為 Email 沒有標準的檢查碼演算法。
            result = ScanResult(
                file_context=file_context,
                pii_type=self.pii_type,
                matched_value=matched_text,
                confidence_score=0.7, # 給予一個基準分數
                scanner_source=self.name,
                validation_status=ValidationStatus.NOT_APPLICABLE,
                context=context,
                # Regex 較難提供如頁碼等精確位置，故此處留空
                location=None
            )
            results.append(result)

        return results