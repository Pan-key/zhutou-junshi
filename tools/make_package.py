# -*- coding: utf-8 -*-
"""组装全内置离线包的素材：runtime/（Ollama 运行时）+ models/（qwen2.5:7b + Laya 快照）。

用法（在项目根目录，用装了依赖的 venv 跑）：
    python tools/make_package.py

做三件事：
  1. runtime/ollama/  从本机已安装的 Ollama 复制 ollama.exe + lib/ollama：
                      CPU 全套 + cuda_v12（NVIDIA 加速）；跳过 cuda_v13 / rocm / vulkan
                      省约 1.6GB——需要的用户自行替换成自己装的完整版。
  2. models/ollama/   从 ~/.ollama/models（或 $OLLAMA_MODELS）复制整个模型目录，
                      里面就是 qwen2.5:7b 的 manifests + blobs。
  3. models/laya/     把 Laya multilingual 子目录（唯一吃中文的 checkpoint）就位：
                      优先拷贝本机 HuggingFace 缓存，没有就联网下载，落成普通本地目录，
                      运行时零网络加载。

已存在的文件跳过（可断点续跑）；最后打印各目录大小。产物都被 .gitignore 排除，不进仓库。
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / "runtime" / "ollama"
MODELS_OLLAMA = ROOT / "models" / "ollama"
MODELS_LAYA = ROOT / "models" / "laya"

# cuda_v13 要更新的驱动，rocm/vulkan 受众更窄：默认只带 cuda_v12，够覆盖绝大多数 N 卡
_GPU_SKIP = {"cuda_v13", "rocm_v7_1", "vulkan"}


def _fmt(n: int) -> str:
    return f"{n / 1e9:.2f} GB" if n >= 1e9 else f"{n / 1e6:.1f} MB"


def _dir_size(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def _copy_tree(src: Path, dst: Path, skip_dirs: set[str] = frozenset()) -> int:
    """复制目录树；目标已存在且大小一致的文件跳过；skip_dirs 里的子目录整体跳过。
    返回复制的文件数。"""
    n = 0
    for item in src.rglob("*"):
        rel = item.relative_to(src)
        if any(part in skip_dirs for part in rel.parts):
            continue  # 父目录被跳过时，它的子项（目录和文件）也整条挡住
        if item.is_dir():
            (dst / rel).mkdir(parents=True, exist_ok=True)
            continue
        target = dst / rel
        if target.is_file() and target.stat().st_size == item.stat().st_size:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        n += 1
    return n


def _find_ollama_install() -> Path | None:
    """常见的 Ollama 安装位置；返回含 ollama.exe 的目录或 None。"""
    base = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
    candidates = [
        Path(base) / "Programs" / "Ollama",
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Ollama",
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Ollama",
    ]
    for c in candidates:
        if (c / "ollama.exe").is_file():
            return c
    return None


def _step_runtime(force: bool = False) -> None:
    src = _find_ollama_install()
    if src is None:
        print("!! 没找到本机 Ollama 安装。请先装 Ollama 并 ollama pull qwen2.5:7b，"
              "再跑本脚本；或手动把 ollama.exe + lib/ollama 放到 runtime/ollama/。")
        sys.exit(1)
    print(f"== 1/3 复制 Ollama 运行时 ← {src}")
    n = _copy_tree(src / "lib" / "ollama", RUNTIME / "lib" / "ollama",
                   skip_dirs=_GPU_SKIP)
    exe = src / "ollama.exe"
    target = RUNTIME / "ollama.exe"
    if not (target.is_file() and target.stat().st_size == exe.stat().st_size):
        shutil.copy2(exe, target)
        n += 1
    print(f"   runtime/ollama: {n} 个文件, {_fmt(_dir_size(RUNTIME))}")


def _step_ollama_models(force: bool = False) -> None:
    src = Path(os.environ.get("OLLAMA_MODELS") or Path.home() / ".ollama" / "models")
    if not (src / "manifests").is_dir():
        print(f"!! 没找到 Ollama 模型目录（{src}）。先装 Ollama 并 ollama pull qwen2.5:7b。")
        sys.exit(1)
    print(f"== 2/3 复制 qwen2.5:7b 模型目录 ← {src}")
    n = _copy_tree(src, MODELS_OLLAMA)
    print(f"   models/ollama: {n} 个文件, {_fmt(_dir_size(MODELS_OLLAMA))}")


def _laya_cache_dir() -> Path | None:
    """本机 HuggingFace 缓存里现成的 multilingual 快照（有就不用联网下载）。"""
    hub = (Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub")
    for snap in (hub / "models--convaiinnovations--laya" / "snapshots").glob("*"):
        if (snap / "multilingual" / "rl_agent_config.json").is_file():
            return snap / "multilingual"
    return None


def _step_laya(force: bool = False) -> None:
    """multilingual 快照就位：优先拷贝本机 HF 缓存（离线可用），否则联网下载。"""
    if (MODELS_LAYA / "multilingual" / "rl_agent_config.json").is_file():
        print(f"== 3/3 Laya 快照已存在，跳过（{_fmt(_dir_size(MODELS_LAYA))}）")
        return
    cache = _laya_cache_dir()
    if cache is not None:
        print(f"== 3/3 从本机 HF 缓存复制 Laya multilingual ← {cache}")
        _copy_tree(cache, MODELS_LAYA / "multilingual")
        print(f"   models/laya: {_fmt(_dir_size(MODELS_LAYA))}")
        return
    print("== 3/3 下载 Laya multilingual 快照（约 0.7GB）→ models/laya")
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("!! 缺少 huggingface_hub。先装依赖：pip install -r requirements.txt")
        sys.exit(1)
    snapshot_download(
        "convaiinnovations/laya",
        local_dir=str(MODELS_LAYA),
        allow_patterns=["multilingual/*"],
    )
    print(f"   models/laya: {_fmt(_dir_size(MODELS_LAYA))}")


def main() -> None:
    ap = argparse.ArgumentParser(description="组装全内置离线包素材")
    ap.add_argument("--force", action="store_true", help="强制重下 Laya（默认已存在则跳过）")
    args = ap.parse_args()
    _step_runtime(args.force)
    _step_ollama_models(args.force)
    _step_laya(args.force)
    total = _dir_size(ROOT / "runtime") + _dir_size(ROOT / "models")
    print(f"\n完成。runtime + models 共 {_fmt(total)}。"
          f"\n接着运行 build.bat 打包含它们在内的完整发布包。")


if __name__ == "__main__":
    main()
