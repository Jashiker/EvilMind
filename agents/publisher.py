"""Agent 3: 真相发布官 — Truth Publisher

职责：汇总前面的分析结果，生成用户可读的核查报告、证据链、认知处方、辟谣卡片。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from agents.base import BaseAgent

logger = logging.getLogger(__name__)

PUBLISHER_SYSTEM = """你是一位真相发布官，负责把专业的核查结果翻译成普通人能看懂的报告。

你的工作包括：
1. 总结核查结论（一句话说清楚）
2. 构建证据链（每一步可追溯）
3. 开具认知处方（告诉用户：怎么骗的、什么弱点被利用、以后怎么防）
4. 生成辟谣卡片内容（精简版，适合分享）

原则：
- 用大白话，不要用专业术语
- 面向普通读者，作为你的家人你会怎么跟他们说
- 认知处方要有温度、有帮助性，不要高高在上
- 辟谣卡片要简洁有力，适合在微信群里传播"""

PUBLISHER_PROMPT = """请根据以下信息生成核查报告。

原始信息：
{text}

恶意假设官的分析：
{malice_context}

核查记者的发现：
{investigator_context}

请输出完整的核查报告，JSON格式：
{{
  "one_sentence_verdict": "一句话结论（面向普通读者，不超过30字）",
  "overall_verdict": "verdict_true|verdict_false|verdict_manipulative|verdict_suspicious|verdict_unknown",
  "verdict_display": "用于展示的结论标签，如'🔴 高度危险的认知操纵'",
  "evil_score": 0.0到1.0,
  "confidence": 0.0到1.0,
  "evidence_chain": [
    {{"step": 1, "description": "第一步做了什么", "source": "来源说明", "finding": "发现了什么"}}
  ],
  "prescription": {{
    "how_deceived": ["它是怎么骗你的第1点", "第2点", "第3点"],
    "cognitive_weakness": ["你的认知弱点1", "弱点2"],
    "prevention": ["防骗建议1", "建议2", "建议3"],
    "immunity_quote": "一句让人记住的防骗口诀（10-15字）"
  }},
  "debunk_card": {{
    "headline": "辟谣标题（简短有力）",
    "fake_claim": "被辟谣的说法",
    "truth": "真相（50字以内）",
    "source": "信息来源",
    "tips": "防骗小贴士（20字以内）"
  }},
  "category": "操纵手法分类: data_fabrication/emotion_hijack/narrative_transplant/authority_fake/trust_corrosion/selective_feeding/none",
  "search_sources_summary": "搜索过程摘要，提及360搜索"
}}
"""


class ReportPublisher(BaseAgent):
    """Agent 3: 真相发布官 — 报告生成 + 认知处方 + 辟谣卡片"""

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        text = input_data["text"]
        malice_result = input_data.get("malice_result", {})
        investigator_result = input_data.get("investigator_result", {})

        logger.info("[Agent 3] 开始生成核查报告...")

        # 构建上下文
        malice_context = json.dumps({
            "evil_score": malice_result.get("evil_score", 0),
            "malice_hypothesis": malice_result.get("malice_hypothesis", ""),
            "primary_attack": malice_result.get("primary_attack", ""),
            "likely_category": malice_result.get("likely_category", ""),
        }, ensure_ascii=False)

        investigator_context = json.dumps({
            "overall_factual_score": investigator_result.get("overall_factual_score", 0.5),
            "original_source_found": investigator_result.get("original_source_found", False),
            "cross_validation_count": investigator_result.get("cross_validation_count", 0),
            "summary": investigator_result.get("summary", ""),
            "investigation_notes": investigator_result.get("investigation_notes", ""),
            "claims": investigator_result.get("claims", []),
        }, ensure_ascii=False)

        try:
            raw = await self.llm.chat_json(
                prompt=PUBLISHER_PROMPT.format(
                    text=text,
                    malice_context=malice_context,
                    investigator_context=investigator_context,
                ),
                system=PUBLISHER_SYSTEM,
            )
        except Exception as e:
            logger.error(f"[Agent 3] 生成报告失败: {e}")
            evil = malice_result.get("evil_score", 0.5)
            return {
                "one_sentence_verdict": f"核查报告生成出错: {e}",
                "overall_verdict": "verdict_unknown",
                "verdict_display": "⚪ 报告生成失败",
                "evil_score": evil,
                "confidence": 0.5,
                "evidence_chain": [],
                "prescription": {},
                "debunk_card": {},
                "category": "none",
                "search_sources_summary": "",
            }

        logger.info("[Agent 3] 报告生成完成")

        return {
            "one_sentence_verdict": raw.get("one_sentence_verdict", ""),
            "overall_verdict": raw.get("overall_verdict", "verdict_unknown"),
            "verdict_display": raw.get("verdict_display", ""),
            "evil_score": float(raw.get("evil_score", 0)),
            "confidence": float(raw.get("confidence", 0.8)),
            "evidence_chain": raw.get("evidence_chain", []),
            "prescription": raw.get("prescription", {}),
            "debunk_card": raw.get("debunk_card", {}),
            "category": raw.get("category", "none"),
            "search_sources_summary": raw.get("search_sources_summary", ""),
        }

    async def self_evaluate(self, report: dict) -> dict:
        """自我评估：对研判结果进行质量审查

        审查维度：
        1. 证据链是否充分、可追溯
        2. 置信度是否合理
        3. 是否有遗漏的核查角度
        4. 结论是否有过度推断
        """
        logger.info("[Agent 3] 开始自我评估...")

        prompt = f"""你是一位严格的真相审查官。请对你的核查报告进行自我评估。

核查报告：
{json.dumps(report, ensure_ascii=False, indent=2)}

请从以下4个维度进行严格评估，每个维度0.0-1.0分：

1. **证据充分性** — 每个判定是否有足够来源支撑？证据链是否可追溯？
2. **置信度合理性** — 报告的 confidence 分数是否符合实际证据强度？
3. **核查完整性** — 是否有遗漏的关键事实点或验证角度？
4. **结论严谨性** — 结论是否有过度推断？是否存在其他可能的解释？

请输出 JSON：
{{
  "quality_score": 0.0到1.0的综合质量分,
  "dimensions": {{
    "evidence_sufficiency": 0.0到1.0,
    "confidence_reasonability": 0.0到1.0,
    "completeness": 0.0到1.0,
    "rigor": 0.0到1.0
  }},
  "strengths": ["做得好的地方1", "做得好的地方2"],
  "weaknesses": ["需要改进的地方1", "需要改进的地方2"],
  "missed_angles": ["可能遗漏的核查角度1"],
  "confidence_adjustment": "上调/维持/下调（附带理由）",
  "final_assessment": "一段话的最终评估（50字内）"
}}"""

        try:
            raw = await self.llm.chat_json(
                prompt=prompt,
                system="你是一位真相核查质量审查官。对自己严格、诚实、不回避问题。",
            )
        except Exception as e:
            logger.warning(f"[Agent 3] 自我评估失败: {e}")
            return {
                "quality_score": 0.7,
                "dimensions": {},
                "strengths": ["自动评估未完成"],
                "weaknesses": [],
                "missed_angles": [],
                "confidence_adjustment": "维持",
                "final_assessment": f"自我评估未完成: {e}",
            }

        logger.info(f"[Agent 3] 自我评估完成: quality={raw.get('quality_score', 0)}")
        return raw
