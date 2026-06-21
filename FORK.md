# Fork workflow (Ripper612 only)

This repository is a **personal fork** of [MobiusQuant/OpenMobius-skill](https://github.com/MobiusQuant/OpenMobius-skill). All changes are pushed to **your fork only**. Do not open pull requests to the upstream project unless you explicitly intend to contribute there.

## First-time clone setup

After cloning, run once:

```powershell
cd d:\local_code\skills-projects\OpenMobius-skill-we
.\scripts\setup_fork.ps1
```

This configures fetch-only `upstream`, push defaults to `origin`, and enables the pre-push hook.

## Safe daily workflow

```powershell
git pull origin main
# edit files
git add .
git commit -m "your message"
git push origin main

# redeploy to agent install dirs
uv run python install.py --update --no-pull --platform claude-code
uv run python install.py --update --no-pull --platform codex
uv run python install.py --update --no-pull --platform claude-code --target-dir "$env:USERPROFILE\.cursor\skills\OpenMobius-skill"
```

Use `git push` without arguments on `main` — it pushes to `origin` by default.

## Syncing MobiusQuant updates (optional)

`upstream` is **fetch-only**. You can merge upstream changes locally, then push to your fork:

```powershell
git fetch upstream
git merge upstream/main
# resolve conflicts, test
git push origin main
```

Never `git push upstream` — it is blocked by remote config and the pre-push hook.

## Never do this

| Action | Why |
|---|---|
| GitHub fork page → **Contribute** → Open pull request | Opens a PR to **MobiusQuant**, the parent repo |
| `git push upstream` | Blocked; targets upstream |
| `gh pr create` without `--repo Ripper612/OpenMobius-skill-we` | May target the wrong repository |

## Pull requests on your own fork

If you use feature branches and want a PR into your fork's `main`:

```powershell
gh pr create --repo Ripper612/OpenMobius-skill-we --base main --head your-branch
```

Most solo work skips PRs entirely: commit on `main` and `git push origin main`.

## Remotes

| Remote | URL | Push |
|---|---|---|
| `origin` | `https://github.com/Ripper612/OpenMobius-skill-we.git` | Yes (default) |
| `upstream` | `https://github.com/MobiusQuant/OpenMobius-skill.git` | **No** (fetch only) |

Verify:

```powershell
git remote -v
```

## Installer note

`install.py --update` (without `--no-pull`) clones from **this fork** (`REPO_URL` in `install.py`). For local edits, prefer `--update --no-pull` after `git pull origin main`.
