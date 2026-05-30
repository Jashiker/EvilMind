"""统一 LLM 客户端 — DeepSeek API (OpenAI 兼容格式)

支持:
- 普通 chat / chat_json
- function calling (tool_calls) + 自动工具执行循环
"""

from __future__ import annotations

import json
import logging
import asyncio
from typing import Any, Callable, Awaitable

import httpx

from config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """DeepSeek LLM API 客户端"""

    def __init__(self):
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.request_timeout, connect=10.0),
        )

    async def close(self):
        await self._http.aclose()

    async def _raw_chat(self, payload: dict) -> dict:
        """底层 API 调用"""
        base_url = settings.deepseek_base_url
        headers = settings.api_headers

        last_error = None
        for attempt in range(settings.max_retries + 1):
            try:
                resp = await self._http.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                body = e.response.text[:200] if e.response else ""
                logger.warning(f"LLM HTTP {e.response.status_code} (attempt {attempt+1}): {body}")
                last_error = e
                if attempt < settings.max_retries:
                    await asyncio.sleep(1.5 ** attempt)
            except (httpx.RequestError, KeyError) as e:
                logger.warning(f"LLM 异常 (attempt {attempt+1}): {e}")
                last_error = e
                if attempt < settings.max_retries:
                    await asyncio.sleep(1.5 ** attempt)

        raise RuntimeError(f"LLM 调用失败（已重试 {settings.max_retries} 次）: {last_error}")

    async def chat(
        self,
        prompt: str,
        system: str = "",
        model: str | None = None,
        json_mode: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """普通 chat，返回助手回复文本"""
        model = model or settings.primary_model
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature if temperature is not None else settings.temperature,
            "max_tokens": max_tokens or settings.max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        data = await self._raw_chat(payload)
        return data["choices"][0]["message"]["content"]

    async def chat_json(
        self,
        prompt: str,
        system: str = "",
        model: str | None = None,
    ) -> dict:
        """chat 并解析 JSON 输出

        先尝试 json_mode（response_format），
        如果失败则降级为普通模式手动解析。
        """
        system_suffix = "\n\n你必须以合法的 JSON 格式输出结果，不要包含任何其他文字。"
        full_system = system + system_suffix

        # 尝试1: json_mode
        for attempt in range(2):
            try:
                raw = await self.chat(
                    prompt=prompt,
                    system=full_system,
                    model=model,
                    json_mode=(attempt == 0),
                    temperature=0.1,
                )
                text = raw.strip()
                if not text:
                    continue

                # 去掉 markdown 代码块标记
                if text.startswith("```"):
                    lines = text.split("\n")
                    text = "\n".join(lines[1:-1])

                # 尝试直接解析
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    pass

                # 尝试提取 {...}
                start, end = text.find("{"), text.rfind("}") + 1
                if start >= 0 and end > start:
                    try:
                        return json.loads(text[start:end])
                    except json.JSONDecodeError:
                        pass

                if attempt == 0:
                    logger.info("json_mode 返回非 JSON，降级普通模式重试")

            except Exception as e:
                if attempt == 0:
                    logger.warning(f"json_mode 失败: {e}，降级普通模式重试")
                else:
                    raise

        logger.error(f"LLM 输出无法解析为 JSON: {raw[:200] if raw else '(empty)'}")
        raise ValueError("LLM 输出无法解析为 JSON")

    async def chat_with_tools(
        self,
        prompt: str,
        system: str = "",
        tools: list[dict] | None = None,
        tool_executor: Callable[[str, dict], Awaitable[str]] | None = None,
        max_rounds: int = 5,
        model: str | None = None,
    ) -> str:
        """带工具调用的 chat — Agent 自主决定是否搜索"""
        model = model or settings.primary_model
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        for round_idx in range(max_rounds):
            payload: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": settings.temperature,
                "max_tokens": settings.max_tokens,
            }
            if tools:
                payload["tools"] = tools

            data = await self._raw_chat(payload)
            choice = data["choices"][0]
            msg = choice["message"]

            # 如果模型没有调用工具，直接返回内容
            if not msg.get("tool_calls"):
                content = msg.get("content", "")
                if content:
                    return content
                # 空内容，再试一次
                if round_idx < max_rounds - 1:
                    continue
                return "模型未返回有效内容"

            # 有工具调用 → 执行工具
            messages.append(msg)

            for tc in msg["tool_calls"]:
                fn = tc["function"]
                tool_name = fn["name"]
                try:
                    tool_args = json.loads(fn["arguments"]) if isinstance(fn["arguments"], str) else fn["arguments"]
                except json.JSONDecodeError:
                    tool_args = {}

                logger.info(f"[Tool] {tool_name}({json.dumps(tool_args, ensure_ascii=False)[:100]})")

                if tool_executor:
                    result = await tool_executor(tool_name, tool_args)
                else:
                    result = f"工具 {tool_name} 未注册"

                logger.info(f"[Tool Result] {tool_name}: {str(result)[:80]}...")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": str(result),
                })

            # 工具执行完后移除工具，强制下一轮输出文本
            tools = None

        logger.warning(f"工具调用达到最大轮次 {max_rounds}")
        return "搜索已完成但无法整理结果，请基于已有知识给出最佳判断。"

    async def ocr_image(
        self,
        image_base64: str,
        mime_type: str = "image/png",
        prompt: str = "",
        model: str | None = None,
    ) -> str:
        """使用多模态 LLM 提取图片中的文字信息

        Args:
            image_base64: 图片的 base64 编码（不含 data:xxx;base64, 前缀）
            mime_type: 图片 MIME 类型
            prompt: 额外的提取指令
            model: 模型名（默认用 vision_model）

        Returns:
            提取的文字内容
        """
        from config import settings

        model = model or settings.vision_model
        base_url = settings.vision_base_url or settings.deepseek_base_url
        api_key = settings.vision_api_key or settings.deepseek_api_key

        user_prompt = prompt or "请仔细提取这张图片中的所有文字信息，包括标题、正文、数字、日期等。保持原文的格式和顺序。如果是聊天截图，请标注每句话是谁说的。如果是文章截图，请保留标题和段落结构。只输出提取的文字，不要添加额外解说。"

        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}},
            ],
        }]

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": settings.max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = await self._http.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            logger.info(f"[OCR] 提取文字 {len(content)} 字符")
            return content
        except Exception as e:
            logger.error(f"[OCR] 视觉模型调用失败: {e}")
            raise RuntimeError(f"图片文字提取失败: {e}")
