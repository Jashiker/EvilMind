"""真相猎人 — 多Agent并行调查 + 辩论共识

零信任模型：假设所有信息都是不可信/邪恶的，全部深度核查。

流程：
  信息输入
    → 知识库检索（命中直接复用）
    → 3路并行调查（360搜索 | Firecrawl搜索 | Firecrawl抓取）
    → 辩论合成
    → 真相发布官
    → 质量审查官
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Callable, Coroutine

from llm.client import LLMClient
from knowledge.store import KnowledgeStore
from agents.malice_hypothesis import MaliceHypothesisAgent
from agents.search_360 import Search360Agent
from agents.search_firecrawl import FirecrawlSearchAgent, FirecrawlScrapeAgent
from agents.debate_synthesizer import DebateSynthesizer
from agents.truth_publisher import TruthPublisherAgent
from output.report import ReportGenerator
from search.web_search import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """多Agent并行调查 + 辩论共识"""

    def __init__(self, llm: LLMClient, knowledge: KnowledgeStore, report_gen: ReportGenerator):
        self.llm = llm
        self.knowledge = knowledge
        self.report_gen = report_gen

        # Agent 1: 恶意假设官（提供零信任视角）
        self.malice_agent = MaliceHypothesisAgent(llm, knowledge)
        # 3路并行调查
        self.agent_360 = Search360Agent(llm, knowledge)
        self.agent_fc_search = FirecrawlSearchAgent(llm, knowledge)
        self.agent_fc_scrape = FirecrawlScrapeAgent(llm, knowledge)
        # 辩论 + 发布 + 审查
        self.debater = DebateSynthesizer(llm, knowledge)
        self.publisher = TruthPublisherAgent(llm, knowledge)

    async def analyze(
        self,
        text: str,
        stream_callback: Callable[[dict], Coroutine] | None = None,
    ) -> dict:
        report_id = uuid.uuid4().hex[:12]
        logger.info(f"[Pipeline] 零信任核查: {text[:50]}...")

        # ── 知识库检索 ──
        similar = self.knowledge.search_similar(text, top_k=3)
        if similar and similar[0]["similarity"] >= 0.9:
            logger.info(f"[Pipeline] 知识库命中 ({similar[0]['similarity']})")
            if stream_callback:
                await stream_callback({
                    "event": "knowledge_hit", "agent": "system",
                    "data": {"similarity": similar[0]["similarity"], "verdict": similar[0]["metadata"]["verdict"]},
                })
            return self._reuse_report(report_id, text, similar[0])

        # ═══════════════════════════════════════════
        # Step 0: 谣言指纹提取
        # ═══════════════════════════════════════════
        from knowledge.fingerprint import extract_fingerprint, find_similar_fingerprints, fingerprint_summary

        fingerprint = extract_fingerprint(text)
        similar_fingerprints = find_similar_fingerprints(fingerprint, self.knowledge)
        fp_summary = fingerprint_summary(fingerprint)

        if stream_callback:
            await stream_callback({
                "event": "fingerprint",
                "data": {
                    "fingerprint": fingerprint,
                    "summary": fp_summary,
                    "similar_cases": similar_fingerprints[:3],
                },
            })

        # ═══════════════════════════════════════════
        # Step 1: 恶意假设官 — 零信任视角分析（含指纹信息）
        # ═══════════════════════════════════════════
        if stream_callback:
            await stream_callback({
                "event": "agent_start", "agent": "malice",
                "data": {"name": "谣言指纹官", "status": "🛡️ 零信任模式：提取指纹特征，分析恶意意图..."},
            })

        # 行为+动机分析
        from knowledge.evolution import analyze_behavior, analyze_motivation, build_evolution_tree

        behavior = analyze_behavior(text, fingerprint)
        motivation = analyze_motivation(text, fingerprint)
        evolution = build_evolution_tree(text, self.knowledge)

        if stream_callback:
            await stream_callback({
                "event": "behavior_motivation",
                "data": {
                    "behavior": behavior,
                    "motivation": motivation,
                    "evolution": {
                        "total_variants": evolution.get("total_variants_found", 0),
                        "mutation_patterns": evolution.get("mutation_patterns", []),
                    },
                },
            })

        fp_context = f"\n\n谣言指纹特征：{fp_summary}\n行为分析：{behavior.get('behavior_summary','')}\n动机分析：{motivation.get('motive_summary','')}\n知识库中指纹相似的案例：{len(similar_fingerprints)}个"
        malice_result = await self.malice_agent.run({"text": text + fp_context})

        if stream_callback:
            await stream_callback({
                "event": "agent_complete", "agent": "malice",
                "data": {
                    "evil_score": malice_result["evil_score"],
                    "malice_hypothesis": malice_result.get("malice_hypothesis", ""),
                    "attack_dimensions": malice_result.get("attack_dimensions", {}),
                    "thinking_visible": malice_result.get("thinking_visible", ""),
                    "primary_attack": malice_result.get("primary_attack", ""),
                },
            })

        # ═══════════════════════════════════════════
        # Step 2: 3路并行调查
        # ═══════════════════════════════════════════
        if stream_callback:
            await stream_callback({
                "event": "parallel_start",
                "data": {"message": "🔍 3路调查员并行取证中...", "agents": ["360搜索", "Firecrawl搜索", "Firecrawl抓取"]},
            })

        # 准备工具子集
        tools_360 = [t for t in TOOL_DEFINITIONS if t["function"]["name"] in ("web_search", "fetch_url")]
        tools_fc = [t for t in TOOL_DEFINITIONS if t["function"]["name"].startswith("firecrawl_")]

        shared_input = {
            "text": text,
            "malice_hypothesis": malice_result.get("malice_hypothesis", ""),
            "tool_executor": execute_tool,
        }

        # 3路并行执行
        results = await asyncio.gather(
            self.agent_360.run({**shared_input, "tools_360": tools_360}),
            self.agent_fc_search.run({**shared_input, "tools_fc_search": tools_fc}),
            self.agent_fc_scrape.run({**shared_input, "tools_fc_scrape": tools_fc}),
            return_exceptions=True,
        )

        findings_360 = results[0] if not isinstance(results[0], Exception) else {"agent": "360搜索", "findings": [], "summary": f"异常: {results[0]}"}
        findings_fc_search = results[1] if not isinstance(results[1], Exception) else {"agent": "Firecrawl搜索", "findings": [], "summary": f"异常: {results[1]}"}
        findings_fc_scrape = results[2] if not isinstance(results[2], Exception) else {"agent": "Firecrawl抓取", "findings": [], "summary": f"异常: {results[2]}"}

        if stream_callback:
            await stream_callback({
                "event": "parallel_complete",
                "data": {
                    "findings_360": findings_360,
                    "findings_fc_search": findings_fc_search,
                    "findings_fc_scrape": findings_fc_scrape,
                },
            })

        # ═══════════════════════════════════════════
        # Step 3: 辩论合成
        # ═══════════════════════════════════════════
        if stream_callback:
            await stream_callback({
                "event": "agent_start", "agent": "debater",
                "data": {"name": "真相仲裁官", "status": "正在对比3路证据，辩论裁定共识..."},
            })

        debate_result = await self.debater.run({
            "text": text,
            "malice_hypothesis": malice_result.get("malice_hypothesis", ""),
            "findings_360": findings_360,
            "findings_fc_search": findings_fc_search,
            "findings_fc_scrape": findings_fc_scrape,
        })

        if stream_callback:
            await stream_callback({
                "event": "agent_complete", "agent": "debater",
                "data": debate_result,
            })

        # ═══════════════════════════════════════════
        # Step 4: 发布官
        # ═══════════════════════════════════════════
        if stream_callback:
            await stream_callback({
                "event": "agent_start", "agent": "publisher",
                "data": {"name": "真相仲裁官", "status": "正在生成核查报告和认知处方..."},
            })

        # 合并调查结果供发布官使用
        merged_investigation = {
            "claims": [],
            "overall_factual_score": debate_result.get("final_verdict", {}).get("confidence", 0.5),
            "cross_validation_count": debate_result.get("cross_validation", {}).get("agreeing_sources", 0),
            "investigation_notes": debate_result.get("debate_summary", ""),
            "summary": f"360: {findings_360.get('summary', '')} | FC搜索: {findings_fc_search.get('summary', '')} | FC抓取: {findings_fc_scrape.get('summary', '')}",
        }

        publisher_result = await self.publisher.run({
            "text": text,
            "malice_result": malice_result,
            "investigator_result": merged_investigation,
        })

        if stream_callback:
            await stream_callback({
                "event": "agent_complete", "agent": "publisher",
                "data": publisher_result,
            })

        # ═══════════════════════════════════════════
        # Step 5: 质量审查
        # ═══════════════════════════════════════════
        if stream_callback:
            await stream_callback({
                "event": "agent_start", "agent": "evaluator",
                "data": {"name": "品质审核官", "status": "正在对报告进行四维质量评估..."},
            })

        temp_report = self.report_gen.generate(
            report_id=report_id, text=text,
            malice_result=malice_result,
            investigator_result=merged_investigation,
            publisher_result=publisher_result,
            escalation="deep",
        )

        evaluation = await self.publisher.self_evaluate(temp_report)

        if stream_callback:
            await stream_callback({
                "event": "agent_complete", "agent": "evaluator",
                "data": evaluation,
            })

        # ═══════════════════════════════════════════
        # 最终报告
        # ═══════════════════════════════════════════
        report = temp_report
        report["self_evaluation"] = evaluation
        report["debate"] = debate_result
        report["fingerprint"] = fingerprint
        report["behavior"] = behavior
        report["motivation"] = motivation
        report["evolution"] = evolution

        if stream_callback:
            await stream_callback({"event": "report", "data": report})

        # 入库
        self.knowledge.add_case(
            text=text,
            verdict=report.get("overall_verdict", "suspicious"),
            category=publisher_result.get("category", "none"),
            evidence_summary=publisher_result.get("one_sentence_verdict", ""),
            evil_score=malice_result.get("evil_score", 0.5),
            report=report,
        )

        if stream_callback:
            await stream_callback({"event": "done", "data": {"message": "核查完成"}})

        return report

    def _reuse_report(self, report_id: str, text: str, case: dict) -> dict:
        meta = case.get("metadata", {})
        return {
            "id": report_id, "input_text": text, "escalation": "cached",
            "overall_verdict": meta.get("verdict", "suspicious"),
            "verdict_display": f"📚 知识库已有相同案例 | 原判: {meta.get('verdict', '')}",
            "evil_score": meta.get("evil_score", 0.5), "confidence": 0.95,
            "one_sentence_verdict": f"该信息已被核查过，结论：{meta.get('verdict', '')}",
            "evidence_chain": [{"step": 1, "description": "知识库命中相同案例", "source": f"案例ID: {case['id']}", "finding": "直接复用已验证结论"}],
            "prescription": {}, "debunk_card": {}, "category": meta.get("category", ""),
            "investigation_depth": "cached", "knowledge_hit": True, "knowledge_new_entry": False,
        }
