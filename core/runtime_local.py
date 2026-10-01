# -*- coding: utf-8 -*-
"""内置本地运行环境：随包 Ollama 运行时 + 随包模型目录 + Laya 离线快照。

打包后的 onedir 目录布局（与 zhutoujunshi.spec 的 Tree 目标一致）：
    <exe 目录>/
      runtime/ollama/ollama.exe, lib/ollama/*     # 随包 Ollama 运行时（CPU + cuda_v12）
      models/ollama/{manifests,blobs,metadata}    # 随包 qwen2.5:7b（Ollama 模型目录）
      models/laya/multilingual/*                  # Laya 中文 checkpoint 快照（本地目录）

源码模式（IDE 里直接 Run）：以上目录若恰好存在同样生效；不存在则退回旧行为——
Ollama 用 127.0.0.1:11434 的假设、Laya 走 HuggingFace 下载。

行为约定（deep integration 的核心）：
  - 先探测 127.0.0.1:11434 上是否已有可用的 Ollama 且带 qwen2.5:7b（用户自己装的也算），
    有就直接复用，不占额外端口、不重复占内存；
  - 没有就拉起随包 ollama serve：OLLAMA_MODELS 指到随包模型目录，端口从 11434 起找空闲，
    等 /api/tags 里出现 qwen2.5:7b 才算就绪；
  - 只清理自己拉起的进程，绝不碰用户自己的 Ollama；
  - Laya 快照存在就用本地路径加载，完全离线；不存在才回退 HuggingFace。
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request

_MODEL = "qwen2.5:7b"
_DEFAULT_PORT = 11434
_START_TIMEOUT = 120.0  # 内置模型目录是现成的，serve 冷启动一般几秒；给足余量

_lock = threading.Lock()
_owned: subprocess.Popen | None = None   # 我们自己拉起的 serve 进程
_ready_base: str | None = None           # 确定可用的 Ollama 根地址（http://127.0.0.1:<port>）
_ready = False


def _app_root() -> str:
    """打包后 = 数据目录：PyInstaller 6.x 的 onedir 把 datas 全放 contents 目录（默认
    _internal），sys._MEIPASS 正好指向它，runtime/ 和 models/ 都跟它同根；
    源码 = 项目根目录（跟 app/settings.py 同一套规则）。"""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def app_root() -> str:
    """程序根目录：打包后 = _MEIPASS（onedir 的 _internal），源码 = 项目根。

    要读随包文件的地方（军师知识库之类）用它拼路径，别各自去猜 sys._MEIPASS。"""
    return _app_root()


def ollama_exe() -> str | None:
    """随包 ollama.exe；没有（源码模式且未放运行时）返回 None。"""
    p = os.path.join(_app_root(), "runtime", "ollama", "ollama.exe")
    return p if os.path.isfile(p) else None


def ollama_models_dir() -> str | None:
    """随包 Ollama 模型目录（含 manifests/blobs）；返回 None 表示没带模型。"""
    p = os.path.join(_app_root(), "models", "ollama")
    return p if os.path.isdir(os.path.join(p, "manifests")) else None


def laya_model_dir() -> str | None:
    """随包 Laya multilingual 快照目录；返回 None 表示没带，走 HuggingFace。"""
    p = os.path.join(_app_root(), "models", "laya", "multilingual")
    return p if os.path.isfile(os.path.join(p, "rl_agent_config.json")) else None


def _http_json(url: str, timeout: float = 3.0):
    """GET 一个 JSON 端点；任何失败返回 None（探测阶段不容忍异常）。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "zhutou-junshi"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def _has_model(port: int) -> bool:
    """这个端口的 Ollama 是否已经有 qwen2.5:7b（名字精确匹配）。"""
    data = _http_json(f"http://127.0.0.1:{port}/api/tags")
    if not data:
        return False
    for m in data.get("models", []):
        name = str(m.get("name") or "")
        if name == _MODEL or name.startswith(_MODEL + ":"):
            return True
    return False


def _port_free(port: int) -> bool:
    """端口上没人监听（TCP connect 被拒/超时 = 空）。"""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return False
    except OSError:
        return True


def _pick_port() -> int:
    """从默认端口起找第一个空闲端口；最多找 10 个。"""
    for port in range(_DEFAULT_PORT, _DEFAULT_PORT + 10):
        if _port_free(port):
            return port
    raise RuntimeError("本地端口 11434-11443 都被占用，无法启动内置模型引擎")


def _wait_ready(port: int, timeout: float) -> bool:
    """等 ollama serve 把 qwen2.5:7b 列出来。模型目录在包里，一次启动就绪。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _has_model(port):
            return True
        time.sleep(1.0)
    return False


def _spawn(port: int) -> subprocess.Popen:
    """拉起随包 ollama serve。OLLAMA_MODELS 指向随包模型目录；不设 OLLAMA_HOST 就绑 127.0.0.1。"""
    exe = ollama_exe()
    if exe is None:
        raise RuntimeError("未找到随包 Ollama 运行时（runtime/ollama/ollama.exe）")
    env = dict(os.environ)
    env["OLLAMA_MODELS"] = ollama_models_dir()  # 全内置模式下一定有；None 也不至于崩
    env["OLLAMA_HOST"] = f"127.0.0.1:{port}"  # 必须带端口，光写 127.0.0.1 会解析失败
    env.setdefault("OLLAMA_NOPRUNE", "1")
    flags = 0
    if sys.platform == "win32":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # GUI 程序别闪黑框
    return subprocess.Popen(
        [exe, "serve"], env=env, creationflags=flags,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def ensure_ollama(timeout: float = _START_TIMEOUT) -> str | None:
    """确保有一个带着 qwen2.5:7b 的本地 Ollama，返回它的根地址（无协议尾斜杠）。

    已就绪就直接返回；探测到系统 Ollama 可用就复用；否则拉起随包 serve。
    失败返回 None（调用方给出用户可读的提示）。线程安全，幂等。
    """
    global _ready, _ready_base, _owned
    if _ready:
        return _ready_base
    with _lock:
        if _ready:
            return _ready_base
        # 1) 复用：默认端口上已经有带模型的 Ollama（用户自己装的也算）
        if _has_model(_DEFAULT_PORT):
            _ready_base = f"http://127.0.0.1:{_DEFAULT_PORT}"
            _ready = True
            return _ready_base
        # 2) 拉起随包 serve：模型目录和运行时都在才值得试
        if ollama_exe() is None or ollama_models_dir() is None:
            return None
        try:
            port = _pick_port()
        except RuntimeError:
            return None
        try:
            _owned = _spawn(port)
        except OSError:
            _owned = None
            return None
        if _wait_ready(port, timeout):
            _ready_base = f"http://127.0.0.1:{port}"
            _ready = True
            return _ready_base
        shutdown()  # 起不来就清理掉，别留半死不活的进程
        return None


def ollama_v1_base() -> str:
    """起草来源为「本地 Ollama」时用的 OpenAI 兼容地址；没就绪也回默认端口，
    让报错信息指向真实位置而不是空串。"""
    if _ready and _ready_base:
        return _ready_base + "/v1"
    return f"http://127.0.0.1:{_DEFAULT_PORT}/v1"


def shutdown() -> None:
    """只收我们自己拉起的 serve；用户自己的 Ollama 绝不碰。幂等。"""
    global _owned, _ready, _ready_base
    with _lock:
        p, _owned = _owned, None
        _ready, _ready_base = False, None
    if p is not None and p.poll() is None:
        try:
            p.terminate()
            p.wait(timeout=5)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass


if __name__ == "__main__":
    # 离线自检：不联网、不起进程，只验路径解析和端口探测逻辑。
    assert _app_root()  # 非空即可
    # 端口探测：11434 在本机大概率被占（用户装过 Ollama），_port_free 不会抛
    _port_free(_DEFAULT_PORT)
    # 随包路径：源码模式下不存在 → None 是合法状态
    ollama_exe(), ollama_models_dir(), laya_model_dir()
    assert ollama_v1_base() == f"http://127.0.0.1:{_DEFAULT_PORT}/v1"
    print("runtime_local paths ok")
