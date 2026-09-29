# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.junshi import _parse_junshi

# 截图里那段实际输出（JSON 不合法，括号不匹配，边界回复是 "2"）
bad = r'{"analysis":"她可能在测试你是否真的在聊天，避免被机器人重复对话。","risk":"如果对方只是在测试，直接回复可能会显得过于明确，导致她感觉到你并不在意。","replies":[{"label":"稳健","text":"好的，我再确认一下。"},{"label":"策略","text":"最近没收到你的消息，可能是因为我在忙其他事。"},{"label":"边界","text":"2"(}}]}'

cands, meta = _parse_junshi(bad)
print("=== 解析结果 ===")
print("analysis:", meta["analysis"][:80])
print("labels:", meta["labels"])
for i, c in enumerate(cands):
    print(f"  [{i+1}] {c}")
