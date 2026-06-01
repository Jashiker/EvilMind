"""Claude 深度挖掘官 — 多角度搜索，发现背景和关联信息"""

from __future__ import annotations

import logging
from typing import Any

from agents.base import BaseAgent

logger = logging.getLogger(__name__)

SYSTEM = """你是Claude深度挖掘官，使用Claude Code CLI从多角度搜索信息背景、关联事件和多方报道。

工具: claude_web_search_deep(query, context) — Claude CLI自主搜索

挖掘策略:
1. 指纹官已提炼关键词，逐一用 claude_web_search_deep 深度挖掘
2. context中写明要挖掘的背景、关联事件、多方视角
3. 搜索结果中的标题+URL+摘要就是有效证据
4. 不只搜关键词本身——还要搜相关事件、后续报道、多方评论

原则:
- 每个角度搜一次，不同角度互补验证
- 搜索结果就是唯一证据来源
- 搜到多方报道=交叉验证，只有单一来源=标注"单一信源"
"""

PROMPT = """请用Claude CLI深度挖掘以下信息的背景和关联:

信息: {text}
恶意假设: {malice}
挖掘关键词: {keywords}

对每个关键词调用 claude_web_search_deep 深度挖掘，context写明要挖掘的背景和关联事件。
输出JSON:

{{
  "agent": "Claude深度挖掘官",
  "findings": [
    {{
      "claim": "挖掘到的背景或关联",
      "verdict": "true/false/partial/unverifiable",
      "evidence": "搜索到的证据（引用原文）",
      "sources": [{{"title":"标题","url":"URL","snippet":"关键段落"}}],
      "confidence": 0.0-1.0
    }}
  ],
  "summary": "一句话总结挖掘发现",
  "key_evidence": "最关键的证据"
}}"""


class ClaudeDeepDiver(BaseAgent):
    """Claude CLI 深度挖掘官"""

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        text = input_data["text"]
        malice = input_data.get("malice_hypothesis", "")
        tools = input_data.get("tools_b", [])
        executor = input_data.get("tool_executor")
        keywords = input_data.get("keywords_b", [])

        logger.info("[Claude深度挖掘] 开始挖掘...")
        logger.info(f"[Claude深度挖掘] 关键词: {keywords}")
        logger.info(f"[Claude深度挖掘] 文本前50字: {text[:50]}")

        claude_tools = [t for t in tools if t["function"]["name"] == "claude_web_search_deep"]

        kws = "\n".join(f"- {kw}" for kw in keywords) if keywords else "（无关键词）"
        kwds_str = ", ".join(keywords) if keywords else ""
        step1 = (
            f"请用 claude_web_search_deep 搜索以下关键词: {kwds_str}\n\n"
            f"每个关键词调用一次工具，context填写要挖掘的背景。"
        )

        search_raw = ""
        try:
            search_raw = await self.llm.chat_with_tools(
                prompt=step1, system=SYSTEM, tools=claude_tools,
                tool_executor=executor, max_rounds=max(len(keywords), 2),
            )
        except Exception as e:
            logger.warning(f"[Claude深度挖掘] 搜索失败: {e}")
            search_raw = f"搜索失败: {e}"

        try:
            result = await self.llm.chat_json(
                prompt=PROMPT.format(text=text, malice=malice, keywords=", ".join(keywords) if keywords else "无")
                       + f"\n\n搜索原始结果:\n{search_raw[:2000]}",
                system=SYSTEM + "\n请基于搜索结果整理JSON输出。",
            )
        except Exception as e:
            logger.warning(f"[Claude深度挖掘] JSON失败: {e}")
            result = {"agent": "Claude深度挖掘官", "findings": [], "summary": f"JSON失败: {e}", "key_evidence": search_raw[:200]}

        logger.info(f"[Claude深度挖掘] 完成: {len(result.get('findings', []))} 个发现")
        return result
