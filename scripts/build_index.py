#!/usr/bin/env python3
"""建知识库向量索引（skill 内置 knowledge_base/ → knowledge_base/_index/）。

读 <skill>/knowledge_base/{concepts,cases}/*.json
  → 每张卡拼成 embed 友好的文本
  → 调 embedder 转向量
  → 存到 ChromaDB（<skill>/knowledge_base/_index/）

Usage:
    python scripts/build_index.py
    python scripts/build_index.py --force        # 强制重建
    python scripts/build_index.py --limit 10     # 只索引 10 张测试
    python scripts/build_index.py --embedder openai  # 切换 embedder
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional


THIS_DIR = Path(__file__).resolve().parent        # scripts/
SKILL_DIR = THIS_DIR.parent                       # skill 根
sys.path.insert(0, str(THIS_DIR))                 # 让 _lib 可见

from _lib.embedder import get_embedder  # noqa: E402


log = logging.getLogger("build_kb_index")


def build_concept_text(card: dict) -> str:
    """把 concept 卡拼成 embedding 友好的纯文本。"""
    parts: list[str] = []
    term = card.get("canonical_term") or card.get("term") or ""
    if term:
        parts.append(f"Term: {term}")
    aliases = card.get("aliases") or []
    if aliases:
        parts.append(f"Aliases: {', '.join(aliases)}")
    school = card.get("school") or ""
    if school:
        parts.append(f"School: {school}")
    definition = card.get("definition") or ""
    if definition:
        parts.append(f"Definition: {definition}")
    rules = card.get("identification_rules") or []
    if rules:
        parts.append("Identification rules:\n" + "\n".join(f"- {r}" for r in rules))
    impl = card.get("trading_implication") or ""
    if impl:
        parts.append(f"Trading implication: {impl}")
    mistakes = card.get("common_mistakes") or []
    if mistakes:
        parts.append("Common mistakes:\n" + "\n".join(f"- {m}" for m in mistakes))
    related = card.get("related_concepts") or []
    if related:
        # related_concepts 可能是字符串列表或 dict 列表
        rel_strs = [
            r.get("term") if isinstance(r, dict) else r
            for r in related
            if r
        ]
        if rel_strs:
            parts.append(f"Related concepts: {', '.join(filter(None, rel_strs))}")
    return "\n\n".join(parts)


def build_case_text(card: dict) -> str:
    """把 case 卡拼成 embedding 友好的纯文本。"""
    parts: list[str] = []
    title = card.get("title") or ""
    if title:
        parts.append(f"Title: {title}")
    school = card.get("school") or ""
    if school:
        parts.append(f"School: {school}")
    asset = card.get("asset")
    tf = card.get("timeframe")
    if asset or tf:
        parts.append(f"Market: {asset or '?'} @ {tf or '?'}")
    ctx = card.get("market_context") or ""
    if ctx:
        parts.append(f"Market context: {ctx}")
    obs = card.get("key_observation") or ""
    if obs:
        parts.append(f"Key observation: {obs}")
    steps = card.get("analysis_steps") or []
    if steps:
        parts.append("Analysis steps:\n" + "\n".join(f"- {s}" for s in steps))
    lessons = card.get("lessons") or ""
    if lessons:
        parts.append(f"Lessons: {lessons}")
    related = card.get("related_concepts") or card.get("illustrates_concepts") or []
    if related:
        rel_strs = [
            r.get("term") if isinstance(r, dict) else r
            for r in related
            if r
        ]
        if rel_strs:
            parts.append(f"Related concepts: {', '.join(filter(None, rel_strs))}")
    return "\n\n".join(parts)


def collect_cards(kb_dir: Path, limit: Optional[int] = None) -> list[dict]:
    """读所有 concept + case 卡，返回 [{id, type, file_path, card_data, text}]。"""
    items: list[dict] = []

    concepts_dir = kb_dir / "concepts"
    if concepts_dir.is_dir():
        for f in sorted(concepts_dir.glob("*.json")):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception as e:  # noqa: BLE001
                log.warning("跳过损坏的 %s: %s", f.name, e)
                continue
            text = build_concept_text(d)
            if not text:
                continue
            items.append({
                "id": f.stem,
                "type": "concept",
                "file_path": f"concepts/{f.name}",
                "card": d,
                "text": text,
            })

    cases_dir = kb_dir / "cases"
    if cases_dir.is_dir():
        for f in sorted(cases_dir.glob("*.json")):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception as e:  # noqa: BLE001
                log.warning("跳过损坏的 %s: %s", f.name, e)
                continue
            text = build_case_text(d)
            if not text:
                continue
            items.append({
                "id": f.stem,
                "type": "case",
                "file_path": f"cases/{f.name}",
                "card": d,
                "text": text,
            })

    if limit:
        items = items[:limit]
    return items


def main() -> int:
    p = argparse.ArgumentParser(description="Build vector index for the skill's knowledge_base/.")
    p.add_argument(
        "--kb", default=None,
        help=f"knowledge_base 目录（默认 {SKILL_DIR / 'knowledge_base'}）",
    )
    p.add_argument(
        "--embedder", default="local",
        choices=["local", "openai"],
        help="embedding provider：local（nomic-embed，开源默认）/ openai",
    )
    p.add_argument(
        "--force", action="store_true",
        help="已存在索引时强制重建",
    )
    p.add_argument(
        "--limit", type=int, default=None,
        help="只索引前 N 张卡（测试用）",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-5s %(message)s",
        datefmt="%H:%M:%S",
    )

    kb_dir = Path(args.kb) if args.kb else SKILL_DIR / "knowledge_base"
    if not kb_dir.is_dir():
        log.error("knowledge_base/ 不存在: %s", kb_dir)
        return 1

    index_dir = kb_dir / "_index"

    # 检查现有索引
    if index_dir.exists() and not args.force:
        log.error(
            "索引目录已存在: %s\n加 --force 强制重建", index_dir,
        )
        return 1

    if args.force and index_dir.exists():
        import shutil  # noqa: PLC0415
        log.info("--force：删除旧索引 %s", index_dir)
        shutil.rmtree(index_dir)

    # 收集卡片
    log.info("扫描知识库: %s", kb_dir)
    items = collect_cards(kb_dir, limit=args.limit)
    n_concept = sum(1 for it in items if it["type"] == "concept")
    n_case = sum(1 for it in items if it["type"] == "case")
    log.info("发现 %d concept + %d case = %d 张卡", n_concept, n_case, len(items))
    if args.limit:
        log.info("（--limit %d 限制）", args.limit)
    if not items:
        log.error("没有可索引的卡片。")
        return 1

    # Embed
    log.info("加载 embedder（%s）...", args.embedder)
    embedder = get_embedder(args.embedder)
    log.info("embedding dimension: %d", embedder.dim)

    texts = [it["text"] for it in items]
    log.info("批量 embedding %d 张卡...", len(texts))
    vecs = embedder.embed_documents(texts)

    # 存到 ChromaDB
    log.info("建 ChromaDB collection 并写入...")
    import chromadb  # noqa: PLC0415
    client = chromadb.PersistentClient(path=str(index_dir))
    collection = client.create_collection(
        name="knowledge_base",
        metadata={"hnsw:space": "cosine"},
    )

    ids = [it["id"] for it in items]
    documents = texts
    metadatas = [
        {
            "type": it["type"],
            "card_id": it["id"],
            "term": (
                it["card"].get("canonical_term")
                or it["card"].get("title")
                or it["id"]
            ),
            "school": it["card"].get("school") or "",
            "file_path": it["file_path"],
        }
        for it in items
    ]
    embeddings = [v.tolist() for v in vecs]

    # ChromaDB 单次 add 上限通常是 ~5000，分批
    BATCH = 1000
    for i in range(0, len(ids), BATCH):
        collection.add(
            ids=ids[i : i + BATCH],
            embeddings=embeddings[i : i + BATCH],
            documents=documents[i : i + BATCH],
            metadatas=metadatas[i : i + BATCH],
        )

    log.info(
        "✓ 完成。%d 个向量（%d 维）已持久化到 %s",
        len(items), embedder.dim, index_dir,
    )
    log.info(
        "下一步：python tools/kb_retrieve.py \"你的问题\" --kb \"%s\"",
        kb_dir,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
