# src/parsers/pdf_parser.py
import logging
import pathlib
import fitz
from src.shared_data_model import FileContext, FileStatus
from src.parsers.base_parser import BaseParser

class PdfParser(BaseParser):
    def supports(self, mime_type: str) -> bool: return mime_type == "application/pdf"
    def parse(self, file_path: pathlib.Path) -> tuple[FileContext, str]:
        ctx_args = {"file_path": file_path, "mime_type": "application/pdf", "file_size_bytes": file_path.stat().st_size}
        try:
            with fitz.open(file_path) as doc:
                if doc.is_encrypted:
                    msg = "檔案已加密，無法解析。"
                    logging.warning(f"{file_path.name}: {msg}")
                    return FileContext(**ctx_args, status=FileStatus.SKIPPED, error_message=msg), ""
                pages_text = [page.get_text("text") for page in doc]
                full_text = "\n".join(pages_text)
                ctx = FileContext(**ctx_args, status=FileStatus.COMPLETED)
                return ctx, full_text
        except Exception as e:
            msg = f"解析 PDF 檔案時發生錯誤: {e}"
            logging.error(f"'{file_path.name}': {msg}", exc_info=True)
            ctx = FileContext(**ctx_args, status=FileStatus.ERROR, error_message=str(e))
            return ctx, ""