"""LLM客户端 — OpenAI SDK (DeepSeek-v4-pro)

使用OpenAI官方SDK, 自动管理上下文窗口。
每个API调用创建独立的messages列表, 天然隔离上下文。
"""

from __future__ import annotations
import json, logging
from typing import Any
from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger(__name__)

ANTI_HALLUCINATION = """\n\n记住：你使用的搜索工具返回的结果是唯一的信息来源。引用的数据和URL必须来自工具返回的真实结果。"""


class LLMClient:
    """DeepSeek API via OpenAI SDK"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=settings.request_timeout,
            max_retries=settings.max_retries,
        )

    async def chat(self, prompt: str, system: str = "", model: str = None,
                   json_mode: bool = False, temperature: float = None,
                   max_tokens: int = None) -> str:
        """普通对话 — 每次调用使用全新上下文"""
        model = model or settings.primary_model
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": model, "messages": messages,
            "temperature": temperature if temperature is not None else settings.temperature,
            "max_tokens": max_tokens or settings.max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        resp = await self.client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    async def chat_json(self, prompt: str, system: str = "", model: str = None) -> dict:
        """JSON对话 — 自动降级处理"""
        system_suffix = "\n\n你必须以合法的JSON格式输出结果。"
        full_system = (system + ANTI_HALLUCINATION + system_suffix) if system else system_suffix

        for attempt in range(2):
            try:
                raw = await self.chat(
                    prompt=prompt, system=full_system, model=model,
                    json_mode=(attempt == 0), temperature=0.1,
                )
                text = raw.strip()
                if not text:
                    continue
                # Strip stray function call tokens
                for tok in ['<function_calls>','</function_calls>','<invoke>','</invoke>',
                           '<parameter>','</parameter>','<tool_call>','</tool_call>']:
                    text = text.replace(tok, '')
                if not text or len(text) < 5:
                    continue
                # Strip markdown code fences
                if text.startswith("```"):
                    lines = text.split("\n")
                    text = "\n".join(lines[1:-1])
                # Try direct parse
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    pass
                # Try extract {...}
                start, end = text.find("{"), text.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(text[start:end])
                if attempt == 0:
                    logger.info("json_mode failed, retrying without json_mode")
            except Exception as e:
                if attempt == 0:
                    logger.warning(f"chat_json attempt {attempt}: {e}")
                else:
                    raise

        raise ValueError(f"LLM JSON parse failed: {raw[:200] if raw else '(empty)'}")

    async def chat_with_tools(self, prompt: str, system: str = "",
                               tools: list[dict] = None,
                               tool_executor=None, max_rounds: int = 2,
                               model: str = None) -> str:
        """带工具调用的对话 — 最多2轮工具调用"""
        model = model or settings.primary_model
        messages = []
        if system:
            messages.append({"role": "system", "content": system + ANTI_HALLUCINATION})
        else:
            messages.append({"role": "system", "content": ANTI_HALLUCINATION.strip()})
        # 用户prompt必须加入messages，否则模型不知道要搜什么
        messages.append({"role": "user", "content": prompt})

        for round_idx in range(max_rounds):
            kwargs: dict[str, Any] = {
                "model": model, "messages": messages,
                "temperature": settings.temperature,
                "max_tokens": settings.max_tokens,
            }
            if tools:
                kwargs["tools"] = tools

            resp = await self.client.chat.completions.create(**kwargs)
            msg = resp.choices[0].message

            # No tool calls → return text
            if not msg.tool_calls:
                return msg.content or ""

            # Execute tool calls
            messages.append(msg)
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                logger.info(f"[Tool] {name}({json.dumps(args, ensure_ascii=False)[:100]})")
                if tool_executor:
                    result = await tool_executor(name, args)
                else:
                    result = f"Tool {name} not registered"
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),
                })
            # Remove tools after first round to force text output
            tools = None

        logger.warning(f"Tool calls max rounds ({max_rounds}) reached")
        return "搜索已完成但未整理结果，请基于已有信息给出最佳判断。"
