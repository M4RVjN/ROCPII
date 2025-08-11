# src/parsers/xlsx_parser.py
import logging
import pathlib
from zipfile import BadZipFile
import openpyxl
from src.shared_data_model import FileContext, FileStatus
from src.parsers.base_parser import BaseParser

class XlsxParser(BaseParser):
    def supports(self, mime_type: str) -> bool:
        return mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    def parse(self, file_path: pathlib.Path) -> tuple[FileContext, str]:
        ctx_args = {"file_path": file_path, "mime_type": self.supports.__annotations__['mime_type'], "file_size_bytes": file_path.stat().st_size}
        workbook = None
        try:
            workbook = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            all_text_chunks = []
            for sheet in workbook:
                all_text_chunks.append(f"\n--- Sheet: {sheet.title} ---\n")
                for row in sheet.iter_rows():
                    cell_values = [str(cell.value) for cell in row if cell.value is not None]
                    if cell_values: all_text_chunks.append(" ".join(cell_values))
            full_text = "\n".join(all_text_chunks)
            ctx = FileContext(**ctx_args, status=FileStatus.COMPLETED)
            return ctx, full_text
        except (BadZipFile, KeyError):
            msg = "檔案可能已加密或已損毀，無法解析。"
            logging.warning(f"'{file_path.name}': {msg}")
            ctx = FileContext(**ctx_args, status=FileStatus.SKIPPED, error_message=msg)
            return ctx, ""
        except Exception as e:
            msg = f"解析 XLSX 檔案時發生未知錯誤: {e}"
            logging.error(f"'{file_path.name}': {msg}", exc_info=True)
            ctx = FileContext(**ctx_args, status=FileStatus.ERROR, error_message=str(e))
            return ctx, ""
        finally:
            if workbook: workbook.close()