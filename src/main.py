# src/main.py (最終版 v3.0 - 清理所有內部定義)

import argparse
import logging
import multiprocessing
import os
import pathlib
import sys
from typing import Optional, Sequence

from src.engine import CoreEngine, ScanConfig

def setup_argument_parser() -> argparse.ArgumentParser:
    try: from src import __version__
    except ImportError: __version__ = "1.0.0"
    
    parser = argparse.ArgumentParser(
        prog="pii_scanner",
        description="ROCPII 白箱個資掃描器",
        epilog=f"版本 {__version__}",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("scan_path", type=pathlib.Path, help="要掃描的目標檔案或目錄路徑。")
    parser.add_argument("-o", "--output", dest="output_path", type=pathlib.Path, default=None, help="指定輸出的 Excel 報告路徑。若未指定，將自動產生檔名。")
    parser.add_argument("-l", "--log-level", dest="log_level", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], default="INFO", help="設定日誌記錄的詳細等級。預設為 INFO。")
    parser.add_argument("-p", "--plugins", dest="enabled_plugins", nargs="+", default=None, metavar="PLUGIN_NAME", help="指定要啟用的插件名稱(以空白分隔)。若未指定，則預設啟用所有可用插件。")
    parser.add_argument("-f", "--force", dest="overwrite_output", action="store_true", help="如果輸出檔案已存在，強制覆寫它。")
    parser.add_argument("-w", "--workers", dest="num_workers", type=int, default=None, help="指定用於掃描的平行工作進程數量。預設為系統的 CPU 核心數。")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    return parser

def _validate_arguments(args: argparse.Namespace) -> Optional[str]:
    if not args.scan_path.exists(): return f"掃描路徑不存在: '{args.scan_path}'"
    if not os.access(args.scan_path, os.R_OK): return f"沒有足夠的權限讀取掃描路徑: '{args.scan_path}'"
    if args.output_path:
        if args.output_path.is_dir(): return f"輸出路徑不能是一個目錄: '{args.output_path}'"
        output_dir = args.output_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        if not os.access(output_dir, os.W_OK): return f"沒有足夠的權限寫入輸出目錄: '{output_dir}'"
        if args.output_path.exists() and not args.overwrite_output: return f"輸出檔案 '{args.output_path}' 已存在。請使用 -f 或 --force 旗標進行覆寫。"
    return None

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = setup_argument_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=args.log_level.upper(), format='%(asctime)s - %(levelname)s - %(message)s')
    
    if args.output_path is None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output_path = pathlib.Path(f"scan_report_{timestamp}.xlsx")
        logging.info(f"未指定輸出路徑，將使用預設檔名: {args.output_path}")
    
    validation_error = _validate_arguments(args)
    if validation_error:
        logging.error(validation_error); return 1
        
    logging.info("參數驗證通過，準備啟動核心引擎...")
    try:
        scan_config = ScanConfig(
            scan_path=args.scan_path.resolve(),
            output_path=args.output_path.resolve(),
            log_level=args.log_level.upper(),
            enabled_plugins=args.enabled_plugins,
            overwrite_output=args.overwrite_output,
            num_workers=args.num_workers
        )
        engine = CoreEngine(config=scan_config)
        engine.run_scan()
    except KeyboardInterrupt:
        logging.warning("\n偵測到使用者中斷操作 (Ctrl+C)。正在提前終止程式...")
        return 130
    except Exception as e:
        logging.critical(f"掃描過程中發生致命錯誤: {e}", exc_info=True)
        return 1
    logging.info("程式執行成功結束。")
    return 0

if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())