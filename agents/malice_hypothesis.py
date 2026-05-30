"""Agent 1: 恶意假设官 — Malice Hypothesis Officer

职责：先假设每条信息背后藏着最邪恶的目的，评估攻击维度，
      打出邪恶评分，决定是否触发深度核查。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from agents.base import BaseAgent

logger = logging.getLogger(__name__)

MALICE_SYSTEM = """你是一位资深的"恶意假设分析师"，专门评估信息背后的潜在攻击意图。

你的工作方式与众不同：拿到一条信息后，你先假设信息的发布者怀有最邪恶的目的，
然后分析这个目的在攻击什么。

你需要评估4个攻击维度：
1. **政治稳定攻击** (political_stability) — 试图动摇对政治体制的信任
2. **经济信心攻击** (economic_confidence) — 试图制造经济恐慌或对经济前景的悲观
3. **社会团结攻击** (social_cohesion) — 试图制造群体对立、撕裂社会
4. **制度信任攻击** (institutional_trust) — 试图瓦解对制度/机构的信任

注意：
- 普通的健康谣言、养生偏方通常邪恶评分较低（<0.3），因为它们主要攻击的是个人判断力而非社会
- 但如果有组织的、系统性的否定官方数据、制造社会对立信息，邪恶评分应该高
- 把信息的具体内容和更大的攻击意图联系起来分析

评分参考：
- 0.8-1.0：高度危险，系统性地攻击政治/经济/社会核心信任
- 0.5-0.8：中等危险，有明显的恶意操纵痕迹
- 0.2-0.5：低危，可能存在误导但无明显攻击意图
- 0.0-0.2：基本无害，多为个人观点或普通误解"""

MALICE_PROMPT = """请分析以下信息，完成三件事：

== 第一件事：恶意假设 ==
假设这条信息的发布者怀有最邪恶的目的——他想通过这条信息达到什么效果？
请用一段话描述你的假设。不要回避，大胆假设。

== 第二件事：攻击维度评估 ==
评估这条信息在4个攻击维度上的得分（0.0-1.0）：

== 第三件事：邪恶评分和升级决策 ==
综合评估后给出：
- evil_score: 0.0-1.0
- escalation: "deep" (需要深度核查) 或 "quick" (快速判伪即可)
- reasoning: 一句话说明理由

待分析信息：
{text}

请以JSON格式输出：
{{
  "malice_hypothesis": "你的恶意假设（一段话，描述发布者最邪恶的目的）",
  "attack_dimensions": {{
    "political_stability": 0.0到1.0,
    "economic_confidence": 0.0到1.0,
    "social_cohesion": 0.0到1.0,
    "institutional_trust": 0.0到1.0
  }},
  "primary_attack": "最主要的攻击维度: political_stability/economic_confidence/social_cohesion/institutional_trust",
  "evil_score": 0.0到1.0,
  "escalation": "deep 或 quick",
  "reasoning": "一句话说明升级/不升级的理由",
  "likely_category": "最可能的操纵手法: data_fabrication/emotion_hijack/narrative_transplant/authority_fake/trust_corrosion/selective_feeding/none",
  "thinking_visible": "一段给用户看的思考过程，用口语化语言描述（50字以内）"
}}"""


class MaliceHypothesisAgent(BaseAgent):
    """Agent 1: 恶意假设官 — 邪恶评分 + 分级决策"""

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        text = input_data["text"]
        logger.info("[Agent 1] 开始恶意假设分析...")

        # 查询知识库中的相关模式
        similar_patterns = self.knowledge.search_patterns(text, top_k=3)
        pattern_hint = ""
        if similar_patterns:
            cats = [p["metadata"].get("category", "") for p in similar_patterns]
            pattern_hint = f"\n\n知识库提示：此信息可能与以下操纵模式相似：{', '.join(cats)}"

        try:
            raw = await self.llm.chat_json(
                prompt=MALICE_PROMPT.format(text=text) + pattern_hint,
                system=MALICE_SYSTEM,
            )
        except Exception as e:
            logger.error(f"[Agent 1] 分析失败: {e}")
            return {
                "evil_score": 0.5,
                "escalation": "deep",
                "reasoning": f"分析出错，默认深度核查: {e}",
                "thinking_visible": "分析遇到问题，为安全起见启动深度核查...",
                "malice_hypothesis": "",
                "attack_dimensions": {},
                "primary_attack": "unknown",
                "likely_category": "none",
            }

        evil = float(raw.get("evil_score", 0.5))
        escalation = raw.get("escalation", "deep")
        if evil < 0.4:
            escalation = "quick"

        logger.info(f"[Agent 1] 邪恶评分: {evil}, 决策: {escalation}, 主攻击维度: {raw.get('primary_attack', 'unknown')}")

        return {
            "evil_score": evil,
            "escalation": escalation,
            "malice_hypothesis": raw.get("malice_hypothesis", ""),
            "attack_dimensions": raw.get("attack_dimensions", {}),
            "primary_attack": raw.get("primary_attack", "unknown"),
            "reasoning": raw.get("reasoning", ""),
            "thinking_visible": raw.get("thinking_visible", ""),
            "likely_category": raw.get("likely_category", "none"),
        }
