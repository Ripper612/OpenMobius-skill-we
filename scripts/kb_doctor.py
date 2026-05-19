#!/usr/bin/env python3
"""kb-doctor：一次性环境体检。

跑一次，定位 kb-qna / kb-analyze-chart / kb-annotate-chart 三个 Skill 运行常见问题：
- Python 虚拟环境 + 包
- nomic 嵌入模型本地缓存
- 知识库向量索引
- CJK 字体（中文 label 渲染必需）
- Skill 安装位置（~/.claude/skills/...）

每项失败都附修复命令。
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Optional


SKILL_DIR = Path(__file__).resolve().parent.parent

# 颜色（不支持 TTY 时降级为空字符串）
_USE_COLOR = sys.stdout.isatty()
GREEN = "\033[32m" if _USE_COLOR else ""
RED = "\033[31m" if _USE_COLOR else ""
YELLOW = "\033[33m" if _USE_COLOR else ""
DIM = "\033[2m" if _USE_COLOR else ""
RESET = "\033[0m" if _USE_COLOR else ""


def _ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def _fail(msg: str, fix: Optional[str] = None) -> None:
    print(f"  {RED}✗{RESET} {msg}")
    if fix:
        for line in fix.strip().splitlines():
            print(f"    {YELLOW}↳{RESET} {line}")


def _warn(msg: str, fix: Optional[str] = None) -> None:
    print(f"  {YELLOW}⚠{RESET} {msg}")
    if fix:
        for line in fix.strip().splitlines():
            print(f"    {DIM}↳{RESET} {line}")


def _section(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


# ============================================================================
# Checks
# ============================================================================

def check_env_python() -> bool:
    _section("Python 虚拟环境")
    # 同时认 .venv（标准）/ .env（旧）
    for sub in (".venv", ".env"):
        env_py = SKILL_DIR / sub / "bin" / "python"
        if env_py.is_file():
            _ok(f"虚拟环境 python 存在: {env_py}")
            return True
    _fail(
        f"找不到 .venv/bin/python in {SKILL_DIR}",
        f"cd {SKILL_DIR}\n"
        f"bash install.sh        # 一键安装 (推荐)\n"
        f"# 或手动:\n"
        f"python3 -m venv .venv && .venv/bin/pip install -r requirements.txt",
    )
    return False


def check_python_packages() -> bool:
    _section("Python 包")
    packages = [
        ("chromadb",                "pip install chromadb",                          True),
        ("sentence_transformers",   "pip install sentence-transformers",             True),
        ("PIL",                     "pip install Pillow",                            True),
        ("numpy",                   "pip install numpy",                             True),
        ("playwright",              "pip install playwright && playwright install chromium", True),
        ("openai",                  "pip install openai  (可选：远程 embedding 时需要)", False),
    ]
    all_ok = True
    for name, install_cmd, required in packages:
        try:
            mod = importlib.import_module(name)
            version = getattr(mod, "__version__", "?")
            _ok(f"{name} {version}")
        except ImportError:
            if required:
                _fail(f"{name} 未安装", install_cmd)
                all_ok = False
            else:
                _warn(f"{name} 未安装（可选）", install_cmd)
    return all_ok


def check_embedding_model() -> bool:
    _section("Embedding 模型 (nomic-embed-text-v1.5)")
    hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
    model_dir = hf_cache / "models--nomic-ai--nomic-embed-text-v1.5"
    if model_dir.is_dir():
        snapshots = list((model_dir / "snapshots").glob("*"))
        if snapshots:
            # 检查 snapshot 里是否真的有权重文件
            snap = snapshots[0]
            weight_files = list(snap.glob("*.safetensors")) + list(snap.glob("pytorch_model.bin"))
            if weight_files:
                size_mb = sum(f.stat().st_size for f in weight_files) / 1024 / 1024
                _ok(f"已下载 ({size_mb:.0f} MB): {snap}")
                return True
            _warn(
                f"模型目录存在但权重文件缺失: {snap}",
                "重新触发下载：跑 python scripts/kb_retrieve.py 'test'",
            )
            return False
    _fail(
        "nomic-embed-text-v1.5 未下载（首次会下 ~274MB）",
        "首次跑 build_index.py 或 kb_retrieve.py 会自动下载\n"
        "或手动预热: .venv/bin/python -c \"from sentence_transformers import "
        "SentenceTransformer; SentenceTransformer('nomic-ai/nomic-embed-text-v1.5', trust_remote_code=True)\"",
    )
    return False


def check_kb_index() -> bool:
    _section("知识库向量索引")
    index_path = SKILL_DIR / "knowledge_base" / "_index" / "chroma.sqlite3"
    if index_path.is_file():
        size_mb = index_path.stat().st_size / 1024 / 1024
        _ok(f"索引存在 ({size_mb:.1f} MB): {index_path.relative_to(SKILL_DIR)}")
        return True
    _fail(
        f"索引不存在: {index_path.relative_to(SKILL_DIR)}",
        f"cd {SKILL_DIR}\n"
        f".venv/bin/python scripts/build_index.py",
    )
    return False


def check_playwright_chromium() -> bool:
    _section("Playwright Chromium (图表渲染)")
    import os as _os  # noqa: PLC0415
    cache = Path(_os.environ.get("PLAYWRIGHT_BROWSERS_PATH",
                                  Path.home() / ".cache" / "ms-playwright"))
    if not cache.is_dir():
        _fail(
            f"{cache} 不存在",
            ".venv/bin/playwright install chromium  (~280MB)",
        )
        return False
    candidates = list(cache.glob("chromium-*")) + list(cache.glob("chromium_headless_shell-*"))
    if not candidates:
        _fail(
            "Chromium 未在缓存中找到",
            ".venv/bin/playwright install chromium  (~280MB)",
        )
        return False
    sizes = [(c.name, sum(f.stat().st_size for f in c.rglob("*") if f.is_file())) for c in candidates]
    total = sum(s for _, s in sizes) / 1024 / 1024
    _ok(f"Chromium 已安装 ({len(candidates)} bundle, {total:.0f} MB total)")
    return True


def check_cjk_fonts() -> bool:
    _section("CJK 字体 (中文标注图必需)")
    # 与 kb_draw_annotation.py 保持一致
    cjk_fonts = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/opentype/source-han-sans/SourceHanSansSC-Regular.otf",
        "C:\\Windows\\Fonts\\msyh.ttc",
        "C:\\Windows\\Fonts\\simhei.ttf",
    ]
    found = [p for p in cjk_fonts if Path(p).is_file()]
    if found:
        _ok(f"已安装 {len(found)} 个 CJK 字体:")
        for p in found:
            print(f"      - {p}")
        return True
    if sys.platform == "linux":
        fix = (
            "Debian/Ubuntu: sudo apt install fonts-noto-cjk\n"
            "Fedora/RHEL:   sudo dnf install google-noto-cjk-fonts\n"
            "Arch:          sudo pacman -S noto-fonts-cjk"
        )
    elif sys.platform == "darwin":
        fix = "macOS 通常自带 PingFang.ttc — 请检查 /System/Library/Fonts/"
    elif sys.platform == "win32":
        fix = "Windows 通常自带 msyh.ttc — 请检查 C:\\Windows\\Fonts\\"
    else:
        fix = "请安装任意 Noto Sans CJK / 文泉驿 / PingFang / SimHei 字体"
    _fail("未找到 CJK 字体（中文 label 会渲染为方块 口口口）", fix)
    return False


def check_skill_install() -> bool:
    _section("Skill 安装")
    skills = ["OpenMobius-skill"]
    base = Path.home() / ".claude" / "skills"
    if not base.is_dir():
        _warn(
            f"{base} 不存在（如果不用 ~/.claude/skills 部署可忽略）",
            f"mkdir -p {base}",
        )
        return True
    all_ok = True
    for name in skills:
        p = base / name
        if p.is_symlink():
            target = p.resolve()
            _ok(f"{name} → {target}")
        elif p.exists():
            _ok(f"{name} (directory)")
        else:
            _fail(
                f"{name} 未安装到 {base}",
                f"ln -sf {SKILL_DIR} {base}/{name}",
            )
            all_ok = False
    return all_ok


def check_local_claude_endpoint() -> bool:
    _section("local-claude endpoint (可选)")
    import socket  # noqa: PLC0415
    host, port = "172.16.0.203", 8080
    try:
        with socket.create_connection((host, port), timeout=2):
            _ok(f"可达: http://{host}:{port}")
            return True
    except Exception as e:  # noqa: BLE001
        _warn(
            f"http://{host}:{port} 不可达 ({e.__class__.__name__})",
            "如果你只用 OpenRouter / API key 模式，可忽略此项",
        )
        return True  # 不算 fail


def check_mobius_api() -> bool:
    """Mobius Quant API connectivity check (public endpoint, no auth)."""
    _section("Mobius Quant API (for live market data and chart generation)")
    import os as _os  # noqa: PLC0415
    import urllib.error  # noqa: PLC0415
    import urllib.request  # noqa: PLC0415

    base = _os.environ.get("MOBIUS_API_BASE", "https://api.mobiusquant.ai")

    req = urllib.request.Request(
        f"{base}/api/health",
        headers={
            "User-Agent": "MobiusSkills-Doctor/0.1",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            import json as _json  # noqa: PLC0415
            data = _json.loads(resp.read().decode("utf-8"))
            status = data.get("status", "unknown")
            totals = data.get("totals", {})
            _ok(
                f"API reachable: {base} (status={status}, "
                f"venues={totals.get('venues', '?')}, "
                f"streams={totals.get('streams', '?')})",
            )
    except urllib.error.HTTPError as e:
        _fail(
            f"API HTTP {e.code}: {base}",
            "Check network or override MOBIUS_API_BASE",
        )
        return False
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        _fail(
            f"API unreachable: {base} ({e.__class__.__name__}: {e})",
            "Ignore if you don't need live market data; otherwise check network / proxy",
        )
        return False
    return True


# ============================================================================
# Main
# ============================================================================

def main() -> int:
    print(f"{DIM}{'=' * 64}{RESET}")
    print(f"  OpenMobius-skill 环境体检 (kb-doctor)")
    print(f"{DIM}{'=' * 64}{RESET}")
    print(f"  Skill: {SKILL_DIR}")
    print(f"  Python: {sys.version.split()[0]} ({sys.executable})")
    print(f"  Platform: {sys.platform}")

    results = {
        "Python 虚拟环境":      check_env_python(),
        "Python 包":           check_python_packages(),
        "Embedding 模型":      check_embedding_model(),
        "知识库索引":           check_kb_index(),
        "Playwright Chromium": check_playwright_chromium(),
        "CJK 字体":            check_cjk_fonts(),
        "Skill 安装":          check_skill_install(),
        "local-claude":       check_local_claude_endpoint(),
        "Mobius API":         check_mobius_api(),
    }

    # 关键项（决定 exit code）— local-claude / Mobius 都是可选
    critical = {k: v for k, v in results.items()
                if k not in ("local-claude", "Mobius API")}

    print(f"\n{DIM}{'=' * 64}{RESET}")
    print("  Summary")
    print(f"{DIM}{'=' * 64}{RESET}")
    passed = sum(1 for v in critical.values() if v)
    total = len(critical)
    for name, ok_ in results.items():
        mark = f"{GREEN}✓{RESET}" if ok_ else f"{RED}✗{RESET}"
        print(f"  {mark} {name}")
    print()
    if passed == total:
        print(f"{GREEN}✓ All critical checks passed ({passed}/{total}){RESET}")
        return 0
    print(f"{YELLOW}⚠ {passed}/{total} critical checks passed — see ↳ fixes above{RESET}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
