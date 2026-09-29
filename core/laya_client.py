# -*- coding: utf-8 -*-
"""Laya 本地判断：替代 Jev（OpenRouter/TypeSafe）做意图判断和排序，完全离线、零 API 成本。

模型：convaiinnovations/laya，multilingual checkpoint（唯一吃中文的）。
权重 ~1.4GB，首次 predict 时从 HuggingFace 下载并缓存。
接口形状和 jev_client.ask 完全一致：{"answers": {名字: 答案}, "usage": {...}}，
engine 不关心跑的是云端 Jev 还是本地 Laya。

参考 probe/probe_laya.py。
"""
from __future__ import annotations

import threading

from .jev_client import JevError  # 复用异常类型

_agent = None
_lock = threading.Lock()


def _load():
    """懒加载单例：第一次调用才加载模型，之后复用。加载要几秒到十几秒。"""
    global _agent
    if _agent is not None:
        return _agent
    with _lock:
        if _agent is not None:
            return _agent
        try:
            import laya
        except ImportError as e:
            raise JevError("未安装 laya 包：pip install laya") from e
        try:
            # multilingual = 唯一吃中文的 checkpoint；typed-decisions 是英文做过题的
            _agent = laya.load("convaiinnovations/laya", subfolder="multilingual")
        except Exception as e:
            raise JevError(f"Laya 模型加载失败（首次需下载 ~1.4GB 权重）: {e}") from e
        return _agent


def _normalize_answer(ans) -> dict:
    """laya 返回的答案对象 → 和 jev_client._answer 一样的 dict 形状。"""
    if isinstance(ans, dict):
        t = ans.get("type") or ("noul" if "noul" in ans else "score" if "score" in ans else "choice")
        if t == "noul":
            return {"type": "noul", "noul": float(ans.get("noul", 0))}
        if t == "score":
            return {"type": "score", "score": float(ans.get("score", 0)),
                    "confidence": float(ans.get("confidence", 0)),
                    "probabilities": {str(k): float(v) for k, v in (ans.get("probabilities") or {}).items()}}
        return {"type": "choice", "choice": str(ans.get("choice", "")),
                "confidence": float(ans.get("confidence", 0)),
                "probabilities": {k: float(v) for k, v in (ans.get("probabilities") or {}).items()}}
    # 对象属性形式
    t = getattr(ans, "type", None) or ("noul" if hasattr(ans, "noul") else
                                       "score" if hasattr(ans, "score") else "choice")
    if t == "noul":
        return {"type": "noul", "noul": float(getattr(ans, "noul", 0))}
    if t == "score":
        probs = getattr(ans, "probabilities", {}) or {}
        return {"type": "score", "score": float(getattr(ans, "score", 0)),
                "confidence": float(getattr(ans, "confidence", 0)),
                "probabilities": {str(k): float(v) for k, v in probs.items()}}
    probs = getattr(ans, "probabilities", {}) or {}
    return {"type": "choice", "choice": str(getattr(ans, "choice", "")),
            "confidence": float(getattr(ans, "confidence", 0)),
            "probabilities": {k: float(v) for k, v in probs.items()}}


def ask_laya(state: dict, questions: dict, timeout: float = 60, **_kw) -> dict:
    """问本地 Laya 一轮判断。参数和 jev_client.ask 对齐（timeout/kw 忽略，离线快）。"""
    agent = _load()
    try:
        result = agent.predict(state, questions)
    except Exception as e:
        raise JevError(f"Laya 本地判断失败: {e}") from e
    raw_answers = result.get("answers") if isinstance(result, dict) else getattr(result, "answers", {})
    answers = {name: _normalize_answer(a) for name, a in raw_answers.items()}
    usage = result.get("usage", {}) if isinstance(result, dict) else {}
    return {"answers": answers, "usage": usage or {}}


if __name__ == "__main__":
    # 离线自检：不加载真模型，只验 _normalize_answer 的字典/对象两种形状。
    fake = {"answers": {
        "literal_question": {"type": "noul", "noul": 0.9},
        "danger_level": {"type": "score", "score": 4.0, "confidence": 0.7, "probabilities": {4: 0.7, 5: 0.3}},
        "best_reply": {"type": "choice", "choice": "reply_b", "confidence": 0.6,
                       "probabilities": {"reply_a": 0.3, "reply_b": 0.6, "reply_c": 0.1}},
    }}
    out = ask_laya({"chat": {}}, {"q": {}}, ) if False else None  # 不真加载
    # 直接验归一化
    a = _normalize_answer(fake["answers"]["danger_level"])
    assert a["score"] == 4.0 and a["probabilities"]["4"] == 0.7
    b = _normalize_answer(fake["answers"]["best_reply"])
    assert b["choice"] == "reply_b" and b["probabilities"]["reply_b"] == 0.6
    print("laya_client normalize ok")
