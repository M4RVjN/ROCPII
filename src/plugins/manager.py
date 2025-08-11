# src/plugins/manager.py (最終修正版)
import importlib
import inspect
import logging
import pathlib
import sys
import threading
from typing import Any, Dict, Optional, List

from src.plugins.base import ScannerPlugin

class PluginManager:
    #      主要是確保頂部的 import 語句是正確的，不包含 'list') ...
    def __init__(self, plugin_dir: str | pathlib.Path, dependencies: Optional[Dict[str, Any]] = None):
        self.plugin_dir = pathlib.Path(plugin_dir)
        self.dependencies = dependencies if dependencies else {}
        self._plugins_map: Dict[str, ScannerPlugin] = {}
        self._lock = threading.Lock()
        self._is_discovered = False
    
    # ... (此處省略其餘方法，保持不變) ...
    def _get_module_path_from_file(self, file_path: pathlib.Path) -> str:
        for parent in file_path.parents:
            if str(parent) in sys.path:
                relative_path = file_path.relative_to(parent)
                return ".".join(relative_path.with_suffix("").parts)
        raise ImportError(f"無法為檔案 '{file_path}' 決定其模組路徑。")

    def _load_plugins_from_file(self, file_path: pathlib.Path):
        try:
            module_path = self._get_module_path_from_file(file_path)
            module = importlib.import_module(module_path)
        except Exception as e:
            logging.error(f"無法載入插件模組 '{file_path.name}': {e}")
            return

        for _, member_class in inspect.getmembers(module, inspect.isclass):
            if (issubclass(member_class, ScannerPlugin) and
                    member_class is not ScannerPlugin and
                    not inspect.isabstract(member_class)):
                try:
                    plugin_instance = member_class(**self.dependencies)
                    plugin_name_lower = plugin_instance.name.lower()
                    if plugin_name_lower in self._plugins_map:
                        logging.warning(f"插件名稱衝突：'{plugin_instance.name}' 已被載入，將忽略在 '{file_path.name}' 中的重複定義。")
                        continue
                    self._plugins_map[plugin_name_lower] = plugin_instance
                    logging.info(f"成功載入插件: {plugin_instance.name}")
                except Exception as e:
                    logging.error(f"實例化插件 '{member_class.__name__}' 失敗: {e}")

    def discover(self):
        with self._lock:
            if self._is_discovered: return
            logging.info(f"開始從 '{self.plugin_dir}' 目錄探索插件...")
            if not self.plugin_dir.is_dir():
                logging.error(f"插件目錄不存在或不是一個目錄: {self.plugin_dir}")
                self._is_discovered = True
                return
            for file_path in self.plugin_dir.iterdir():
                if file_path.is_file() and file_path.name.endswith(".py"):
                    if not file_path.name.startswith(("_", "base.", "manager.")):
                        self._load_plugins_from_file(file_path)
            self._is_discovered = True
            logging.info(f"插件探索完成，共載入 {len(self._plugins_map)} 個插件。")

    def get_all(self) -> List[ScannerPlugin]:
        if not self._is_discovered: self.discover()
        return list(self._plugins_map.values())

    def get_enabled(self, enabled_names: Optional[List[str]]) -> List[ScannerPlugin]:
        all_plugins = self.get_all()
        if not enabled_names: return all_plugins
        loaded_plugins = []
        for name in enabled_names:
            name_lower = name.lower()
            plugin = self._plugins_map.get(name_lower)
            if plugin:
                loaded_plugins.append(plugin)
            else:
                logging.warning(f"警告：請求啟用未找到的插件 '{name}'，將被忽略。")
        return loaded_plugins