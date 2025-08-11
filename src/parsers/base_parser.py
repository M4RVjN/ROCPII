# src/parsers/base_parser.py
from __future__ import annotations
import abc
import pathlib
from typing import Iterable
from src.shared_data_model import FileContext

class BaseParser(abc.ABC):
    @abc.abstractmethod
    def supports(self, mime_type: str) -> bool: ...
    @abc.abstractmethod
    def parse(self, file_path: pathlib.Path) -> tuple[FileContext, str]: ...