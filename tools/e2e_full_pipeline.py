# -*- coding: utf-8 -*-
"""E2E-3: 整条流水线 = 默认配置（本地 Laya 判断 + 本地 Ollama 起草 + 军师模式）。

这就是用户双击 exe 后真实发生的事：runtime_local.ensure_ollama() 决定用哪个本地
Ollama（系统在跑且有模型就用系统的，否则拉起随包 serve），engine.analyze 依次跑
Laya → 军师推演 → 3 条候选。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import runtime_local  # noqa: E402
from core.engine import analyze  # noqa: E402

base = runtime_local.ensure_ollama()
assert base, "本地模型引擎未就绪"
print("engine base:", base)

msgs = [("her", "周六想吃火锅，你有空吗？"), ("me", "有空呀，还是上次那家？"),
        ("her", "好呀！六点见怎么样？我好久没吃了")]
r = analyze(msgs, "friends", context=10, provider="ollama", jev_provider="local",
            junshi=True)
print("analyze ok, top:", r["candidates"][0][:60])
assert r.get("candidates"), "没有候选回复"
assert len(r["candidates"]) == 3, r["candidates"]
print("E2E-3 PASS")
