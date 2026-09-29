# -*- coding: utf-8 -*-
from openai import OpenAI
c = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

print("=== 英文测试 ===")
r = c.chat.completions.create(
    model="qwen2.5:7b",
    messages=[{"role":"user","content":"What is 1+1? Answer in one short sentence."}],
    temperature=0.3, max_tokens=80)
print(repr(r.choices[0].message.content))

print("\n=== ollama show 模板信息 ===")
import subprocess
out = subprocess.run([r"C:\Users\Pankey\AppData\Local\Programs\Ollama\ollama.exe", "show", "qwen2.5:7b"],
                     capture_output=True, text=True, encoding="utf-8", errors="replace")
print(out.stdout[:2000])
print("STDERR:", out.stderr[:500])
