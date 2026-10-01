# -*- coding: utf-8 -*-
"""E2E-2: Laya 从随包快照离线加载并做一轮真实判断（不联网）。

验证 core/laya_client 的 bundled 分支：laya.load(本地目录) → predict。
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import runtime_local  # noqa: E402
from core.laya_client import ask_laya  # noqa: E402
from core.questions import JUDGE_QUESTIONS, build_rank_question, build_state  # noqa: E402

# 随包快照路径可解析
d = runtime_local.laya_model_dir()
assert d and os.path.isfile(os.path.join(d, "rl_agent_config.json")), d
print("bundled laya dir ok:", d)

msgs = [("her", "你到底来不来"), ("me", "我这边还有点事"),
        ("her", "算了，你别来了，我自己去。以后也别问我了")]
cands = ["我马上出发，二十分钟到", "那你自己注意安全", "行吧随你"]
questions = dict(JUDGE_QUESTIONS)
questions.update(build_rank_question(cands))

t0 = time.perf_counter()
out = ask_laya(build_state(msgs, "romantic partners"), questions)
dt = time.perf_counter() - t0
print(f"predict ok in {dt:.1f}s, {len(out['answers'])} answers")
names = {q: a.get("choice") or a.get("score") for q, a in out["answers"].items()}
print("sample answers:", {k: names[k] for k in list(names)[:4]})
assert out["answers"], "Laya 没返回任何答案"
print("E2E-2 PASS")
