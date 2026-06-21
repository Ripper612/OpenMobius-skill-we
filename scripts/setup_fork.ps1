# One-shot fork-only git setup for Ripper612/OpenMobius-skill-we.
# Run from repo root after clone.

$ErrorActionPreference = "Stop"

$ForkOrigin = "https://github.com/Ripper612/OpenMobius-skill-we.git"
$UpstreamFetch = "https://github.com/MobiusQuant/OpenMobius-skill.git"

Write-Host "OpenMobius fork setup (push to origin only)" -ForegroundColor Cyan

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

if (-not (Test-Path ".git")) {
    throw "Not a git repository: $root"
}

# origin
$originUrl = (git remote get-url origin 2>$null)
if ($LASTEXITCODE -ne 0) {
    git remote add origin $ForkOrigin
    Write-Host "  + added origin -> $ForkOrigin"
} elseif ($originUrl -ne $ForkOrigin) {
    Write-Host "  ! origin is $originUrl (expected $ForkOrigin)" -ForegroundColor Yellow
} else {
    Write-Host "  ok origin -> $ForkOrigin"
}

# upstream (fetch only)
$upstreamUrl = (git remote get-url upstream 2>$null)
if ($LASTEXITCODE -ne 0) {
    git remote add upstream $UpstreamFetch
    Write-Host "  + added upstream -> $UpstreamFetch"
} else {
    Write-Host "  ok upstream fetch -> $upstreamUrl"
}
git remote set-url --push upstream no_push

# push defaults
git config branch.main.pushRemote origin
git config remote.pushDefault origin
git config push.default current

# tracked hooks
if (Test-Path ".githooks/pre-push") {
    git config core.hooksPath .githooks
    Write-Host "  ok core.hooksPath -> .githooks"
} else {
    Write-Host "  ! missing .githooks/pre-push" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Verification:" -ForegroundColor Cyan
git remote -v
Write-Host ""
git config --local --get-regexp "branch.main.pushremote|remote.pushdefault|push.default|core.hookspath"
Write-Host ""
Write-Host "Done. Push with: git push origin main" -ForegroundColor Green
Write-Host "See FORK.md — do NOT use GitHub's Contribute button (opens PR to MobiusQuant)." -ForegroundColor Yellow
