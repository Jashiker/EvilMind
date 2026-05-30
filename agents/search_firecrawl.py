"""Firecrawl 搜索 Agent — 使用 Firecrawl search + scrape 进行深度调查"""

from __future__ import annotations

import json
import logging
from typing import Any

from agents.base import BaseAgent

logger = logging.getLogger(__name__)

SYSTEM_FC_SEARCH = """你是Firecrawl深度搜索调查员，使用Firecrawl搜索引擎获取网页完整内容。

工具：
- firecrawl_search(query) — 搜索并自动抓取结果页的完整Markdown内容
- firecrawl_scrape(url) — 抓取指定URL的干净Markdown内容

优势：Firecrawl能获取网页的完整正文（去噪后的Markdown），比普通搜索摘要信息量大得多。

工作方式：
1. 先用 firecrawl_search 搜索1-2个精准关键词
2. 如需深入某个页面，用 firecrawl_scrape 抓取原文
3. 对比发现与原始信息
4. 给出判定

原则：最多2次工具调用，之后必须输出JSON结论。
"""

SYSTEM_FC_SCRAPE = """你是Firecrawl精准抓取调查员，专门用Firecrawl抓取特定URL的完整内容进行深度阅读。

工具：
- firecrawl_scrape(url) — 抓取指定URL的干净Markdown内容，去除广告和导航，保留正文
- firecrawl_search(query) — 搜索并抓取搜索结果

优势：Firecrawl抓取的Markdown内容比普通网页抓取干净10倍，保留原文结构。

工作方式：
1. 如果已知具体URL（如stats.gov.cn），直接用 firecrawl_scrape 抓取
2. 否则用 firecrawl_search 找到目标页面再抓取
3. 仔细阅读正文，提取关键数据
4. 与原始信息对比

原则：最多2次工具调用，之后必须输出JSON结论。
"""

PROMPT_FC = """请用Firecrawl验证以下信息：

信息：{text}
恶意假设：{malice}

请用你的工具进行调查，然后输出JSON：

{{
  "agent": "{agent_name}",
  "findings": [
    {{
      "claim": "核查的事实点",
      "verdict": "true/false/partial/unverifiable",
      "evidence": "抓取到的关键证据（引用原文数据）",
      "sources": [{{"title":"页面标题","url":"URL","content":"关键段落"}}],
      "confidence": 0.0-1.0
    }}
  ],
  "summary": "一句话总结发现",
  "key_evidence": "最关键的证据（引用具体数据）"
}}"""


class FirecrawlSearchAgent(BaseAgent):
    """Firecrawl 搜索调查员 — 使用 firecrawl_search"""

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        text = input_data["text"]
        malice = input_data.get("malice_hypothesis", "")
        tools = input_data.get("tools_fc_search", [])
        executor = input_data.get("tool_executor")

        logger.info("[FC Search Agent] 开始调查...")

        # Step 1: 工具搜索
        search_raw = ""
        try:
            search_raw = await self.llm.chat_with_tools(
                prompt=f"请用Firecrawl搜索验证以下信息，搜索后简要报告发现了什么。\n\n信息：{text}\n恶意假设：{malice}",
                system=SYSTEM_FC_SEARCH,
                tools=tools,
                tool_executor=executor,
                max_rounds=2,
            )
        except Exception as e:
            logger.warning(f"[FC Search Agent] 搜索失败: {e}")
            search_raw = f"搜索失败: {e}"

        # Step 2: 整理JSON
        try:
            result = await self.llm.chat_json(
                prompt=PROMPT_FC.format(text=text, malice=malice, agent_name="Firecrawl搜索")
                       + f"\n\n🔍 搜索原始结果：\n{search_raw[:2000]}",
                system=SYSTEM_FC_SEARCH + "\n请基于搜索结果整理JSON输出。",
            )
        except Exception as e:
            logger.warning(f"[FC Search Agent] JSON失败: {e}")
            result = {"agent": "Firecrawl搜索", "findings": [], "summary": f"JSON失败: {e}", "key_evidence": search_raw[:200]}

        logger.info(f"[FC Search Agent] 完成: {len(result.get('findings', []))} 个发现")
        return result


class FirecrawlScrapeAgent(BaseAgent):
    """Firecrawl 抓取调查员 — 使用 firecrawl_scrape 精准抓取"""

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        text = input_data["text"]
        malice = input_data.get("malice_hypothesis", "")
        tools = input_data.get("tools_fc_scrape", [])
        executor = input_data.get("tool_executor")

        logger.info("[FC Scrape Agent] 开始调查...")

        # Step 1: 工具抓取
        search_raw = ""
        try:
            search_raw = await self.llm.chat_with_tools(
                prompt=f"请用Firecrawl抓取相关网页验证以下信息，抓取后简要报告发现了什么。\n\n信息：{text}\n恶意假设：{malice}",
                system=SYSTEM_FC_SCRAPE,
                tools=tools,
                tool_executor=executor,
                max_rounds=2,
            )
        except Exception as e:
            logger.warning(f"[FC Scrape Agent] 搜索失败: {e}")
            search_raw = f"搜索失败: {e}"

        # Step 2: 整理JSON
        try:
            result = await self.llm.chat_json(
                prompt=PROMPT_FC.format(text=text, malice=malice, agent_name="Firecrawl抓取")
                       + f"\n\n🔍 抓取原始结果：\n{search_raw[:2000]}",
                system=SYSTEM_FC_SCRAPE + "\n请基于抓取结果整理JSON输出。",
            )
        except Exception as e:
            logger.warning(f"[FC Scrape Agent] JSON失败: {e}")
            result = {"agent": "Firecrawl抓取", "findings": [], "summary": f"JSON失败: {e}", "key_evidence": search_raw[:200]}

        logger.info(f"[FC Scrape Agent] 完成: {len(result.get('findings', []))} 个发现")
        return result
