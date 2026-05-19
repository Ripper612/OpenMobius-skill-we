# Workflow: Kline Data Analysis (no chart required)

For when the user provides **structured K-line data** (pasted) or just **asset name + timeframe**, without necessarily attaching a chart image.

## When this workflow applies

- User pastes OHLCV data (CSV / JSON / Markdown table / TradingView export)
- User mentions an asset + timeframe by name without a chart: "BTC 1h 怎么样" / "茅台日线分析下" / "ETH 5m 现在能做空吗"
- User explicitly asks for "real data" / "实时数据" / "拉一下数据"

## When NOT to use

- User attached a chart and asked for analysis → use `analyze.md` (which itself auto-fetches data as Step 1e)
- Pure concept question with no asset / no data → use `qna.md`
- User wants annotation → use `annotate.md`

## The data sources

This workflow accepts **two data sources**:

| Source | When |
|---|---|
| **A. Mobius API fetch** | User gave asset name (e.g. "BTC 1h") — call API to get real OHLCV |
| **B. User-pasted data** | User pasted CSV/JSON/table — parse it locally |

Both result in standard OHLCV → feed to feature extractor → 5-section output.

## Mandatory Workflow (4 steps)

### Step 1: Acquire data

**Path A — fetch from API**:

```bash
.venv/bin/python scripts/kb_klines.py fetch \
    --query "<asset natural name, e.g. '比特币' or 'BTC' or 'ETH' or '茅台'>" \
    --interval <1m|5m|15m|30m|1h|4h|1d> \
    --limit 200 \
    --with-htf \
    --output /tmp/<symbol>_<interval>.json
```

If the API is unreachable, fall back to Path B (ask user to paste OHLCV).

- `--query` accepts Chinese natural names ("比特币" "以太坊" "茅台") + English aliases ("BTC" "ETH" "TSLA")
- `--with-htf` auto-fetches one timeframe up for HTF bias (1h → 4h, 5m → 15m, etc.)
- API supports: crypto (binance/bybit/okx/hyperliquid), stocks (cn/hk/us), forex

If user gave a canonical symbol directly (e.g. "BTCUSDT spot"), use:
```bash
kb_klines.py fetch --exchange binance --market spot --symbol BTCUSDT --interval 1h ...
```

**Path B — parse user-pasted data**:

```bash
echo "<user pasted text>" | \
.venv/bin/python scripts/kb_klines.py parse \
    --symbol <symbol> \
    --interval <tf> \
    --output /tmp/parsed.json
```

The parser auto-detects: JSON array (binance-style), CSV with header, Markdown table, whitespace-separated table.

**If parser fails** (rare unusual format): you (the LLM) can convert the user's text into a JSON object array `[{"time": ..., "open": ..., "high": ..., "low": ..., "close": ..., "volume": ...}]` and feed via stdin to `parse`.

### Step 2: Extract features

```bash
.venv/bin/python scripts/kb_klines.py analyze \
    --input /tmp/<symbol>_<interval>.json \
    --output /tmp/<symbol>_features.txt
```

The output is a structured text summary including:
- **Market state**: current close, range, trend %, ATR(14)
- **Structure**: swing sequence (HH/HL/LH/LL), BOS/CHoCH events
- **FVG candidates**: untested / partial bullish & bearish FVGs with mitigation %
- **Order Block candidates**: bullish/bearish OB with displacement strength
- **Liquidity Sweep candidates**: buy-side / sell-side sweeps with wick size
- **Displacement candles**: > 2× ATR moves with magnitude
- **Volume anomalies**: > 2× avg volume candles

If HTF was fetched, summary includes both **primary** and **HTF** sections.

Read this file via the `Read` tool — it's plaintext, ~50-100 lines.

### Step 3: Retrieve knowledge base concepts

Based on what the feature extractor surfaced, retrieve relevant ICT/SMC concepts:

```bash
.venv/bin/python scripts/kb_retrieve.py "<keywords>" --top-k 5
```

Pick keywords from the surfaced features:
- If sweeps detected → "liquidity sweep reversal CISD"
- If displacement detected → "displacement order block continuation"
- If FVG untested → "fair value gap mitigation entry"
- HTF/LTF align question → "HTF LTF alignment bias"

Multiple retrievals encouraged when several patterns surface.

### Step 4: (Optional) Generate a fresh chart image

If the user wants a visual chart, build it from pure K-lines + knowledge-base overlays (no indicators — those are out of scope for this skill).

```bash
# 1. Pull pure K-lines → panels payload skeleton (items=[])
.venv/bin/python scripts/kb_klines.py chart \
    --query "<asset>" --interval <tf> --limit 200 \
    --output /tmp/<sym>_chart.json
```

Then merge into `panels[0].items` your KB overlays from the analyze features JSON
(field `suggested_overlay_items`, which already contains FVG/OB rectangles, sweep
hlines + markers, swing markers — auto-generated from the analysis) PLUS your
own trade-setup hlines.

**Item types**:

| Type | Use for | Required fields |
|---|---|---|
| `rectangle` | FVG / Order Block / Killzone zones | `time_start`, `price_top`, `price_bottom`, `label`, `style.role` (`time_end` optional, omit = extend to right) |
| `hline` | Entry / SL / Target / Swept level / Current price | `value`, `label`, `style.role` |
| `markers` | Swing point, sweep candle | `data: [{time, shape, position, text}]`, `style.role` |

**Style roles** (color auto-resolved from theme):

| Role | Semantic |
|---|---|
| `fvg` / `fvg_bear` | Bullish / Bearish Fair Value Gap |
| `ob` / `ob_bear` | Bullish / Bearish Order Block |
| `breaker` | Breaker Block |
| `liquidity` | Liquidity Sweep |
| `entry_long` / `entry_short` | Long / Short entry |
| `stop_loss` / `target` | SL / TP |
| `bullish` / `bearish` / `muted` | Generic up / down / hint |

**Critical: keep labels short.** They're rendered next to the price-axis on the right side and long labels eat into the K-line area.

```
✓ "Short 2202"             (≤ 12 chars including price)
✓ "SL 2231"
✓ "T1 2176"
✓ "bear FVG"
✗ "Short Entry 2202 (FVG mid)"     ← 太长，挡 K 线
✗ "SL 2230.80 (above 4h OB)"
✗ "T1 2176.09 (HL sweep)"
```

Put rationale ("Entry at FVG mid", "SL above 4h OB", "T1 at HL sweep") in **prose**, not in the chart label.

**Example** — short setup at 78500, SL 80000, T1 77000:

```json
{"type": "hline", "value": 78500, "label": "Short 78500",
 "style": {"role": "entry_short", "width": 2}}
{"type": "hline", "value": 80000, "label": "SL 80000",
 "style": {"role": "stop_loss", "dash": "dashed", "width": 2}}
{"type": "hline", "value": 77000, "label": "T1 77000",
 "style": {"role": "target", "width": 2}}
```

**Overlay item count guideline**: keep total items in `panels[0].items` ≤ 8.
- From `suggested_overlay_items`: pick the **2 most relevant** rectangles + **1-2 sweep lines** + the **most recent 1-2 swing markers**.
- Trade setup: entry / SL / 1-2 targets (4 hlines max).
- More than 8 → labels overlap and crowd the right edge.

**Example** — bearish FVG zone 80300-80500 starting from candle time 1747000000:

```json
{"type": "rectangle",
 "time_start": 1747000000,
 "time_end":   null,
 "price_top":    80500,
 "price_bottom": 80300,
 "label": "bearish FVG",
 "style": {"role": "fvg_bear", "fill_opacity": 0.15, "border_width": 1, "dash": "dashed"}}
```

Then render to PNG:

```bash
.venv/bin/python scripts/kb_klines.py render \
    --input /tmp/<sym>_chart.json \
    --output /tmp/<sym>_chart.png \
    --theme dark --width 1400 --height 900
```

Output is a TradingView-grade PNG ready to include in your reply.

### Step 5: Synthesize + output

**Output format is MANDATORY.** The reply MUST use the four section
headings below **verbatim**, in this exact order, in the user's language:

- `## 结论 / Conclusion`
- `## 分析逻辑 / Analysis`
- `## 后续走势与操作 / Outcome Cases`
- `## 风险与失效 / Risks & Invalidation`

A fifth section `## 信息缺失 / Missing Information` is optional and only
added when confidence ≤ medium.

Free-form prose without these `##` headings is an **incomplete reply** and
must be rejected before sending to the user.

The template below is the only acceptable structure (this workflow has no
image input, so the auto-annotation step from `analyze.md` is omitted):

```markdown
## 结论 / Conclusion
- **Bias**: <long-leaning / short-leaning / neutral / uncertain>
- **Confidence**: <very_high / high / medium / low / very_low>
- **操作建议 / Action**: <one-line concrete recommendation with PRECISE prices from data>
- **关键依据 / Key evidence (≤3)**: <bullet list of 2-3 most decisive signals>

## 分析逻辑 / Analysis

1. **数据观察 / What's in the data**: cite specific price levels from feature summary
2. **HTF/LTF 对齐 / HTF-LTF alignment** (if HTF available): bias confirmation
3. **知识库匹配 / Knowledge base hits**: which retrieved cards apply
4. **规则推导 / Rule application**: cite specific rule + EXACT data evidence
5. **驳回的可能性 / Rejected hypotheses**

## 后续走势与操作 / Outcome Cases

2-3 scenarios using 5-tier probability. Each case has:
- **Case <letter> (<probability>)**: <scenario>
- **触发信号 / Trigger signals**: <observable signals>
- **操作建议 / Action**: <concrete entry/stop/target with PRECISE prices>
- **失效条件 / Invalidation**: <what kills this case>

## 风险与失效 / Risks & Invalidation
- **主要风险 / Main risks** (from cards' common_mistakes)
- **整体失效 / Overall invalidation**: <precise price level>
- **监控提示 / Monitoring hints**

## 信息缺失 / Missing Information (optional, only if confidence ≤ medium)
```

After the 5 sections, append:
```
📊 数据源 / Data: <fetch/parse> @ <symbol> <interval> (<count> candles)
📂 特征摘要 / Features: <path to features.txt>
🖼️ 行情图 / Chart: <path to rendered PNG>   ← only if Step 4 ran
```

## Key advantages over visual-only

In this workflow, prices are **exact** (from real data), not estimated. Reflect this in the output:

| Visual-only (analyze.md without API) | Data-grounded (this workflow) |
|---|---|
| "FVG around 73K-74.5K" | "Bullish FVG 73,182 - 74,210, 33% mitigated (touched 73,495 once)" |
| "swing high near 95K" | "Swing high at 95,847 (12 bars / 12h ago)" |
| "long lower wick" | "Sell-side sweep at 94,100 with 187 wick, closed 23 above sweep level" |
| "looks like an OB up there" | "Bearish OB at 81,092-81,329, next displacement 3.47× ATR, untested" |

Use these precise numbers in your reply — they're the core value-add.

## Constraints

1. **No fabrication** (shared rule) — every price you cite must appear in the feature summary
2. **Cite the knowledge base** — every confirmed pattern references a retrieved card
3. **Language** (shared rule) — Chinese prose / English technical terms
4. **State the data source explicitly** — tell the user whether you used API data or parsed data
5. **If parse failed** — tell the user the format issue and ask for one of: CSV with header / JSON / Markdown table
6. **API failure handling** — if fetch returns error, tell the user and ask if they want to paste data manually instead

## Examples

### Example 1 — Pure asset name

User: "BTC 1h 现在怎么样"

Steps:
1. `kb_klines.py fetch --query "BTC" --interval 1h --limit 200 --with-htf --output /tmp/btc.json`
2. `kb_klines.py analyze --input /tmp/btc.json --output /tmp/btc_features.txt`
3. Read `/tmp/btc_features.txt`
4. Retrieve relevant concepts (e.g. `kb_retrieve.py "liquidity sweep FVG market structure"`)
5. Output 5-section reply with **exact** prices from feature summary

### Example 2 — Pasted CSV

User: "我有一段 ETH 5m 的数据：
```
time,open,high,low,close,volume
2026-05-17 10:00,2240,2245,2235,2241,1234
...
```
帮我分析一下"

Steps:
1. Save the pasted text to `/tmp/eth_paste.csv`
2. `kb_klines.py parse --input /tmp/eth_paste.csv --symbol ETHUSDT --interval 5m --output /tmp/eth.json`
3. `kb_klines.py analyze --input /tmp/eth.json --output /tmp/eth_features.txt`
4. Read features + retrieve + 5-section output
5. **NOTE**: user-pasted data has no HTF fetched (since asset may be from any source); state this and offer to fetch HTF from Mobius if applicable

### Example 3 — Stock

User: "茅台日线最近怎么样"

Steps:
1. `kb_klines.py fetch --query "茅台" --interval 1d --limit 100 --with-htf` → may return 600519 (stock:cn)
2. `--with-htf` for daily → no HTF (1d is top), skip
3. Continue as Example 1

### Example 4 — Parse failed

User: "数据：[some malformed text]"

If parser returns "无法识别格式":
- You (the LLM) extract structure: "I see these are OHLC values for ETH. Let me convert..."
- Build a JSON object array yourself: `[{"time": ..., "open": ..., ...}]`
- Pipe via stdin: `echo '<json>' | kb_klines.py parse --symbol ETH --interval 5m --output ...`
- Continue as Example 2

## Tool reference

```bash
# Resolve natural name only
kb_klines.py resolve "比特币"

# Fetch with HTF
kb_klines.py fetch --query "BTC" --interval 1h --with-htf --output /tmp/x.json

# Fetch with canonical symbol
kb_klines.py fetch --exchange binance --market perp --symbol BTCUSDT --interval 1h ...

# Parse pasted text
kb_klines.py parse --input <file> --symbol <s> --interval <tf> --output <json>
echo '<text>' | kb_klines.py parse --symbol <s> --interval <tf>

# Analyze (extract features)
kb_klines.py analyze --input <json> --output <features.txt>
```

All paths are **relative to the skill directory**. Always `cd "${SKILL_DIR}"` before running commands so that `scripts/` and `.venv/` resolve correctly.
