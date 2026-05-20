# Agent Install Guide for OpenMobius-skill

This file is written for **AI agents** (Claude Code / Codex / OpenClaw /
Hermes / etc.) that the user has asked to install OpenMobius-skill on
their machine. Read it end-to-end before executing, then run the steps
in order. **Do not skip steps.**

If you are a human, see [`README.md`](./README.md) and
[`INSTALL.md`](./INSTALL.md) instead — they're optimised for human
readers.

---

## Trigger phrases

Run the procedure below when the user says any of (case-insensitive,
free-form, both languages):

**中文**

- 帮我装 OpenMobius / 帮我装 mobius / 帮我装 mobius-skill
- 帮我装这个交易 skill / 装一下 ICT skill
- 安装 OpenMobius-skill / 安装 mobius 交易知识

**English**

- install OpenMobius / install OpenMobius-skill
- install the mobius trading skill / install ICT skill
- set up OpenMobius-skill on this machine
- add the mobius market-analysis skill

If the user clearly intends to install but uses different wording,
also proceed.

---

## Step 1 — Pre-flight checks

Verify the prerequisites are present:

```bash
python3 --version 2>&1 || echo "MISSING: python3"
git --version    2>&1 || echo "MISSING: git"
```

**Success criterion**

- `python3 --version` reports `Python 3.10` or higher (3.10 / 3.11 / 3.12 /
  3.13 / 3.14 all OK).
- `git --version` reports any version.

**Failure handling**

| Symptom | Action |
|---|---|
| `python3: command not found` | Tell user: install Python 3.10+ from <https://www.python.org/downloads/> or via their package manager. Halt — do not proceed until user confirms install. |
| Python version < 3.10 | Tell user: upgrade Python to 3.10 or newer. Halt. |
| `git: command not found` | Tell user: install git. macOS: `xcode-select --install`; Linux: `sudo apt install git` / `sudo dnf install git`. Halt. |

---

## Step 2 — Choose the target agent platform

If you (the agent) already know which platform you're running on (e.g.
you're Claude Code → use `claude-code`), use it directly.

Otherwise, detect installed platforms:

```bash
for d in ~/.claude ~/.codex ~/.openclaw ~/.hermes; do
    [ -d "$d" ] && echo "found: $d"
done
```

- **0 found** → ask user which agent they're using.
- **1 found** → use it.
- **2+ found** → ask user which one to install into (or offer
  `--platform all`).

Map the user's answer to a flag:

| Agent | `--platform` flag | Install target dir |
|---|---|---|
| Claude Code | `claude-code` | `~/.claude/skills/OpenMobius-skill/` |
| Codex | `codex` | `~/.codex/skills/OpenMobius-skill/` |
| OpenClaw | `openclaw` | `~/.openclaw/skills/OpenMobius-skill/` |
| Hermes | `hermes` | `~/.hermes/skills/market-data/OpenMobius-skill/` |
| All four | `all` | each of the above |

Save the chosen flag as `<FLAG>` for the next steps.

---

## Step 3 — Tell the user what's about to happen

Before triggering the install, surface this to the user (in their
language, but the bullets must include the time and size numbers
verbatim):

> "Installing OpenMobius-skill to `<INSTALL_TARGET>`. This will take
> roughly 5–10 minutes on first run (downloads ~280 MB Playwright
> chromium and ~274 MB nomic embedding model). After install the
> clone in `/tmp` is deleted automatically — your agent skills dir
> becomes the self-contained install."

Wait for user confirmation (Y/proceed/继续/好) before running Step 4.

---

## Step 4 — Run the installer

```bash
git clone --depth 1 https://github.com/MobiusQuant/OpenMobius-skill /tmp/openmobius-install
cd /tmp/openmobius-install
python3 install.py --platform <FLAG>
```

**Monitor `stdout`** for these milestones (in order):

1. `[1/9] Checking Python ≥ 3.10` (or `Python version`)
2. `Virtual env`
3. `Python dependencies`
4. `Playwright chromium`
5. `CJK fonts`
6. `Embedding model`
7. `Vector index`
8. `Skill registration` (or `Wrote .../SKILL.md`)
9. `Doctor`

The final summary should show `✓` on every line.

**Success criterion**

- `install.py` exits with code 0.
- Final summary shows `✓ Installation complete`.

**Failure handling**

| Symptom in stdout | Likely cause | Action |
|---|---|---|
| `ensurepip is not available` | Debian/Ubuntu missing `python3-venv` | Tell user: `sudo apt install python3.X-venv` (use detected X), then re-run Step 4. |
| `playwright install chromium` fails mid-download | Network or disk | Tell user: check disk space + network; optionally set `PLAYWRIGHT_BROWSERS_PATH` to a writable dir; re-run Step 4. |
| `SentenceTransformer` / `nomic-embed-text` download fails | HuggingFace.co network | Tell user: try later, or set `HF_HUB_OFFLINE=0` and `HF_ENDPOINT` to a mirror. |
| `[load] X cards have missing / stale embeddings` | KB shipped without embeddings | Re-run with `python3 scripts/build_index.py --regenerate --force` (slow). This is unexpected — report as bug if it happens on a fresh clone. |
| Index OOM on low-RAM machine | <2 GB free | Tell user: free RAM, or use `--no-prebuilt` (removed in latest version — alternative: switch to OpenAI embedder via `OPENAI_API_KEY`). |
| Any other unexpected exit code | — | Re-run with `python3 install.py --platform <FLAG> --strict -v` to surface the real error, then report to the user. |

---

## Step 5 — Cleanup the temporary clone

After Step 4 succeeds:

```bash
rm -rf /tmp/openmobius-install
```

The install target dir (`~/.<platform>/skills/OpenMobius-skill/`) is
self-contained — the `/tmp` clone is not referenced anywhere going
forward and safely removable.

---

## Step 6 — Verify the install

```bash
~/.<PLATFORM_DIR>/skills/OpenMobius-skill/.venv/bin/python \
    ~/.<PLATFORM_DIR>/skills/OpenMobius-skill/scripts/kb_doctor.py
```

Substitute `<PLATFORM_DIR>` per the user's platform:

| Platform | Path prefix |
|---|---|
| Claude Code | `~/.claude/skills/OpenMobius-skill/` |
| Codex | `~/.codex/skills/OpenMobius-skill/` |
| OpenClaw | `~/.openclaw/skills/OpenMobius-skill/` |
| Hermes | `~/.hermes/skills/market-data/OpenMobius-skill/` |

**Success criterion**

- All check items report ✓, except possibly `Mobius API` (optional;
  network may be down — non-fatal).

**Failure handling**

| Doctor item | Action |
|---|---|
| `Python 虚拟环境` ✗ | The venv was not created correctly. Re-run Step 4 with `--no-resume`. |
| `Python 包` ✗ | Some pip install failed. Re-run Step 4 with `--strict -v` to see which. |
| `Embedding 模型` ✗ | nomic model didn't reach cache. Re-run Step 4 — Playwright/model steps are idempotent. |
| `知识库索引` ✗ | Vector index didn't build. Run `<target>/.venv/bin/python <target>/scripts/build_index.py --force` manually. |
| `Skill 安装` ✗ | The SKILL.md was not written. Re-run Step 4 — SKILL.md generation is idempotent. |
| `Mobius API` ✗ | Non-fatal. Skill still works for concept Q&A and pasted-data analysis. |

---

## Step 7 — Report back to the user

Tell the user (in their language) the following, including the
specific items in **bold**:

1. **Skill installed** to `<EXACT INSTALL TARGET PATH>`.
2. The skill auto-activates for these question types:
   - ICT/SMC concept questions ("什么是 FVG", "how to identify OB")
   - Chart-image analysis (user attaches a trading chart)
   - Asset+timeframe queries ("BTC 1h 怎么样", "茅台日线分析")
   - Image annotation requests
3. **Restart your agent CLI** so the skill is loaded.
4. After restart, the user can try:
   - "What is Liquidity Sweep?"
   - "ETH 4h 现在怎么样"

Example user-facing message (English):

> ✓ OpenMobius-skill installed to `~/.codex/skills/OpenMobius-skill/`.
> The skill auto-activates on ICT/SMC trading questions, chart
> analysis, asset+timeframe queries, and image annotation. **Restart
> your Codex CLI** for the skill to be loaded — then try asking
> "What is Fair Value Gap?" or "ETH 1h 怎么样".

---

## Things you (the agent) should NOT do

- **Do not** edit or patch `install.py` to bypass errors. If a step
  fails, report it to the user and ask for guidance.
- **Do not** skip the doctor check (Step 6). It's the only way to know
  the install actually works.
- **Do not** re-install if the target dir already contains a working
  install. Use `python3 install.py --update --platform <FLAG>` instead.
- **Do not** install on an unsupported environment (iOS, web-only
  agents). Tell the user it requires a local Python 3.10+ runtime.
- **Do not** install user-global caches (chromium / nomic model) to
  unusual locations unless the user explicitly requested via
  `PLAYWRIGHT_BROWSERS_PATH` or `HF_HOME`.

---

## If the user asks to uninstall

```bash
cd /tmp
git clone --depth 1 https://github.com/MobiusQuant/OpenMobius-skill /tmp/openmobius-tmp
python3 /tmp/openmobius-tmp/install.py --uninstall --platform <FLAG>
rm -rf /tmp/openmobius-tmp
```

For a complete uninstall including the shared user-global caches
(chromium ~280 MB, nomic ~274 MB — note other tools may share these):

```bash
python3 /tmp/openmobius-tmp/install.py --uninstall --platform <FLAG> --purge --yes-i-know
```

---

## If the user asks to update

```bash
# Update one platform (currently installed):
python3 ~/.<PLATFORM_DIR>/skills/OpenMobius-skill/install.py --update --platform <FLAG>
```

This will:
1. Clone the latest upstream code to a fresh `/tmp` dir.
2. Re-copy source files into the install target (overwrites).
3. Re-run install steps in resume mode (skips already-done work).
4. Regenerate `SKILL.md`.
5. Clean up the `/tmp` clone.

---

## Repository URL (for fetching this file fresh)

```
https://raw.githubusercontent.com/MobiusQuant/OpenMobius-skill/main/README_AGENT.md
```

The agent may `WebFetch` this URL at the start of the install
procedure to ensure it's working from the latest instructions.
