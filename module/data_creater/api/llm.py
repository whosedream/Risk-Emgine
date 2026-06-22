"""
LLM API 调用封装
"""

import json
import asyncio
import logging
from typing import Union

import httpx
from config.settings import ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN, MODEL

logger = logging.getLogger(__name__)


async def call_llm(prompt: str, system_prompt: str = "") -> str:
    """
    调用 Anthropic API 获取 LLM 响应
    """
    headers = {
        "x-api-key": ANTHROPIC_AUTH_TOKEN,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    messages = [{"role": "user", "content": prompt}]

    body = {
        "model": MODEL,
        "max_tokens": 4096,
        "messages": messages
    }

    if system_prompt:
        body["system"] = system_prompt

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ANTHROPIC_BASE_URL}/v1/messages",
            headers=headers,
            json=body,
            timeout=120.0
        )
        response.raise_for_status()
        data = response.json()

    return data["content"][0]["text"]


async def call_llm_json(prompt: str, system_prompt: str = "") -> dict:
    """
    调用 LLM 并解析 JSON 响应
    """
    response = await call_llm(prompt, system_prompt)

    # 尝试提取 JSON
    try:
        # 如果响应包含 ```json 代码块
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
        else:
            json_str = response.strip()

        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from LLM response: {e}\nResponse: {response}")


async def call_llm_with_retry(
    prompt: str,
    system_prompt: str = "",
    parse_json: bool = False,
    max_retries: int = 3,
    base_delay: float = 1.0,
    rate_limit_delay: float = 10.0
) -> Union[str, dict]:
    """
    带重试的 LLM 调用

    Args:
        parse_json: 如果为 True，调用 call_llm_json 并返回 dict
                   如果为 False，调用 call_llm 并返回 str
        max_retries: 重试次数（总共尝试 max_retries + 1 次）

    重试策略：
    - 网络超时、5xx 错误：指数退避重试（1s, 2s, 4s）
    - 429 速率限制：较长退避（10s, 20s, 40s）
    - 4xx 客户端错误：不重试，立即失败
    - JSON 解析失败（ValueError）：重试
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            if parse_json:
                return await call_llm_json(prompt, system_prompt)
            else:
                return await call_llm(prompt, system_prompt)

        except httpx.TimeoutException as e:
            last_exception = e
            logger.warning(f"LLM 调用超时 (attempt {attempt + 1}/{max_retries + 1}): {e}")

        except httpx.HTTPStatusError as e:
            last_exception = e
            if e.response.status_code == 429:
                delay = rate_limit_delay * (2 ** attempt)
                logger.warning(f"速率限制 (attempt {attempt + 1}), 等待 {delay}s")
                await asyncio.sleep(delay)
                continue
            elif e.response.status_code >= 500:
                logger.warning(f"服务器错误 {e.response.status_code} (attempt {attempt + 1}): {e}")
            else:
                raise

        except ValueError as e:
            last_exception = e
            logger.warning(f"JSON 解析失败 (attempt {attempt + 1}): {e}")

        except Exception as e:
            raise

        if attempt < max_retries:
            delay = base_delay * (2 ** attempt)
            await asyncio.sleep(delay)

    raise last_exception
