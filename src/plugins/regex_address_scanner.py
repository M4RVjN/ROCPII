import re
from typing import ClassVar

from src.shared_data_model import FileContext, ScanReport, ScanResult, ValidationStatus
from src.plugins.base import ScannerPlugin

CONTEXT_WINDOW_SIZE = 100

def _build_address_regex() -> re.Pattern:
    """
    根據使用者提供的邏輯，建立一個複雜的台灣地址正規表示式。
    """
    # 移除 'u' 前綴，因為 Python 3 預設即為 Unicode
    city = [
        '台北市', '新北市', '基隆市', '宜蘭縣', '新竹市', '新竹縣', '桃園市', 
        '苗栗縣', '台中市', '彰化縣', '南投縣', '雲林縣', '嘉義市', '嘉義縣', 
        '台南市', '高雄市', '屏東縣', '台東縣', '花蓮縣', '澎湖縣', '金門縣', '連江縣'
    ]
    other_city = [
        '台北縣', '高雄縣', '臺北市', '臺北縣', '台中縣', '臺中市', '臺中縣'
    ]

    # 主要部分：[縣市]...路/街...號
    addr_main = '[%s]\w+?[路街鄉鎮市區]\w*?\d{1,5}號' % '|'.join(city + other_city)
    # 可選部分：樓、室、之X
    addr_optional = r'(?:\d{1,3}樓)?(?:之\d{1,3})?(?:\d{1,3}室)?'
    
    # 完整的 Regex 規則
    full_regex_str = addr_main + addr_optional
    
    return re.compile(full_regex_str)

class RegexAddressScanner(ScannerPlugin):
    """
    一個使用正規表示式來掃描台灣地址的插件。
    """
    pii_type: ClassVar[str] = "ADDRESS"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.regex = _build_address_regex()

    def scan(self, text: str, file_context: FileContext) -> ScanReport:
        results: ScanReport = []
        for match in self.regex.finditer(text):
            matched_text = match.group(0)
            
            # 地址的 Regex 匹配可信度很高，給予較高的基礎分數
            confidence = 0.85

            context_start = max(0, match.start() - CONTEXT_WINDOW_SIZE)
            context_end = min(len(text), match.end() + CONTEXT_WINDOW_SIZE)
            context = text[context_start:context_end]

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