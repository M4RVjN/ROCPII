# src/parsers/__init__.py (最終版 - TxtParser 全覆蓋策略)

import logging
import os
import pathlib
import magic
from typing import Iterable

from src.shared_data_model import FileContext, FileStatus
from src.parsers.base_parser import BaseParser
# 我們現在只需要匯入這幾個核心解析器
from src.parsers.docx_parser import DocxParser
from src.parsers.pdf_parser import PdfParser
from src.parsers.xlsx_parser import XlsxParser
from src.parsers.txt_parser import TxtParser


class FileParserDispatcher:
    """
    一個根據檔案副檔名和 MIME 類型來分派任務給不同解析器的可呼叫類別。
    本版本採用「全面性優先」策略，所有基於文字的格式都由 TxtParser 處理。
    """
    def __init__(self):
        # 實例化所有解析器 # <- 新增
        docx_parser = DocxParser()
        xlsx_parser = XlsxParser()
        pdf_parser = PdfParser()
        txt_parser = TxtParser() # 所有純文字類型共用這一個解析器

        # 【最終決定】擴充副檔名映射表，將所有網頁和純文字檔案類型全部指向 TxtParser
        self.extension_map = { # <- 新增
            # Office & PDF
            '.docx': docx_parser,
            '.xlsx': xlsx_parser,
            '.pdf': pdf_parser,
            # Common Text & Web Files - ALL use TxtParser
            '.txt': txt_parser,
            '.html': txt_parser,
            '.htm': txt_parser,
            '.css': txt_parser,
            '.js': txt_parser,
            '.json': txt_parser,
            '.xml': txt_parser,
            '.svg': txt_parser,
            '.md': txt_parser,
            '.log': txt_parser,
            '.csv': txt_parser,
            '.ini': txt_parser,
            '.conf': txt_parser,
        }
        # 用於MIME類型匹配的後備列表
        self.mime_parsers: list[BaseParser] = [docx_parser, xlsx_parser, pdf_parser, txt_parser] # <- 新增
        logging.info(f"檔案解析分派器已初始化，支援 {len(self.extension_map)} 種副檔名。")

    # __call__ 和 _get_mime_type 方法與前一版完全相同，保持不變
    def _get_mime_type(self, file_path: pathlib.Path) -> str | None:
        try: return magic.from_file(str(file_path), mime=True)
        except magic.MagicException as e:
            logging.error(f"使用 python-magic 識別 '{file_path.name}' 時發生錯誤: {e}")
            return None

    def __call__(self, file_path: pathlib.Path) -> tuple[FileContext, str]:
        try:
            if not file_path.is_file(): raise FileNotFoundError("路徑不是一個有效的檔案")
            if not os.access(file_path, os.R_OK): raise PermissionError("沒有足夠的權限讀取檔案")
            if file_path.stat().st_size == 0:
                ctx = FileContext(file_path=file_path, mime_type="", file_size_bytes=0, status=FileStatus.SKIPPED, error_message="空檔案")
                return ctx, ""
        except (FileNotFoundError, PermissionError) as e:
            ctx = FileContext(file_path=file_path, mime_type="", file_size_bytes=0, status=FileStatus.ERROR, error_message=str(e))
            return ctx, ""

        file_ext = file_path.suffix.lower()
        if file_ext in self.extension_map:
            parser = self.extension_map[file_ext]
            logging.debug(f"檔案 '{file_path.name}' 根據副檔名 '{file_ext}' 分派給 {parser.__class__.__name__}。")
            return parser.parse(file_path)

        mime_type = self._get_mime_type(file_path)
        if mime_type:
            for parser in self.mime_parsers:
                if parser.supports(mime_type):
                    logging.debug(f"檔案 '{file_path.name}' 根據 MIME 類型 '{mime_type}' 分派給 {parser.__class__.__name__}。")
                    return parser.parse(file_path)

        final_mime = mime_type or "未知"
        logging.warning(f"檔案 '{file_path.name}' (副檔名: '{file_ext}', MIME: {final_mime}) 沒有找到支援的解析器，將跳過。")
        ctx = FileContext(file_path=file_path, mime_type=final_mime, file_size_bytes=file_path.stat().st_size, status=FileStatus.SKIPPED, error_message=f"不支援的檔案類型")
        return ctx, ""