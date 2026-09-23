# -*- coding: utf-8 -*-
"""
大模型调用模块 —— 统一封装多家模型服务商。

设计要点：
    1. 所有服务商都走 OpenAI 兼容协议，因此只需要一个 HTTP 客户端；
    2. 未配置任何 API Key 时自动降级为「演示模式」（mock），
       保证任何人 clone 下来无需 Key 就能跑通全流程；
    3. 超时、返回格式异常等错误统一转成 LLMError，由上层决定如何回退。
"""

import json
import os
import re
from typing import Any, Dict, Optional

import httpx

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # 未安装 python-dotenv 时也能运行
    pass

LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))


class LLMError(Exception):
    """调用大模型失败。"""


# 各服务商的默认接入地址与模型
PROVIDER_CONFIG = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "env_key": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
    },
    "dashscope": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "env_key": "DASHSCOPE_API_KEY",
        "default_model": "qwen-plus",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-4o-mini",
    },
    "ollama": {
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        "env_key": "OLLAMA_API_KEY",  # 本地模型随便填一个非空值即可
        "default_model": "qwen2.5:7b",
    },
}


def get_provider() -> str:
    """
    决定当前使用哪个服务商。

    优先读取 LLM_PROVIDER；若未设置，则按 Key 是否配置自动推断；
    全都没有则返回 mock（演示模式）。
    """
    explicit = os.getenv("LLM_PROVIDER", "").strip().lower()
    if explicit:
        if explicit == "mock":
            return "mock"
        cfg = PROVIDER_CONFIG.get(explicit)
        if cfg and os.getenv(cfg["env_key"]):
            return explicit
        # 指定了服务商但没有 Key，退回演示模式
        return "mock"

    for name, cfg in PROVIDER_CONFIG.items():
        if name == "ollama":
            continue
        if os.getenv(cfg["env_key"]):
            return name
    return "mock"


def is_mock_mode() -> bool:
    return get_provider() == "mock"


def chat(system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
    """
    调用大模型并返回纯文本结果。

    参数：
        system_prompt: 系统提示词，用于约束模型行为
        user_prompt:   用户提示词
        temperature:   温度，生成 SQL 时建议 0，保证稳定性
    """
    provider = get_provider()
    if provider == "mock":
        raise LLMError("当前处于演示模式，未调用真实大模型。")

    cfg = PROVIDER_CONFIG[provider]
    api_key = os.getenv(cfg["env_key"], "")
    model = os.getenv("%s_MODEL" % provider.upper(), cfg["default_model"])

    if not api_key:
        raise LLMError("未配置 %s，无法调用大模型。" % cfg["env_key"])

    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }

    try:
        with httpx.Client(timeout=LLM_TIMEOUT) as client:
            resp = client.post(
                "%s/chat/completions" % cfg["base_url"],
                headers={
                    "Authorization": "Bearer %s" % api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        raise LLMError("调用大模型超时，请稍后重试或检查网络。")
    except httpx.HTTPStatusError as exc:
        raise LLMError("大模型返回错误状态码：%s" % exc.response.status_code)
    except Exception as exc:
        raise LLMError("调用大模型失败：%s" % exc)

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise LLMError("大模型返回结构异常，无法解析。")


def extract_json(text: str) -> Optional[dict]:
    """
    从模型输出中提取 JSON 对象。

    模型经常把 JSON 包在 markdown 代码块里，这里做容错处理。
    """
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
    cleaned = re.sub(r"```\s*$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 退而求其次：抓取第一个 { 到最后一个 } 之间的内容
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None
