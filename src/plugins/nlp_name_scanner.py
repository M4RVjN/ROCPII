# src/plugins/nlp_name_scanner.py (優化版 - 僅掃描姓名)

import logging
from typing import ClassVar, List, Dict, Any

from transformers import Pipeline

from src.shared_data_model import FileContext, ScanReport, ScanResult, ValidationStatus
from src.plugins.base import ScannerPlugin

CONTEXT_WINDOW_SIZE = 50
MAX_CHUNK_LENGTH = 500
CHUNK_STRIDE = 50

# 【優化】目標實體現在只剩下 "PERSON"
TARGET_ENTITY_GROUP = "PERSON"


class NlpNameScanner(ScannerPlugin):
    """
    一個使用 ckiplab NER 模型來掃描中文姓名的具體插件實作。
    """
    # 【優化】pii_type 改回更精確的名稱
    pii_type: ClassVar[str] = "PERSON_NAME"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model: Pipeline = kwargs.get('nlp_model')
        if not self.model:
            raise TypeError(f"{self.name} 需要一個 'nlp_model' 依賴項。")

    @staticmethod
    def _group_contiguous_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not entities: return []
        grouped = []
        for entity in entities:
            entity_word = entity['word'].replace('##', '').replace(' ', '')
            if not entity_word: continue
            if (grouped and 
                entity['entity_group'] == grouped[-1]['entity_group'] and 
                entity['start'] == grouped[-1]['end']):
                last_group = grouped[-1]
                last_group['word'] += entity_word
                last_group['end'] = entity['end']
                last_group['score'] = max(last_group['score'], entity['score'])
            else:
                new_entity = entity.copy(); new_entity['word'] = entity_word
                grouped.append(new_entity)
        return grouped

    @staticmethod
    def _chunk_text(text: str) -> list[str]:
        # ... (此函式保持不變) ...
        if len(text) <= MAX_CHUNK_LENGTH: return [text]
        return [text[i: i + MAX_CHUNK_LENGTH] for i in range(0, len(text), MAX_CHUNK_LENGTH - CHUNK_STRIDE)]

    def scan(self, text: str, file_context: FileContext) -> ScanReport:
        if not text.strip(): return []
        results: ScanReport = []; found_entities = set()
        text_chunks = self._chunk_text(text)

        try:
            batch_results = self.model(text_chunks)
        except Exception as e:
            logging.error(f"'{self.name}' 在批次模型推論時發生錯誤: {e}", exc_info=True)
            return []

        for i, chunk_results in enumerate(batch_results):
            if not isinstance(chunk_results, list): continue
            
            grouped_chunk_entities = self._group_contiguous_entities(chunk_results)
            chunk_offset = i * (MAX_CHUNK_LENGTH - CHUNK_STRIDE)
            
            for entity in grouped_chunk_entities:
                # 【優化】現在只對 "PERSON" 類型的實體感興趣
                if entity.get('entity_group') == TARGET_ENTITY_GROUP:
                    matched_text = entity['word']
                    absolute_start = entity['start'] + chunk_offset
                    
                    if (matched_text, absolute_start) in found_entities: continue
                    found_entities.add((matched_text, absolute_start))

                    context_start = max(0, absolute_start - CONTEXT_WINDOW_SIZE)
                    context_end = min(len(text), absolute_start + len(matched_text) + CONTEXT_WINDOW_SIZE)
                    
                    result = ScanResult(
                        file_context=file_context,
                        pii_type=self.pii_type, # <-- 直接使用類別的 pii_type
                        matched_value=matched_text,
                        confidence_score=round(float(entity['score']), 4),
                        scanner_source=self.name,
                        validation_status=ValidationStatus.NOT_APPLICABLE,
                        context=text[context_start:context_end],
                        location=f"附近 (char ~{absolute_start})"
                    )
                    results.append(result)
        return results