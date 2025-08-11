# src/engine.py

import logging
import multiprocessing
import os
import pathlib
import time
from dataclasses import dataclass, field
from typing import Iterable, Optional, List

from tqdm import tqdm

from src.shared_data_model import ScanReport, FileContext, FileStatus
from src.plugins.manager import PluginManager
from src.parsers import FileParserDispatcher
from src.reporting import generate_report

@dataclass(frozen=True)
class ScanConfig:
    """從 CLI 傳遞給核心引擎的標準化設定物件"""
    scan_path: pathlib.Path
    output_path: pathlib.Path
    log_level: str
    enabled_plugins: Optional[List[str]]
    overwrite_output: bool
    num_workers: Optional[int]

class MockNlpModel:
    """一個用於演示和測試的模擬 NLP 模型類別。"""
    def __call__(self, text_or_list, **kwargs):
        if isinstance(text_or_list, str): return []
        elif isinstance(text_or_list, list): return [[] for _ in text_or_list]

@dataclass
class WorkerResult:
    status: str; file_path: pathlib.Path
    results: ScanReport = field(default_factory=list); error_message: Optional[str] = None

worker_parser: Optional[FileParserDispatcher] = None
worker_plugins: Optional[List] = None

def _initialize_worker(plugins: list):
    """讓每一個子進程在自己內部建立一個全新的、乾淨的解析器實例。"""
    global worker_parser, worker_plugins
    worker_parser = FileParserDispatcher()
    worker_plugins = plugins
    logging.getLogger().setLevel(logging.ERROR)

def _scan_single_file_worker(file_path: pathlib.Path) -> WorkerResult:
    if worker_parser is None or worker_plugins is None:
        return WorkerResult(status='ERROR', file_path=file_path, error_message="工作進程未被正確初始化。")
    try:
        file_context, full_text = worker_parser(file_path)
        if file_context.status != FileStatus.COMPLETED:
             return WorkerResult(status='SUCCESS', file_path=file_path)
        
        file_results: ScanReport = []
        for plugin in worker_plugins:
            try:
                results = plugin.scan(full_text, file_context)
                if results: file_results.extend(results)
            except Exception as e:
                logging.error(f"插件 {plugin.name} 在掃描 {file_path} 時失敗: {e}", exc_info=True)
        return WorkerResult(status='SUCCESS', file_path=file_path, results=file_results)
    except Exception as e:
        error_message = f"處理檔案時發生未知錯誤: {e.__class__.__name__}: {e}"
        return WorkerResult(status='ERROR', file_path=file_path, error_message=error_message)


class CoreEngine:

    # 核心引擎初始化
    def __init__(self, config: ScanConfig):
        self.config = config
        self._initialize_components()

    def _initialize_components(self):
        logging.info("正在初始化核心引擎元件...")
        nlp_model = self._load_nlp_model()
        plugins_path = pathlib.Path(__file__).parent / "plugins"
        self.plugin_manager = PluginManager(plugin_dir=plugins_path, dependencies={'nlp_model': nlp_model})
        self.file_parser = FileParserDispatcher()
        logging.info("核心元件初始化完成。")
    
    # NLP 模型載入
    def _load_nlp_model(self):
        logging.info("正在載入 NLP 模型 ...")
        try:
            from transformers import pipeline
            model = pipeline("ner", model="ckiplab/bert-base-chinese-ner", aggregation_strategy="max")
            logging.info("成功載入 ckiplab/bert-base-chinese-ner 模型。")
        except ImportError:
            logging.error("未安裝 'transformers' 或 'torch' 函式庫，將使用無功能的模擬物件。")
            model = MockNlpModel()
        logging.info("NLP 模型載入完成。")
        return model
    
    # 檔案探索與掃描
    def _discover_files(self) -> List[pathlib.Path]:
        path = self.config.scan_path
        logging.info(f"開始在 '{path}' 中探索檔案...")
        if path.is_file(): files = [path]
        else: files = [f for f in path.rglob('*') if f.is_file()]
        logging.info(f"檔案探索完成，共找到 {len(files)} 個檔案。")
        return files

    # 掃描過程的核心(平行處理)
    def _run_parallel_processing(self, files_to_scan: List[pathlib.Path], enabled_plugins: list) -> tuple[ScanReport, list[dict]]:
        total_files = len(files_to_scan)
        num_processes = self.config.num_workers or os.cpu_count()
        logging.info(f"將使用 {num_processes} 個平行進程進行掃描。")
        chunksize = max(1, total_files // (num_processes * 4)) if total_files > 0 else 1
        all_results: ScanReport = []; files_with_errors = []

        with multiprocessing.Pool(processes=num_processes, initializer=_initialize_worker, initargs=(enabled_plugins,)) as pool:
            results_iterator = pool.imap_unordered(_scan_single_file_worker, files_to_scan, chunksize=chunksize)
            progress_bar = tqdm(results_iterator, total=total_files, desc="掃描進度", unit="file")
            
            for result in progress_bar:
                if result.status == 'SUCCESS':
                    if result.results: all_results.extend(result.results)
                else:
                    files_with_errors.append({'path': result.file_path, 'error': result.error_message})
                    logging.warning(f"處理檔案 '{result.file_path}' 時發生錯誤: {result.error_message}")
        return all_results, files_with_errors

    # 掃描結果處理與報告產製
    def _finalize_scan(self, all_results: ScanReport, files_with_errors: list[dict], start_time: float):
        end_time = time.perf_counter()
        logging.info(f"所有檔案掃描完成，耗時 {end_time - start_time:.2f} 秒。")
        logging.info(f"共發現 {len(all_results)} 筆個人資料。")
        if files_with_errors: logging.warning(f"有 {len(files_with_errors)} 個檔案處理失敗。")
        
        if all_results or not files_with_errors:
            logging.info(f"正在產生報告至 {self.config.output_path}...")
            generate_report(all_results, self.config.output_path)
            logging.info("報告產生完畢。")
        else:
            logging.info("未發現任何個人資料，且有檔案處理失敗，故不產生報告。")
    
    # main 的入口
    def run_scan(self):
        start_time = time.perf_counter()
        logging.info("掃描任務開始。")
        enabled_plugins = self.plugin_manager.get_enabled(self.config.enabled_plugins)
        if not enabled_plugins: logging.warning("沒有任何啟用的插件，掃描終止。"); return
        files_to_scan = self._discover_files()
        if not files_to_scan: logging.warning("在指定路徑下未找到任何檔案，掃描終止。"); return
        all_results, files_with_errors = self._run_parallel_processing(files_to_scan, enabled_plugins)
        self._finalize_scan(all_results, files_with_errors, start_time)