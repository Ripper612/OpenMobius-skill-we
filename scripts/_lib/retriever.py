"""向量检索：从 ChromaDB 持久化索引按 query 找 top-K cards。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


log = logging.getLogger(__name__)


@dataclass
class RetrievedCard:
    """一条检索结果。"""
    card_id: str            # 卡片唯一 id（文件名 stem）
    card_type: str          # "concept" / "case"
    term: str               # 概念名 / 案例标题
    school: str             # 流派
    file_path: str          # 相对于 knowledge_base/ 的路径
    document: str           # 检索时存的拼接文本
    distance: float         # 向量距离（越小越相关）
    metadata: dict          # 完整 metadata


class Retriever:
    """ChromaDB 检索器。"""

    COLLECTION_NAME = "knowledge_base"

    def __init__(self, kb_dir: Path, embedder) -> None:
        """
        Args:
            kb_dir: 知识库目录（如 materials/<name>/knowledge_base/）
            embedder: rag.embedder 的实例（LocalNomicEmbedder 或 OpenAIEmbedder）
        """
        import chromadb  # noqa: PLC0415
        self.kb_dir = Path(kb_dir)
        self.embedder = embedder
        index_dir = self.kb_dir / "_index"
        if not index_dir.is_dir():
            raise FileNotFoundError(
                f"向量索引不存在: {index_dir}\n"
                f"请先跑：.venv/bin/python scripts/build_index.py"
            )
        self.client = chromadb.PersistentClient(path=str(index_dir))
        try:
            self.collection = self.client.get_collection(self.COLLECTION_NAME)
        except Exception as e:
            raise RuntimeError(
                f"无法加载 collection '{self.COLLECTION_NAME}'：{e}\n"
                f"索引目录: {index_dir}"
            )

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_school: Optional[str] = None,
        filter_type: Optional[str] = None,
    ) -> list[RetrievedCard]:
        """检索 top-K 相关 cards。

        Args:
            query: 自然语言查询
            top_k: 返回数量
            filter_school: 限定流派（如 "ICT"）
            filter_type: 限定类型（"concept" 或 "case"）
        """
        q_vec = self.embedder.embed_query(query)

        where_clause = {}
        if filter_school:
            where_clause["school"] = filter_school
        if filter_type:
            where_clause["type"] = filter_type
        where = where_clause if where_clause else None

        results = self.collection.query(
            query_embeddings=[q_vec.tolist()],
            n_results=top_k,
            where=where,
        )

        cards: list[RetrievedCard] = []
        for i in range(len(results["ids"][0])):
            meta = results["metadatas"][0][i]
            cards.append(RetrievedCard(
                card_id=results["ids"][0][i],
                card_type=meta.get("type", "?"),
                term=meta.get("term", "?"),
                school=meta.get("school", ""),
                file_path=meta.get("file_path", ""),
                document=results["documents"][0][i],
                distance=results["distances"][0][i],
                metadata=meta,
            ))
        return cards

    def get_full_card(self, card: RetrievedCard) -> Optional[dict]:
        """根据检索结果，读完整 JSON 卡片（带 source_cards / images 等所有字段）。"""
        if not card.file_path:
            return None
        full_path = self.kb_dir / card.file_path
        if not full_path.exists():
            log.warning("卡片文件不存在: %s", full_path)
            return None
        try:
            return json.loads(full_path.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            log.error("读取 %s 失败: %s", full_path, e)
            return None
