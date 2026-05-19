#!/usr/bin/env python3
"""Build the vector index for the skill's knowledge_base/.

This script has two modes:

  Default mode — fast install path (used by every user):
    Reads pre-computed embeddings from each JSON card's `_embedding` field
    and writes them into ChromaDB. Takes a few seconds. Does NOT need the
    nomic embedding model.

  --regenerate — KB maintainer path:
    Loads the embedding model, computes embeddings for every card, writes
    them back into the JSON cards' `_embedding` / `_embedding_model` fields,
    then writes ChromaDB. Takes 30 s – 10 min depending on CPU.

Usage:
    python scripts/build_index.py                       # fast load from JSON
    python scripts/build_index.py --force               # rebuild ChromaDB only
    python scripts/build_index.py --regenerate          # KB maintainer: recompute
    python scripts/build_index.py --regenerate --force  # full rebuild
    python scripts/build_index.py --limit 10            # only first N (testing)
    python scripts/build_index.py --regenerate --embedder openai  # different model
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional


THIS_DIR = Path(__file__).resolve().parent        # scripts/
SKILL_DIR = THIS_DIR.parent                       # skill root
sys.path.insert(0, str(THIS_DIR))                 # for _lib import


log = logging.getLogger("build_kb_index")


# The canonical embedding model used to populate `_embedding` fields in the
# bundled knowledge_base/ JSON cards. If --regenerate uses a different model
# (e.g. openai), this constant doesn't change — the per-card
# `_embedding_model` field reflects the actual model that produced its vector.
EXPECTED_MODEL = "nomic-ai/nomic-embed-text-v1.5"
EXPECTED_DIM   = 768


def build_concept_text(card: dict) -> str:
    """Compose a concept card into embedding-friendly plain text."""
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
        rel_strs = [
            r.get("term") if isinstance(r, dict) else r
            for r in related
            if r
        ]
        if rel_strs:
            parts.append(f"Related concepts: {', '.join(filter(None, rel_strs))}")
    return "\n\n".join(parts)


def build_case_text(card: dict) -> str:
    """Compose a case card into embedding-friendly plain text."""
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
    """Return all concept+case cards as [{id, type, file_path, card, text}]."""
    items: list[dict] = []

    concepts_dir = kb_dir / "concepts"
    if concepts_dir.is_dir():
        for f in sorted(concepts_dir.glob("*.json")):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception as e:  # noqa: BLE001
                log.warning("skipping corrupt %s: %s", f.name, e)
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
                log.warning("skipping corrupt %s: %s", f.name, e)
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


def write_card_json(file_path: Path, card_data: dict) -> None:
    """Atomic write a card JSON back to disk (UTF-8, indent=2, preserves CJK)."""
    tmp = file_path.with_suffix(file_path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(card_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(file_path)


def load_embeddings_from_cards(items: list[dict]) -> tuple[list[list[float]], list[str]]:
    """Read pre-computed embeddings from each card's `_embedding` field.

    Returns (embeddings, missing_or_stale_ids).
    """
    embeddings: list[list[float]] = []
    bad: list[str] = []
    for it in items:
        emb = it["card"].get("_embedding")
        model = it["card"].get("_embedding_model")
        if (
            emb is None
            or model != EXPECTED_MODEL
            or not isinstance(emb, list)
            or len(emb) != EXPECTED_DIM
        ):
            bad.append(it["id"])
            embeddings.append([])  # placeholder, won't be used
            continue
        embeddings.append(emb)
    return embeddings, bad


def main() -> int:
    p = argparse.ArgumentParser(
        description="Build vector index for the skill's knowledge_base/."
    )
    p.add_argument(
        "--kb", default=None,
        help=f"knowledge_base directory (default {SKILL_DIR / 'knowledge_base'})",
    )
    p.add_argument(
        "--embedder", default="local",
        choices=["local", "openai"],
        help="(--regenerate) embedding provider — local (nomic) or openai",
    )
    p.add_argument(
        "--force", action="store_true",
        help="rebuild ChromaDB even if it already exists",
    )
    p.add_argument(
        "--regenerate", action="store_true",
        help="recompute embeddings and write them back into each JSON card "
             "(KB maintainer mode; needs the embedding model). "
             "Default mode reads existing embeddings from JSON (no model needed).",
    )
    p.add_argument(
        "--limit", type=int, default=None,
        help="only process first N cards (testing)",
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
        log.error("knowledge_base/ not found: %s", kb_dir)
        return 1

    index_dir = kb_dir / "_index"

    # Existence check for the ChromaDB output
    if index_dir.exists() and not args.force:
        log.error(
            "Index already exists: %s\nAdd --force to rebuild.", index_dir,
        )
        return 1
    if args.force and index_dir.exists():
        import shutil  # noqa: PLC0415
        log.info("--force: removing old index %s", index_dir)
        shutil.rmtree(index_dir)

    # Collect cards
    log.info("Scanning knowledge base: %s", kb_dir)
    items = collect_cards(kb_dir, limit=args.limit)
    n_concept = sum(1 for it in items if it["type"] == "concept")
    n_case = sum(1 for it in items if it["type"] == "case")
    log.info("Found %d concept + %d case = %d cards", n_concept, n_case, len(items))
    if args.limit:
        log.info("(--limit %d applied)", args.limit)
    if not items:
        log.error("No cards to index.")
        return 1

    # ── Two paths to obtain embeddings ──────────────────────────────────────

    if args.regenerate:
        # Compute fresh embeddings via the model, write back to JSON
        from _lib.embedder import get_embedder  # noqa: PLC0415

        log.info("[regenerate] Loading embedder (%s)...", args.embedder)
        embedder = get_embedder(args.embedder)
        log.info("[regenerate] embedding dim = %d", embedder.dim)

        texts = [it["text"] for it in items]
        log.info("[regenerate] Embedding %d cards (this can take 30 s – 10 min)...", len(texts))
        vecs = embedder.embed_documents(texts)

        # Persist embeddings into each JSON card
        log.info("[regenerate] Writing embeddings back into JSON cards...")
        model_label = getattr(embedder, "model_name", "unknown")
        for it, vec in zip(items, vecs):
            it["card"]["_embedding"]       = [float(x) for x in vec.tolist()]
            it["card"]["_embedding_model"] = model_label
            json_path = kb_dir / it["file_path"]
            write_card_json(json_path, it["card"])
        log.info("[regenerate] Updated %d JSON files", len(items))

        embeddings_for_chroma = [v.tolist() for v in vecs]
        embedding_dim = embedder.dim
    else:
        # Load embeddings directly from each JSON card
        log.info("[load] Reading embeddings from JSON cards...")
        embeddings_for_chroma, bad = load_embeddings_from_cards(items)
        if bad:
            log.error("")
            log.error("%d / %d cards have missing / stale / wrong-dim embeddings:",
                      len(bad), len(items))
            for cid in bad[:5]:
                log.error("  - %s", cid)
            if len(bad) > 5:
                log.error("  ... and %d more", len(bad) - 5)
            log.error("")
            log.error("To regenerate embeddings (needs the nomic model, takes 30 s – 10 min):")
            log.error("  python scripts/build_index.py --regenerate --force")
            return 1
        log.info(
            "[load] All %d cards have valid embeddings (%s, %dd)",
            len(items), EXPECTED_MODEL, EXPECTED_DIM,
        )
        embedding_dim = EXPECTED_DIM

    # ── Write to ChromaDB ───────────────────────────────────────────────────

    log.info("Writing ChromaDB collection...")
    import chromadb  # noqa: PLC0415
    client = chromadb.PersistentClient(path=str(index_dir))
    collection = client.create_collection(
        name="knowledge_base",
        metadata={"hnsw:space": "cosine"},
    )

    ids = [it["id"] for it in items]
    documents = [it["text"] for it in items]
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

    BATCH = 1000
    for i in range(0, len(ids), BATCH):
        collection.add(
            ids=ids[i : i + BATCH],
            embeddings=embeddings_for_chroma[i : i + BATCH],
            documents=documents[i : i + BATCH],
            metadatas=metadatas[i : i + BATCH],
        )

    log.info(
        "✓ Index built: %d vectors (%d-d) → %s",
        len(items), embedding_dim, index_dir,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
