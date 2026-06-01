"""Claude 事实核查官 — 精准验证信息中的具体事实点"""

from __future__ import annotations

import logging
from typing import Any

from agents.base import BaseAgent

logger = logging.getLogger(__name__)

SYSTEM = """你是Claude事实核查官，使用Claude Code CLI搜索引擎精准验证信息中的每一个事实主张。

工具: claude_web_search_deep(query, context) — Claude CLI自主搜索

核查策略:
1. 指纹官已提炼关键词，逐一用 claude_web_search_deep 精准核查
2. context中写明要验证的具体数字、日期、机构名、人物
3. 搜索结果中的标题+URL+摘要就是有效证据
4. 找到的数据必须与原始信息逐条对比

原则:
- 每个事实点用一组精准关键词搜一次
- 搜索结果就是唯一证据来源，不编造不推测
- 数据对得上=verified，对不上=fabricated，搜不到=unverifiable
- 不确定就标注"无法验证"
"""

PROMPT = """请用Claude CLI精准核查以下信息中的事实点:

信息: {text}
恶意假设: {malice}
核查关键词: {keywords}

对每个关键词调用 claude_web_search_deep 核查，context写明要验证的具体事实和数据。
对比搜索结果中的真实数据与原始信息，输出JSON:

{{
  "agent": "Claude事实核查官",
  "findings": [
    {{
      "claim": "核查的事实点",
      "verdict": "true/false/partial/unverifiable",
      "evidence": "搜索到的证据（引用原文数据）",
      "sources": [{{"title":"标题","url":"URL","snippet":"关键段落"}}],
      "confidence": 0.0-1.0
    }}
  ],
  "summary": "一句话总结核查发现",
  "key_evidence": "最关键的证据"
}}"""


class ClaudeFactChecker(BaseAgent):
    """Claude CLI 事实核查官"""

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        text = input_data["text"]
        malice = input_data.get("malice_hypothesis", "")
        tools = input_data.get("tools_a", [])
        executor = input_data.get("tool_executor")
        keywords = input_data.get("keywords_a", [])

        logger.info("[Claude事实核查] 开始核查...")
        logger.info(f"[Claude事实核查] 关键词: {keywords}")
        logger.info(f"[Claude事实核查] 文本前50字: {text[:50]}")

        claude_tools = [t for t in tools if t["function"]["name"] == "claude_web_search_deep"]

        kws = "\n".join(f"- {kw}" for kw in keywords) if keywords else "（无关键词）"
        kwds_str = ", ".join(keywords) if keywords else ""
        step1 = (
            f"请用 claude_web_search_deep 搜索以下关键词: {kwds_str}\n\n"
            f"每个关键词调用一次工具，context填写要验证的事实。"
        )

        search_raw = ""
        try:
            search_raw = await self.llm.chat_with_tools(
                prompt=step1, system=SYSTEM, tools=claude_tools,
                tool_executor=executor, max_rounds=max(len(keywords), 2),
            )
        except Exception as e:
            logger.warning(f"[Claude事实核查] 搜索失败: {e}")
            search_raw = f"搜索失败: {e}"

        try:
            result = await self.llm.chat_json(
                prompt=PROMPT.format(text=text, malice=malice, keywords=", ".join(keywords) if keywords else "无")
                       + f"\n\n搜索原始结果:\n{search_raw[:2000]}",
                system=SYSTEM + "\n请基于搜索结果整理JSON输出。",
            )
        except Exception as e:
            logger.warning(f"[Claude事实核查] JSON失败: {e}")
            result = {"agent": "Claude事实核查官", "findings": [], "summary": f"JSON失败: {e}", "key_evidence": search_raw[:200]}

        logger.info(f"[Claude事实核查] 完成: {len(result.get('findings', []))} 个发现")
        return result
