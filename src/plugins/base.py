# src/plugins/base.py
from __future__ import annotations
import abc
from typing import ClassVar

from src.shared_data_model import FileContext, ScanReport

class ScannerPlugin(abc.ABC):
    pii_type: ClassVar[str]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, 'pii_type') or not cls.pii_type:
            raise TypeError(f"插件類別 {cls.__name__} 未能定義 'pii_type' 屬性。")

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def __init__(self, **kwargs):
        pass

    @abc.abstractmethod
    def scan(self, text: str, file_context: FileContext) -> ScanReport:
        ...