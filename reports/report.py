"""报告生成器 — 汇总3个Agent的结果，生成最终报告"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ReportGenerator:
    """汇总分析结果，生成最终核查报告"""

    def generate(
        self,
        report_id: str,
        text: str,
        malice_result: dict,
        investigator_result: dict,
        publisher_result: dict,
        escalation: str,
    ) -> dict:
        """生成最终报告

        Args:
            report_id: 报告唯一ID
            text: 原始输入文本
            malice_result: Agent 1 的结果
            investigator_result: Agent 2 的结果
            publisher_result: Agent 3 的结果
            escalation: 分级决策结果 "deep" | "quick"

        Returns:
            完整的报告 dict
        """
        evil = malice_result.get("evil_score", 0)

        # 如果是快速判伪（低危），使用简化报告
        if escalation == "quick":
            return self._quick_report(report_id, text, malice_result, publisher_result)

        # 深度核查报告
        return self._deep_report(report_id, text, malice_result, investigator_result, publisher_result)

    def _quick_report(self, report_id: str, text: str, malice_result: dict, publisher_result: dict) -> dict:
        """低危信息的快速判伪报告"""
        evil = malice_result.get("evil_score", 0)
        return {
            "id": report_id,
            "input_text": text,
            "escalation": "quick",
            "overall_verdict": publisher_result.get("overall_verdict", "verdict_suspicious"),
            "verdict_display": publisher_result.get("verdict_display", "🟢 低危信息"),
            "evil_score": evil,
            "confidence": publisher_result.get("confidence", 0.8),
            "one_sentence_verdict": publisher_result.get("one_sentence_verdict", ""),
            "malice_hypothesis": malice_result.get("malice_hypothesis", ""),
            "thinking_visible": malice_result.get("thinking_visible", ""),
            "attack_dimensions": malice_result.get("attack_dimensions", {}),
            "prescription": publisher_result.get("prescription", {}),
            "debunk_card": publisher_result.get("debunk_card", {}),
            "category": publisher_result.get("category", "none"),
            "investigation_depth": "quick",
            "investigation_notes": "低危信息，快速判伪，未启动深度核查",
            "knowledge_hit": False,
            "knowledge_new_entry": True,
        }

    def _deep_report(
        self,
        report_id: str,
        text: str,
        malice_result: dict,
        investigator_result: dict,
        publisher_result: dict,
    ) -> dict:
        """高危信息的深度核查报告"""
        evil = malice_result.get("evil_score", 0)

        return {
            "id": report_id,
            "input_text": text,
            "escalation": "deep",
            "overall_verdict": publisher_result.get("overall_verdict", "verdict_unknown"),
            "verdict_display": publisher_result.get("verdict_display", ""),
            "evil_score": evil,
            "confidence": publisher_result.get("confidence", 0.8),
            "one_sentence_verdict": publisher_result.get("one_sentence_verdict", ""),
            "malice_hypothesis": malice_result.get("malice_hypothesis", ""),
            "thinking_visible": malice_result.get("thinking_visible", ""),
            "attack_dimensions": malice_result.get("attack_dimensions", {}),
            "primary_attack": malice_result.get("primary_attack", ""),
            "factual_score": investigator_result.get("overall_factual_score", 0.5),
            "original_source_found": investigator_result.get("original_source_found", False),
            "cross_validation_count": investigator_result.get("cross_validation_count", 0),
            "investigation_notes": investigator_result.get("investigation_notes", ""),
            "search_sources_summary": publisher_result.get("search_sources_summary", ""),
            "prescription": publisher_result.get("prescription", {}),
            "debunk_card": publisher_result.get("debunk_card", {}),
            "category": publisher_result.get("category", "none"),
            "investigation_depth": "deep",
            "knowledge_hit": False,
            "knowledge_new_entry": True,
        }
