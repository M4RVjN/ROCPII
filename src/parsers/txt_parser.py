# src/parsers/txt_parser.py
import logging
import pathlib
from typing import ClassVar
from src.shared_data_model import FileContext, FileStatus
from src.parsers.base_parser import BaseParser

class TxtParser(BaseParser):
    ENCODINGS_TO_TRY: ClassVar[list[str]] = ['utf-8', 'big5', 'gbk', 'latin-1']
    def supports(self, mime_type: str) -> bool: return mime_type.startswith('text/')
    def parse(self, file_path: pathlib.Path) -> tuple[FileContext, str]:
        ctx_args = {"file_path": file_path, "mime_type": "text/plain", "file_size_bytes": file_path.stat().st_size}
        for encoding in self.ENCODINGS_TO_TRY:
            try:
                full_text = file_path.read_text(encoding=encoding)
                ctx = FileContext(**ctx_args, status=FileStatus.COMPLETED)
                logging.info(f"檔案 '{file_path.name}' 成功使用 '{encoding}' 編碼讀取。")
                return ctx, full_text
            except UnicodeDecodeError: continue
            except Exception as e:
                msg = f"讀取檔案時發生 I/O 錯誤: {e}"
                logging.error(f"'{file_path.name}': {msg}", exc_info=True)
                ctx = FileContext(**ctx_args, status=FileStatus.ERROR, error_message=str(e))
                return ctx, ""
        msg = "嘗試所有可用編碼後，仍無法解碼檔案。"
        logging.warning(f"'{file_path.name}': {msg}")
        ctx = FileContext(**ctx_args, status=FileStatus.ERROR, error_message=msg)
        return ctx, ""