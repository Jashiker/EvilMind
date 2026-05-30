"""360搜索 Agent — 使用360搜索引擎进行溯源调查"""

from __future__ import annotations

import json
import logging
from typing import Any

from agents.base import BaseAgent

logger = logging.getLogger(__name__)

SYSTEM_360 = """你是360搜索调查员，专门使用360搜索引擎验证信息真伪。

工具：web_search(query) — 360搜索引擎

工作方式：
1. 从信息中提取1-2个关键事实点
2. 用精准的中文关键词搜索官方数据源
3. 对比搜索结果与原始信息
4. 给出判定和证据

原则：
- 优先搜索 .gov.cn 官方数据源
- 搜索结果已包含标题、URL、摘要
- 2次搜索后必须给出结论
- 不确定就标注"无法验证"
"""

PROMPT_360 = """请用360搜索验证以下信息：

信息：{text}
恶意假设：{malice}

请搜索验证，然后用JSON输出结果：

{{
  "agent": "360搜索",
  "findings": [
    {{
      "claim": "核查的事实点",
      "verdict": "true/false/partial/unverifiable",
      "evidence": "搜索到的证据",
      "sources": [{{"title":"标题","url":"URL","snippet":"摘要"}}],
      "confidence": 0.0-1.0
    }}
  ],
  "summary": "一句话总结360搜索的发现",
  "key_evidence": "最关键的证据"
}}"""


class Search360Agent(BaseAgent):
    """360搜索调查员"""

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        text = input_data["text"]
        malice = input_data.get("malice_hypothesis", "")
        tools = input_data.get("tools_360", [])
        executor = input_data.get("tool_executor")

        logger.info("[360 Agent] 开始调查...")

        # 只给360搜索工具（web_search + fetch_url）
        search_only_tools = [t for t in tools if t["function"]["name"] in ("web_search", "fetch_url")]

        # Step 1: 工具搜索
        search_raw = ""
        try:
            search_raw = await self.llm.chat_with_tools(
                prompt=f"请用360搜索验证以下信息，搜索后简要报告发现了什么。\n\n信息：{text}\n恶意假设：{malice}",
                system=SYSTEM_360,
                tools=search_only_tools,
                tool_executor=executor,
                max_rounds=2,
            )
        except Exception as e:
            logger.warning(f"[360 Agent] 搜索失败: {e}")
            search_raw = f"搜索失败: {e}"

        # Step 2: 整理JSON
        try:
            result = await self.llm.chat_json(
                prompt=PROMPT_360.format(text=text, malice=malice) + f"\n\n🔍 搜索原始结果：\n{search_raw[:2000]}",
                system=SYSTEM_360 + "\n请基于搜索结果整理JSON输出。",
            )
        except Exception as e:
            logger.warning(f"[360 Agent] JSON整理失败: {e}")
            result = {"agent": "360搜索", "findings": [], "summary": f"JSON整理失败: {e}", "key_evidence": search_raw[:200]}

        logger.info(f"[360 Agent] 完成: {len(result.get('findings', []))} 个发现")
        return result
