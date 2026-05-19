
# OpenMobius-skill — ICT/SMC Trading Knowledge Skill

A unified skill for four interaction modes with a curated knowledge base (380 concept cards + 584 case cards) distilled from 130 ICT/SMC trading-analysis videos.

**Core principle**: every claim must be grounded in (a) visible chart evidence OR (b) a retrieved knowledge-base rule. **No fabrication** — when uncertain, state so explicitly.

## Always retrieve from the knowledge base first

The knowledge base contains rule-based identification criteria and documented pitfalls that generic training data lacks. **Always retrieve first, then synthesize** — don't answer trading questions from memory alone.

## Output format is mandatory

Every workflow ends in a synthesis step with `##` section headings (see
each `workflows/<name>.md`'s final step). **Those headings MUST appear
verbatim in your user-facing reply**, in the order specified, in the
user's language. Free-form prose that omits the headings is an
**incomplete reply** and must be revised before sending.

## Scenario Router

Pick the right sub-workflow based on the user's input. Each workflow has detailed steps in its own document:

| User input | Workflow | Document to read |
|---|---|---|
| Concept question, **no chart, no data, no asset name** ("什么是 FVG", "how to identify OB", "止损放哪里") | **Q&A** | `workflows/qna.md` |
| **Chart attached** + any question about it ("分析", "看一下", "走势", "where to enter", "what's happening") | **Analyze** (auto-fetches real OHLCV + annotation) | `workflows/analyze.md` |
| User explicitly asks to **draw/annotate** an image, OR follows up after analysis with "把这个标在图上" | **Annotate** | `workflows/annotate.md` |
| User pastes **OHLCV data** OR mentions **asset + timeframe by name** without chart ("BTC 1h 怎么样" / pastes CSV / "茅台日线") | **Kline analysis** | `workflows/klines.md` |

**How to route**:

1. Read this SKILL.md to understand the routing
2. Identify which scenario the user is in
3. Use the `Read` tool to load the relevant workflow document (relative to this SKILL.md: `workflows/<name>.md`)
4. Follow that workflow's steps

> **Important — Analyze workflow now auto-fetches data**: If a chart is attached AND the asset/timeframe is identifiable from the chart, `analyze.md` will fetch real OHLCV from Mobius API to **complement visual analysis with precise prices**. This is on by default; user can opt out by saying "只看图不拉数据" / "skip data fetch".

> **Note**: The **Analyze** workflow already auto-generates an annotated image as its final step. You do NOT need to separately invoke Annotate after Analyze unless the user wants to re-render with different parameters (different colors, new bbox, JSON-only output, etc.).

## Two chart generation paths

When the user wants a visual chart, choose the right tool:

| Situation | Tool | Output |
|---|---|---|
| User uploaded their own chart image; wants markup ON that image | `scripts/kb_draw_annotation.py` (PIL) | Annotated copy of original image |
| No chart image, OR user wants a clean new chart | `scripts/kb_klines.py chart` + `render` | Fresh TradingView-grade chart: pure K-lines + knowledge-base overlays (FVG/OB rectangles, sweep lines, swing markers, trade-setup lines) |

For path #2, the typical pipeline is:

```bash
# 1. Pull pure K-lines (no indicators) → panels payload skeleton (items=[])
.venv/bin/python scripts/kb_klines.py chart \
    --query "BTC" --interval 1h --limit 200 \
    --output /tmp/chart.json

# 2. Run analyze (on fetch output) to get suggested_overlay_items
.venv/bin/python scripts/kb_klines.py fetch --query "BTC" --interval 1h --limit 200 --output /tmp/data.json
.venv/bin/python scripts/kb_klines.py analyze --input /tmp/data.json --format json --output /tmp/features.json

# 3. (LLM step) Merge selected suggested_overlay_items + your trade_setup hlines
#    into /tmp/chart.json's panels[0].items. Item types:
#      - rectangle:  FVG / Order Block / Killzone zones  (price_top + price_bottom + time_start [+ time_end])
#      - hline:      Entry / SL / Target / Swept levels
#      - markers:    Swing points, sweep candles
#    All items use style.role from this set (see "Style role reference" below).

# 4. Render PNG
.venv/bin/python scripts/kb_klines.py render \
    --input /tmp/chart.json --output /tmp/chart.png \
    --theme dark --width 1400 --height 900
```

## Indicator queries

When the user explicitly asks about **technical indicator values**
("RSI 多少 / MACD 怎么样 / EMA 价位 / 看 ATR / Bollinger 上下轨"):

```bash
.venv/bin/python scripts/kb_klines.py indicators \
    --query "BTC" --interval 1h \
    --inds "rsi:14,macd:12:26:9,ema:50,ema:200" \
    --limit 200 \
    --format compact
```

Format `<inds>`: `name:p1:p2,name:p1` (e.g. `rsi:14`, `macd:12:26:9`,
`bollinger:20:2`). Supported: ema/sma/wma/rsi/atr/macd/bollinger/stoch/cci/adx/vwap/obv/cvd.

Output modes:
- `--format json` (default): full API response (klines + indicators with columns/data/explain)
- `--format compact`: LLM-friendly current-value summary (last row only)

Use `compact` when synthesizing a verbal answer; use `json` when downstream
needs raw rows.

**Two knowledge sources you have**:

1. **Mobius API's indicator knowledge base** (the `explain` field in the API
   response — included by default in both `json` and `compact` output):
   - `category` — indicator class (trend / oscillator / volatility / volume / ...)
   - `desc` — one-line meaning
   - **`summary_focus`** — 3-5 analysis dimensions. **This is the most
     important field**. It tells you exactly what to look at for this
     indicator (e.g. RSI: "current zone / oversold duration / trend / cross-tf
     consistency / divergence vs price"). **Structure your verbal answer
     around these dimensions** — don't just dump the number.
   - `outputs` — meaning of each output column
   - `signals` — signal-firing rules

2. **Local ICT knowledge base** (`kb_retrieve.py` — ICT/SMC concepts only,
   NO traditional indicator cards). Useful when the indicator analysis
   surfaces an ICT concept (e.g. divergence → cross-ref SMT Divergence card;
   displacement → cross-ref ICT Displacement card). **Don't waste a kb_retrieve
   call looking for "RSI" or "MACD" — those cards don't exist in the KB**.

### Recommended LLM behavior

1. Call `indicators --format compact` to get values + `summary_focus`
2. Structure your reply as bullet points matching each `summary_focus` item
3. For each dimension, state the observation in plain prose with the number
4. If ICT-related themes surface (divergence, displacement, structure shift),
   optionally call `kb_retrieve.py` for the relevant ICT card

**Constraints**:
1. **Text-only**: indicators are reported in prose / tables.
   **DO NOT render indicators on charts** — chart rendering stays
   knowledge-base-only (FVG/OB/Sweep). If user wants both, give text indicator
   answer AND a separate KB-only chart.

## Chart label rules (CRITICAL)

Labels on the chart are rendered next to the right price-axis. **Long labels eat into K-line area and overlap each other.**

- ✅ Short: `"Short 2202"`, `"SL 2231"`, `"T1 2176"`, `"bear FVG"`
- ❌ Long: `"Short Entry 2202 (FVG mid)"`, `"SL 2230.80 (above 4h OB)"`

Put **rationale** in your conversational reply (prose), not in the chart label.

**Item count guideline**: total items in `panels[0].items` ≤ 8 (2 FVG/OB rectangles + 2 sweep hlines + 2 swing markers + entry/SL/target ≤ 4 lines).

## Style role reference (panels.items style.role)

| Role | Used for | Color hint |
|---|---|---|
| `bullish` / `bearish` | Generic up/down | green / red |
| `muted` | Background hints, current price line | gray |
| `fvg` / `fvg_bear` | Bullish / Bearish Fair Value Gap rectangles | green / red |
| `ob` / `ob_bear` | Bullish / Bearish Order Block rectangles | purple / dark-purple |
| `breaker` | Breaker Block rectangles | purple |
| `liquidity` | Liquidity Sweep hline + markers | orange |
| `entry_long` | Long entry price | green |
| `entry_short` | Short entry price | red |
| `stop_loss` | Stop Loss | red |
| `target` | T1/T2/T3 | blue |

Colors auto-resolve from theme (dark/light) — only specify `role`, never hex colors.

## Shared Rules (apply to all three workflows)

1. **No fabrication** — every price level cited must be visible on the chart or computed from a retrieved rule applied to a visible price.
2. **Cite the knowledge base** — every confirmed pattern must reference a retrieved card. Format: `"Rule N of <concept>: '<rule text>' — visible at <evidence>"`.
3. **Language rules**:
   - Prose language matches user's input: Chinese question → Chinese prose; English → English prose
   - Technical terms stay in English regardless of prose language: FVG, Order Block, Breaker, CISD, OTE, Liquidity Sweep, Killzone, IFVG, MSS, BOS, CHoCH, Displacement, etc. Do NOT translate to "公允价值缺口" — keep "Fair Value Gap" or "FVG"
   - Numbers/prices/percentages: keep original form
4. **State uncertainty explicitly** — prefer `null` or "uncertain — <reason>" over speculation.
5. **Multiple retrievals are OK** — for complex charts or multi-concept questions, run `kb_retrieve.py` more than once with different keyword combinations.
6. **Probability tiers (5 levels, semantic only)** — use exactly these names; do NOT expose internal percentages to users:

   | Tier | 中文 | Meaning |
   |---|---|---|
   | `very_high` | 很高 | Dominant scenario; strong rule-based confirmation |
   | `high` | 较高 | Primary plausible scenario; most rules confirm |
   | `medium` | 中等 | Plausible but partial rule confirmation |
   | `low` | 较低 | Edge case; speculative |
   | `very_low` | 很低 | Tail risk; mentioned for completeness only |

7. **Non-trading content** — if the image or question is not about trading, say so and stop.

## Tools

All scripts live in `${SKILL_DIR}/scripts/` and run via `${SKILL_DIR}/.venv/bin/python`. `${SKILL_DIR}` is the directory containing this SKILL.md (typically `~/.claude/skills/OpenMobius-skill/` after install, or the repo root after `git clone`). When invoking shell commands, **always `cd "${SKILL_DIR}"` first** so relative paths resolve correctly.

| Tool | Purpose |
|---|---|
| `scripts/kb_retrieve.py "<query>" --top-k 5` | Vector retrieval from knowledge base |
| `scripts/kb_klines.py resolve "<name>"` | Natural name → canonical asset spec |
| `scripts/kb_klines.py fetch --query "<name>" --interval <tf> --with-htf` | Pull real OHLCV (+ HTF) from Mobius API |
| `scripts/kb_klines.py parse --input <file>` | Parse pasted CSV/JSON/Markdown → standard OHLCV |
| `scripts/kb_klines.py analyze --input <ohlcv.json>` | Extract features (swing/FVG/OB/sweep/displacement/structure). Add `--format json` to get structured features + `suggested_overlay_items` |
| `scripts/kb_klines.py chart --query <name> --interval <tf>` | Pull pure K-lines (no indicators) → panels payload (items empty, ready for LLM to fill with KB overlays) |
| `scripts/kb_klines.py render --input <panels.json> --output <png>` | Render panels JSON → PNG via Playwright + lightweight-charts (TradingView-grade chart) |
| `scripts/kb_klines.py indicators --query <name> --interval <tf> --inds <list>` | Pull tech indicator values (RSI/MACD/EMA/...) — text output only, NOT rendered on charts |
| `scripts/kb_draw_annotation.py --json <path>` | Render annotation JSON onto chart (PIL, for **user-uploaded** images) |
| `scripts/kb_phase_b_to_c.py --input <analysis.json> --image <png> --output <annotated.png>` | Convert analysis JSON → annotated image (one shot) |
| `scripts/build_index.py` | Build the vector index from `knowledge_base/{concepts,cases}/` (one-time) |
| `scripts/kb_doctor.py` | Environment health check (run if anything's broken) |

Common options for `scripts/kb_retrieve.py`:
- `--top-k N` (default 5)
- `--type concept|case` (filter by card type)
- `--school <NAME>` (e.g. `--school ICT`)
- `--format markdown|json|compact`

## Setup (one-time)

```bash
cd /path/to/OpenMobius-skill       # the skill directory
bash install.sh                  # creates .venv, installs deps, builds index, checks fonts
```

The installer auto-registers the skill with Claude Code. If anything breaks
(CJK label garbling, retrieval errors, missing index, etc.):

```bash
cd "${SKILL_DIR}" && .venv/bin/python scripts/kb_doctor.py
```

## Examples (quick reference; full examples in each workflow doc)

**Example 1 — Concept Q&A** (no chart, no asset name):
> User: "什么是 Fair Value Gap，怎么交易"
> → Read `workflows/qna.md` → run kb_retrieve → synthesize answer in Chinese with English technical terms

**Example 2 — Chart analysis** (with chart, identifiable asset):
> User: [attaches BTC 4H chart] "分析一下当前行情"
> → Read `workflows/analyze.md` → identify asset → auto-fetch real OHLCV from Mobius → 5-section reply with **precise prices** + auto-annotated image

**Example 3 — Annotation only** (follow-up):
> User: [after analysis JSON exists] "把刚才分析的画到图上"
> → Read `workflows/annotate.md` → call kb_phase_b_to_c.py → output annotated image

**Example 4 — Kline analysis** (no chart):
> User: "BTC 1h 现在怎么样" (or pastes a CSV of OHLCV)
> → Read `workflows/klines.md` → fetch/parse → analyze (extract features) → retrieve → 5-section reply with exact data-grounded prices
