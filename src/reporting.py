# src/reporting.py (最終版 - 多重顏色條件格式化)

import logging
import pathlib
from typing import Optional

import pandas as pd
from xlsxwriter.utility import xl_col_to_name

from src.shared_data_model import ScanReport

class ReportGenerator:
    """
    一個將 ScanResult 列表轉換為客製化格式 Excel 報告的類別。
    """
    # --- 欄位常數 ---
    _COL_PII_TYPE = "個資類型"
    _COL_MATCHED_VALUE = "符合內容"
    _COL_CONFIDENCE = "信賴分數"
    _COL_FILE_PATH = "檔案路徑"
    _COL_SOURCE = "掃描來源"
    _COL_CONTEXT = "上下文"
    
    _ORDERED_COLUMNS = [
        _COL_PII_TYPE, _COL_MATCHED_VALUE, _COL_CONFIDENCE, 
        _COL_FILE_PATH, _COL_SOURCE, _COL_CONTEXT
    ]

    _SHEET_NAME_DETAILS = "掃描結果"

    # --- 樣式與格式化常數 ---
    # 【新功能】定義三種風險等級的顏色
    _LOW_CONF_COLOR = {'font_color': "#000000", 'bg_color': "#FD6D6D"} # 紅色
    _MEDIUM_RISK_COLOR = {'font_color': '#000000', 'bg_color': "#FFB1B1"} # 粉紅色
    _HIGH_RISK_COLOR = {'font_color': '#000000', 'bg_color': "#FFFF6B"} # 黃色
    
    _HEADER_BG_COLOR = "#4F81BD"
    _MAX_COL_WIDTH = 70
    _COL_WIDTH_SAMPLE_ROWS = 1000

    def __init__(self, workbook):
        """初始化報告生成器，並預先定義所有 Excel 格式。"""
        self.workbook = workbook
        self.header_format = self.workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'top',
            'fg_color': self._HEADER_BG_COLOR, 'font_color': 'white', 'border': 1
        })
        self.high_risk_format = self.workbook.add_format(self._HIGH_RISK_COLOR)
        self.medium_risk_format = self.workbook.add_format(self._MEDIUM_RISK_COLOR)
        self.low_conf_format = self.workbook.add_format(self._LOW_CONF_COLOR)

    def _results_to_dataframe(self, scan_results: ScanReport) -> pd.DataFrame:
        # ... (此函式與前一版完全相同) ...
        if not scan_results: return pd.DataFrame(columns=self._ORDERED_COLUMNS)
        records = [{
                self._COL_PII_TYPE: res.pii_type, self._COL_MATCHED_VALUE: res.matched_value,
                self._COL_CONFIDENCE: res.confidence_score, self._COL_FILE_PATH: str(res.file_context.file_path),
                self._COL_SOURCE: res.scanner_source, self._COL_CONTEXT: res.context,
            } for res in scan_results]
        return pd.DataFrame.from_records(records)[self._ORDERED_COLUMNS]

    def _write_details_sheet(self, writer: pd.ExcelWriter, df: pd.DataFrame):
        logging.debug(f"正在建立 '{self._SHEET_NAME_DETAILS}' 工作表...")
        df.to_excel(writer, sheet_name=self._SHEET_NAME_DETAILS, index=False, header=False, startrow=1)
        worksheet = writer.sheets[self._SHEET_NAME_DETAILS]

        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, self.header_format)

        (max_row, max_col) = df.shape
        worksheet.autofilter(0, 0, max_row, max_col - 1)
        worksheet.freeze_panes(1, 0)

        try:
            score_col_idx = df.columns.get_loc(self._COL_CONFIDENCE)
            score_col_letter = xl_col_to_name(score_col_idx)
            data_range = f'A2:{xl_col_to_name(max_col-1)}{max_row+1}'

            # 【新功能】套用多重條件格式化規則
            # 規則的順序很重要，xlsxwriter 會依序套用，後面的規則會覆蓋前面的
            
            # 規則 1: 極低信賴分數 (<0.5) -> 紅色
            worksheet.conditional_format(data_range, {
                'type': 'formula',
                'criteria': f'=${score_col_letter}2<0.5',
                'format': self.low_conf_format
            })
            
            # 規則 2: 低信賴分數 (0.5 ~ 0.59) -> 粉紅色
            worksheet.conditional_format(data_range, {
                'type': 'formula',
                'criteria': f'=AND(${score_col_letter}2>=0.5, ${score_col_letter}2<0.6)',
                'format': self.medium_risk_format
            })

            # 規則 3: 中信賴分數 (0.6 ~ 0.79) -> 黃色
            worksheet.conditional_format(data_range, {
                'type': 'formula',
                'criteria': f'=AND(${score_col_letter}2>=0.6, ${score_col_letter}2<0.8)',
                'format': self.high_risk_format
            })

        except KeyError:
            logging.warning(f"在 DataFrame 中未找到 '{self._COL_CONFIDENCE}' 欄位，跳過條件格式化。")
        
        # ... (自動調整欄寬邏輯保持不變) ...
        for i, col in enumerate(df.columns):
            sampled_df = df[col].head(self._COL_WIDTH_SAMPLE_ROWS).astype(str)
            max_len = max(sampled_df.str.len().max(), len(col)) if not sampled_df.empty else len(col)
            width = min(max(max_len, 10) + 2, self._MAX_COL_WIDTH)
            worksheet.set_column(i, i, width)

# 外部呼叫的進入點函式
def generate_report(scan_results: ScanReport, output_path: pathlib.Path):
    try:
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            reporter = ReportGenerator(writer.book)
            df = reporter._results_to_dataframe(scan_results)

            # 【客製化】移除總覽頁，只建立詳細結果工作表
            if not df.empty:
                reporter._write_details_sheet(writer, df)
                logging.info(f"報告生成成功，包含 {len(df)} 筆發現。")
            else:
                worksheet = reporter.workbook.add_worksheet(reporter._SHEET_NAME_DETAILS)
                worksheet.write('A1', "任務完成，未在任何檔案中發現個資。")
                logging.info("未發現任何個人資料，已生成空的結果報告。")
    except Exception as e:
        logging.critical(f"生成報告時發生未預期錯誤: {e}", exc_info=True)