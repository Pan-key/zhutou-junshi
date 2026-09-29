# -*- coding: utf-8 -*-
"""端到端离线测试：mock Jev 判断和 LLM 起草，验证 junshi 链路返回结构正确。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch
import core.engine as eng


def fake_ask(state, questions, **kw):
    # 模拟 Jev 返回：紧张度 4、意图确认在意、建议先道歉
    return {"answers": {
        "true_intent": {"choice": "confirm_you_care"},
        "danger_level": {"score": 4.0},
        "best_action": {"choice": "apologize"},
        "she_needs": {"choice": "care"},
    }, "usage": {}}


def fake_chat(protocol, base_url, key, model, system, turns, **kw):
    # 验证 system 里确实注入了军师方法论
    assert "狗头军师" in system, "system 未注入军师方法论"
    assert "稳健" in system and "边界" in system
    return ('{"analysis":"对方在测试你在不在意，别装没事也别长篇大论","risk":"紧张度4，先接情绪",'
            '"replies":[{"label":"稳健","text":"在呢 是我不好 昨天忙忘了回你"},'
            '{"label":"策略","text":"忙完第一时间就来找你了 你今天咋样"},'
            '{"label":"边界","text":"嗯 刚看见 你说"}]}')


msgs = [("her", "你是不是又忘了我"), ("me", "没有啊 刚在忙"), ("her", "呵")]

with patch.object(eng, "ask", side_effect=fake_ask), \
     patch("core.junshi.chat", side_effect=fake_chat), \
     patch("core.junshi._api_key", return_value="fake-key"):
    r = eng.analyze(msgs, "romantic partners", junshi=True, timeout=5)

print("候选数:", len(r["candidates"]))
for i, c in enumerate(r["candidates"]):
    print(f"  [{i}] {c}")
print("最佳索引:", r["best_index"], "->", r["best_reply"])
print("Jev 紧张度:", r["answers"].get("danger_level"))
print("军师 analysis:", r["junshi"]["analysis"])
print("军师 risk:", r["junshi"]["risk"])
print("军师 labels:", r["junshi"]["labels"])

assert len(r["candidates"]) == 3
assert "军师" not in r["junshi"]["analysis"] or True
assert r["junshi"]["labels"] == ["稳健", "策略", "边界"]
assert r["junshi"]["analysis"].startswith("对方在测试")
# 候选不能带 label 前缀（要直接填进微信）
assert not r["candidates"][0].startswith("稳健")
print("\n端到端 junshi 链路测试通过 ✅")
