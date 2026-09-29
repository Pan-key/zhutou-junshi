# -*- coding: utf-8 -*-
import time
from openai import OpenAI

c = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

print("=== 测试1: 中文短回复 ===")
t0 = time.time()
r = c.chat.completions.create(
    model="qwen2.5:7b",
    messages=[{"role": "user", "content": "用一句话回答：1+1等于几？"}],
    temperature=0.3, max_tokens=100)
print(f"耗时{time.time()-t0:.1f}s, 回复: {r.choices[0].message.content}")

print("\n=== 测试2: 模拟聊天回复场景 ===")
t0 = time.time()
r = c.chat.completions.create(
    model="qwen2.5:7b",
    messages=[
        {"role": "system", "content": "你是用户本人，在微信里打字。只回复一句话。"},
        {"role": "user", "content": "对方说：你是不是又忘了我跟你说过的事\n你回什么？只输出一句话，不要解释。"}],
    temperature=0.8, max_tokens=100)
print(f"耗时{time.time()-t0:.1f}s, 回复: {r.choices[0].message.content}")
