# -*- coding: utf-8 -*-
"""端到端测试：Laya 本地判断 + qwen2.5:7b 本地军师起草"""
import sys, os, time, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.engine import analyze

# 模拟一段情侣吵架场景
messages = [
    ("her", "你是不是又忘了我跟你说过的事？"),
    ("me", "啊？什么事"),
    ("her", "就上周我跟你说我妈要来吃饭，你说要提前订位的"),
]

print("=" * 60)
print("场景：女友怪你忘了订位")
print("对方消息:", messages[-1][1])
print("=" * 60)

t0 = time.time()
result = analyze(
    messages=messages,
    relationship="romantic partners",
    provider="custom_openai",
    base_url="http://localhost:11434/v1",
    model="qwen2.5:7b",
    jev_provider="local",
    jev_model="laya-multilingual",
    junshi=True,
    timeout=120,
    context=10,
    style="",
)
elapsed = time.time() - t0

print(f"\n总耗时: {elapsed:.1f}s")
print(f"\n--- Jev/Laya 判断 ---")
for k, v in result.get("answers", {}).items():
    print(f"  {k}: {v}")

print(f"\n--- 军师分析 ---")
jm = result.get("junshi", {})
print(f"  analysis: {jm.get('analysis', '')[:200]}")
print(f"  risk: {jm.get('risk', '')[:200]}")
print(f"  labels: {jm.get('labels', [])}")

print(f"\n--- {len(result['candidates'])} 条候选回复 ---")
for i, c in enumerate(result["candidates"]):
    label = jm.get("labels", ["", "", ""])[i] if i < len(jm.get("labels", [])) else ""
    print(f"\n[{i+1}] {label}")
    print(f"    {c.get('text', c) if isinstance(c, dict) else c}")

print(f"\n--- 最佳推荐 ---")
bi = result.get("best_index", 0)
print(f"  第 {bi+1} 条: {result['candidates'][bi]}")
