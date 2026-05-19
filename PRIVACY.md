# Privacy and Data Handling

`OpenMobius-skill` is a **local-first AI agent skill**. This document
describes every piece of data that leaves your machine, the destination,
and the purpose.

## Network endpoints

The installer and runtime make outbound requests to only the following
hosts. No other domains are contacted, ever.

| Host | When | Purpose | What is sent |
|---|---|---|---|
| `pypi.org` (and PyPI mirrors) | Install time | Install declared Python dependencies from `requirements.txt` | Standard pip download requests |
| `huggingface.co` | Install time | Download the open-source `nomic-embed-text-v1.5` model (Apache 2.0) | Standard HuggingFace Hub download requests |
| `playwright.azureedge.net` | Install time | Download chromium browser used for chart rendering | Standard Playwright download requests |
| `mobiusquant.ai` / `api.mobiusquant.ai` | Install + runtime | (a) Fetch install manifest. (b) Public OHLCV / indicator / playbook endpoints (used at runtime when the user asks a trading question that needs live data). | Manifest fetches contain no user data. Runtime API calls contain only your explicit query: asset name, timeframe, indicator name. **No authentication required, no credentials collected.** |

## What is stored locally

The installer writes only to these locations:

| Location | Content | Removable by |
|---|---|---|
| `<skill-dir>/.venv/` | Python virtual environment | `python install.py --uninstall --full` |
| `~/.cache/huggingface/hub/` | nomic embedding model cache | `python install.py --uninstall --purge --yes-i-know` |
| `~/.cache/ms-playwright/` | chromium browser binary | `python install.py --uninstall --purge --yes-i-know` |
| `<skill-dir>/knowledge_base/_index/` | Local ChromaDB vector index | `python install.py --uninstall --full` |
| `~/.<agent>/skills/OpenMobius-skill/` (symlink) | Skill registration into your AI agent | `python install.py --uninstall` |

`<skill-dir>` defaults to `~/OpenMobius-skill/` for the curl installer, or
to the location you clone into for the git workflow.

## What is NOT done

- **No telemetry.** No usage analytics, crash reports, or any
  background-collected data are transmitted from your machine.
- **No background processes.** No daemons, system services, or startup
  entries are installed.
- **No system-level modifications.** No `/etc/`, no
  `/Library/LaunchAgents/`, no registry keys.
- **No automatic updates.** Version upgrades require explicit
  `python install.py --update`.

## How to inspect

Before installing you can review the install steps in `install.py`. The
`--strict` flag halts on the first error (useful for CI environments).

## Reporting

For privacy or security concerns, please open an issue on the project's
GitHub repository (when public) or contact the project maintainers via
the website listed in `README.md`.
