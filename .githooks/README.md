# Git hooks (fork-only workflow)

Tracked hooks for this fork. Enable after clone:

```powershell
git config core.hooksPath .githooks
```

Or run [`scripts/setup_fork.ps1`](../scripts/setup_fork.ps1).

**pre-push** — rejects pushes to `upstream` or MobiusQuant URLs. Always push to `origin` (Ripper612 fork).
