# -*- coding: utf-8 -*-
"""E2E-1: 用随包 Ollama 运行时 + 随包 qwen2.5:7b 模型目录，真实起草一条回复。

不依赖本机已装的 Ollama：强制走 _spawn 分支，挑一个空闲端口（11434 通常被系统
Ollama 占着），OLLAMA_MODELS 指向随包 models/ollama。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import runtime_local  # noqa: E402

# 1) 随包路径全部解析到
assert os.path.isfile(runtime_local.ollama_exe()), runtime_local.ollama_exe()
assert os.path.isdir(os.path.join(runtime_local.ollama_models_dir(), "manifests"))
assert os.path.isfile(os.path.join(runtime_local.laya_model_dir(), "rl_agent_config.json"))
print("paths ok")

# 2) 拉起随包 serve（强制走内置运行时分支）
port = runtime_local._pick_port()
print(f"spawn bundled ollama serve on {port} ...")
proc = runtime_local._spawn(port)
try:
    ok = runtime_local._wait_ready(port, timeout=120)
    print("serve ready:", ok)
    assert ok, "随包 ollama serve 未就绪"
    # 3) OpenAI 兼容端点真实起草
    from core.llm import chat

    text = chat(
        "openai", f"http://127.0.0.1:{port}/v1", "ollama-local", "qwen2.5:7b",
        "你是一个简洁的助手，只回一两句话。",
        ["夸我一句，十个字以内"],
        temperature=0.5, max_tokens=80,
    )
    print("draft ok:", text.strip()[:120])
    assert text.strip(), "起草返回空"
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
print("E2E-1 PASS")
