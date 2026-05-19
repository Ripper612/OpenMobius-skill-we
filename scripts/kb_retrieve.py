#!/usr/bin/env python3
"""知识库检索工具：query → top-K 相关 cards 的完整内容。

这是个**纯检索工具**，不调 LLM 生成回答。
设计目的：被 Skill（Claude Code / Codex / Hermes / OpenClaw）调用，
让平台 LLM 拿到检索结果后自己综合答案。

Usage:
    python tools/kb_retrieve.py "什么是 Fair Value Gap"
    python tools/kb_retrieve.py "FVG 怎么入场" --top-k 5
    python tools/kb_retrieve.py "ICT killzone" --kb "materials/Education - ICT/knowledge_base"
    python tools/kb_retrieve.py "BTC reversal" --type case
    python tools/kb_retrieve.py "Order Block" --school ICT
    python tools/kb_retrieve.py "..." --format json   # JSON 输出便于程序解析
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent        # skills/OpenMobius-skill/scripts/
SKILL_DIR = THIS_DIR.parent                       # skills/OpenMobius-skill/
sys.path.insert(0, str(THIS_DIR))                 # 让 _lib 包可见

from _lib.embedder import get_embedder  # noqa: E402
from _lib.retriever import Retriever  # noqa: E402


log = logging.getLogger("kb_retrieve")


# 默认知识库（如果用户不指定 --kb）
DEFAULT_KB = SKILL_DIR / "knowledge_base"


def format_card_text(card_full: dict, retrieved_doc: str, header: str) -> str:
    """把检索结果格式化成 LLM 可读的 markdown 块。"""
    out = [f"## {header}"]

    if card_full.get("canonical_term"):
        out.append(f"**Term**: {card_full['canonical_term']}")
        if card_full.get("aliases"):
            out.append(f"**Aliases**: {', '.join(card_full['aliases'])}")
        if card_full.get("school"):
            out.append(f"**School**: {card_full['school']}")
        out.append("")
        if card_full.get("definition"):
            out.append(f"**Definition**: {card_full['definition']}")
        if card_full.get("identification_rules"):
            out.append("\n**Identification rules**:")
            for r in card_full["identification_rules"]:
                out.append(f"- {r}")
        if card_full.get("trading_implication"):
            out.append(f"\n**Trading implication**: {card_full['trading_implication']}")
        if card_full.get("common_mistakes"):
            out.append("\n**Common mistakes**:")
            for m in card_full["common_mistakes"]:
                out.append(f"- {m}")
        related = card_full.get("related_concepts") or []
        if related:
            rel_strs = [r.get("term") if isinstance(r, dict) else r for r in related]
            rel_strs = [s for s in rel_strs if s]
            if rel_strs:
                out.append(f"\n**Related**: {', '.join(rel_strs)}")
        stats = card_full.get("stats") or {}
        if stats.get("source_count"):
            out.append(f"\n_合并自 {stats['source_count']} 个视频源_")
    elif card_full.get("title"):
        # case 卡
        out.append(f"**Title**: {card_full['title']}")
        if card_full.get("school"):
            out.append(f"**School**: {card_full['school']}")
        meta = []
        if card_full.get("asset"):
            meta.append(f"asset={card_full['asset']}")
        if card_full.get("timeframe"):
            meta.append(f"timeframe={card_full['timeframe']}")
        if meta:
            out.append(f"**Market**: {', '.join(meta)}")
        out.append("")
        if card_full.get("market_context"):
            out.append(f"**Context**: {card_full['market_context']}")
        if card_full.get("key_observation"):
            out.append(f"**Observation**: {card_full['key_observation']}")
        if card_full.get("analysis_steps"):
            out.append("\n**Analysis steps**:")
            for s in card_full["analysis_steps"]:
                out.append(f"- {s}")
        if card_full.get("lessons"):
            out.append(f"\n**Lessons**: {card_full['lessons']}")
        related = card_full.get("illustrates_concepts") or []
        if related:
            rel_strs = [r if isinstance(r, str) else r.get("term", "") for r in related]
            rel_strs = [s for s in rel_strs if s]
            if rel_strs:
                out.append(f"\n**Illustrates concepts**: {', '.join(rel_strs)}")
        if card_full.get("primary_image"):
            out.append(f"\n**Primary image**: {card_full['primary_image']}")
    else:
        # 兜底：直接用 embed 时的文本
        out.append(retrieved_doc)

    return "\n".join(out)


def main() -> int:
    p = argparse.ArgumentParser(
        description="检索知识库 top-K 卡片（不调 LLM，留给平台 LLM 综合）",
    )
    p.add_argument("query", help="自然语言查询")
    p.add_argument(
        "-k", "--top-k", type=int, default=5,
        help="返回 top-K 条（默认 5）",
    )
    p.add_argument(
        "--kb", default=None,
        help=f"知识库目录（默认: {DEFAULT_KB.relative_to(SKILL_DIR)}）",
    )
    p.add_argument(
        "--embedder", default="local",
        choices=["local", "openai"],
        help="embedding provider（默认 local nomic-embed）",
    )
    p.add_argument(
        "--type", default=None,
        choices=["concept", "case"],
        help="只检索某类型卡片",
    )
    p.add_argument(
        "--school", default=None,
        help="只检索某流派（如 ICT / SMC / Wyckoff）",
    )
    p.add_argument(
        "--format", default="markdown",
        choices=["markdown", "json", "compact"],
        help="输出格式：markdown（默认，LLM 友好）/ json / compact（一行一张）",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.WARNING if not args.verbose else logging.DEBUG,
        format="%(levelname)-5s %(message)s",
    )

    kb_dir = Path(args.kb) if args.kb else DEFAULT_KB
    if not kb_dir.is_dir():
        log.error("知识库目录不存在: %s", kb_dir)
        return 1

    embedder = get_embedder(args.embedder)
    try:
        retriever = Retriever(kb_dir, embedder)
    except (FileNotFoundError, RuntimeError) as e:
        log.error(str(e))
        return 1

    cards = retriever.search(
        query=args.query,
        top_k=args.top_k,
        filter_school=args.school,
        filter_type=args.type,
    )

    if not cards:
        print("(no results)")
        return 0

    if args.format == "json":
        out = []
        for c in cards:
            full = retriever.get_full_card(c)
            out.append({
                "card_id": c.card_id,
                "type": c.card_type,
                "term": c.term,
                "school": c.school,
                "distance": round(c.distance, 4),
                "file_path": c.file_path,
                "card": full,
            })
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    if args.format == "compact":
        for i, c in enumerate(cards, 1):
            print(
                f"[{i}] {c.term:<40}"
                f" type={c.card_type:<7} school={c.school or '-':<10}"
                f" distance={c.distance:.3f}"
                f" → {c.file_path}"
            )
        return 0

    # markdown
    print(f"# 检索结果：'{args.query}'（top {len(cards)}）\n")
    for i, c in enumerate(cards, 1):
        full = retriever.get_full_card(c) or {}
        header = (
            f"[{i}] {c.term}"
            f"  _(type={c.card_type}, school={c.school or '-'}, "
            f"distance={c.distance:.3f})_"
        )
        print(format_card_text(full, c.document, header))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
