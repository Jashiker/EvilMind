"""Agent 2: 核查记者 — Fact Investigator

职责：像调查记者一样，对高危信息进行溯源、交叉验证、逻辑推演。
     使用360搜索 API 进行搜索，读取原始网页核实。
     只在恶意假设官判定"升级"时才启动。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from agents.base import BaseAgent

logger = logging.getLogger(__name__)

INVESTIGATOR_SYSTEM = """你是一位专业的调查记者，专门核查信息的真实性。

你拥有以下工具：
1. web_search(query) — 使用360搜索引擎搜索互联网，获取权威数据和信息来源
2. fetch_url(url) — 读取指定网页的完整内容，获取原始数据

你的工作流程：
1. 从待核查信息中提取1-2个最关键的可验证事实点
2. 对每个事实点使用 web_search 搜索1次（搜索词要精准，包含官方机构名）
3. 搜索完成后立即根据搜索结果给出判定，不要反复搜索
4. 只在搜索结果摘要不够明确时，才用 fetch_url 读取1个网页

重要规则：
- 最多使用2次 web_search，1次 fetch_url
- 搜索后必须立即给出JSON结果，不要继续搜索
- 搜索词格式：'[关键词] [官方机构名] 官方数据'
- 如果搜索结果已经能判定真伪，不要再搜索
- 无法验证的标注"无法验证"，不要猜测"""

INVESTIGATOR_PROMPT = """请核查以下信息的真实性。

待核查信息：
{text}

恶意假设官的分析：
{malice_context}

请按以下步骤操作：
1. 提取所有可验证的事实点（数据、事件、引言等）
2. 对每个事实点使用 web_search 进行搜索验证（优先搜索中文官方数据源）
3. 对关键数据源使用 fetch_url 读取原始网页确认
4. 给出每个事实点的真伪判定

请用以下 JSON 格式输出最终结果（在你完成所有搜索后）：
{{
  "claims": [
    {{
      "claim": "事实声明原文",
      "claim_type": "data|event|quote|statistic",
      "verifiable": true,
      "verdict": "true|false|partial|unverifiable",
      "confidence": 0.0到1.0,
      "official_data": {{"source": "数据来源", "actual_value": "实际数据"}},
      "sources": [
        {{"title": "来源标题", "url": "来源URL", "snippet": "关键内容摘录"}}
      ],
      "explanation": "通俗的判定说明"
    }}
  ],
  "overall_factual_score": 0.0到1.0的综合置信度,
  "original_source_found": true或false（是否找到了原始出处）,
  "cross_validation_count": 交叉验证的信源数量,
  "investigation_notes": "调查记者笔记（一段话总结调查发现）",
  "summary": "一段通俗的话总结事实核查结论"
}}
"""


class FactInvestigatorAgent(BaseAgent):
    """Agent 2: 核查记者 — 深度溯源+交叉验证"""

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        text = input_data["text"]
        malice_result = input_data.get("malice_result", {})
        tools = input_data.get("tools", [])
        tool_executor = input_data.get("tool_executor")

        logger.info("[Agent 2] 开始深度核查（调查记者模式）...")

        # 构建恶意假设上下文
        malice_context = ""
        if malice_result:
            malice_context = f"""
恶意假设: {malice_result.get('malice_hypothesis', '无')}
邪恶评分: {malice_result.get('evil_score', 0)}
主要攻击维度: {malice_result.get('primary_attack', 'unknown')}
"""

        # 查知识库获取相似案例作为参考
        similar = self.knowledge.search_similar(text, top_k=3)
        kb_context = ""
        if similar and similar[0]["similarity"] >= 0.6:
            kb_context = f"\n\n知识库参考案例（仅供参考）：{json.dumps([{'text': s['document'][:80], 'verdict': s['metadata'].get('verdict','')} for s in similar], ensure_ascii=False)}"

        # Step 1: 使用 function calling 让模型搜索
        search_results_text = ""
        try:
            search_results_text = await self.llm.chat_with_tools(
                prompt=f"请搜索验证以下信息的关键事实。搜索后简要说明发现了什么。\n\n信息：{text}\n{malice_context}{kb_context}",
                system=INVESTIGATOR_SYSTEM,
                tools=tools,
                tool_executor=tool_executor,
                max_rounds=2,
            )
        except Exception as e:
            logger.error(f"[Agent 2] 搜索失败: {e}")

        # Step 2: 基于搜索结果，让模型整理结构化 JSON
        if not search_results_text or len(search_results_text) < 20:
            logger.warning("[Agent 2] 搜索无结果，使用知识库+推理判断")
            search_results_text = f"搜索未能获取有效结果。请基于以下已知信息进行判断：{kb_context}"

        try:
            result = await self.llm.chat_json(
                prompt=INVESTIGATOR_PROMPT.format(text=text, malice_context=malice_context)
                       + f"\n\n🔍 360搜索结果：\n{search_results_text[:2000]}"
                       + kb_context,
                system=INVESTIGATOR_SYSTEM,
            )
        except Exception as e:
            logger.error(f"[Agent 2] JSON整理失败: {e}")
            result = {
                "claims": [],
                "overall_factual_score": 0.5,
                "original_source_found": False,
                "cross_validation_count": 0,
                "investigation_notes": f"结果整理失败: {e}",
                "summary": search_results_text[:300],
            }

        claims = result.get("claims", [])
        false_count = sum(1 for c in claims if c.get("verdict") == "false")
        score = result.get("overall_factual_score", 0.5)

        logger.info(f"[Agent 2] 核查完成: {len(claims)} 个事实点, {false_count} 个为假, 置信度 {score}")

        return {
            "claims": claims,
            "overall_factual_score": min(1.0, max(0.0, float(score))),
            "original_source_found": result.get("original_source_found", False),
            "cross_validation_count": result.get("cross_validation_count", 0),
            "investigation_notes": result.get("investigation_notes", ""),
            "summary": result.get("summary", ""),
        }
