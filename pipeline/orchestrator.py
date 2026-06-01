"""邪恶思潮 · 4阶段严格顺序管道

阶段1: 指纹研判团队 (5 Agent并行→综合+关键词提取)
阶段2: 三路侦察兵 (3 Agent并行取证)
阶段3: 合议庭仲裁 (综合辩论)
阶段4: 品质审核官
"""

from __future__ import annotations
import asyncio, json, logging, uuid
from typing import Callable, Coroutine

from llm.client import LLMClient
from knowledge.store import KnowledgeStore
from agents.fingerprint_team import FingerprintVerifier, EvolutionAnalyst, IntentMiner, RiskAssessor, SynthesisJudge
from agents.claude_checker import ClaudeFactChecker
from agents.claude_diver import ClaudeDeepDiver
from agents.search_osint import OpenOSINTAgent
from agents.jury import JuryDeliberator
from agents.publisher import ReportPublisher
from reports.report import ReportGenerator
from search.web_search import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)
FULL_TOOLS = TOOL_DEFINITIONS

ANTI_HALLUCINATION = ("\n\n⚠️ 严格规则: 1)只使用搜索返回的真实信息 2)禁止编造来源URL "
                       "3)每条证据须有真实搜索URL 4)不确定标注'无法验证' 5)至少2个独立来源确认事实")


class TruthHunterPipeline:

    def __init__(self, llm: LLMClient, knowledge: KnowledgeStore, report_gen: ReportGenerator):
        self.llm = llm
        self.knowledge = knowledge
        self.report_gen = report_gen
        self._lock = asyncio.Lock()
        self.fp_verifier = FingerprintVerifier(llm, knowledge)
        self.evo_analyst = EvolutionAnalyst(llm, knowledge)
        self.intent_miner = IntentMiner(llm, knowledge)
        self.risk_assessor = RiskAssessor(llm, knowledge)
        self.synthesis_judge = SynthesisJudge(llm, knowledge)
        self.agent_a = ClaudeFactChecker(llm, knowledge)
        self.agent_b = ClaudeDeepDiver(llm, knowledge)
        self.agent_osint = OpenOSINTAgent(llm, knowledge)
        self.debater = JuryDeliberator(llm, knowledge)
        self.publisher = ReportPublisher(llm, knowledge)

    async def analyze(self, text: str, stream_callback: Callable[[dict], Coroutine] | None = None) -> dict:
        async with self._lock:
            return await self._analyze_impl(text, stream_callback)

    async def _analyze_impl(self, text: str, stream_callback: Callable[[dict], Coroutine] | None = None) -> dict:
        report_id = uuid.uuid4().hex[:12]
        logger.info(f"[Pipeline] 核查: {text[:50]}...")
        cb = stream_callback or (lambda _: None)

        from knowledge.fingerprint import extract_fingerprint, find_similar_fingerprints, fingerprint_summary
        from knowledge.evolution import analyze_behavior, analyze_motivation, build_evolution_tree
        from knowledge.cognitive_warfare import detect_attack_patterns

        # ── KB 检索 + 短路径 ──
        similar = self.knowledge.search_similar(text, top_k=5)
        kb_ctx, kb_hint = "", ""
        if similar and similar[0]["similarity"] >= 0.6:
            cases = [f"- [{s['metadata'].get('verdict','')}] {s['document'][:60]}" for s in similar[:3]]
            kb_ctx = f"\n📚 知识库匹配:\n" + "\n".join(cases)
            if similar[0]["similarity"] >= 0.9:
                kb_hint = f"\n⚠️ KB高度匹配(sim={similar[0]['similarity']:.0%})，参考: {similar[0]['metadata'].get('verdict','')}"

        # ── 指纹+行为+动机+进化树 ──
        fp = extract_fingerprint(text)
        fp_sim = find_similar_fingerprints(fp, self.knowledge)
        fp_sum = fingerprint_summary(fp)
        behavior = analyze_behavior(text, fp)
        motivation = analyze_motivation(text, fp)
        evolution = build_evolution_tree(text, self.knowledge)
        cw = detect_attack_patterns(text)
        date_ctx = f"\n当前日期：{__import__('datetime').datetime.now().strftime('%Y年%m月%d日')}。"

        await cb({"event": "fingerprint", "data": {"fingerprint": fp, "summary": fp_sum, "similar_cases": fp_sim[:3]}})
        if cw["template_count"] > 0:
            await cb({"event": "cognitive_warfare", "data": cw})
        await cb({"event": "behavior_motivation", "data": {"behavior": behavior, "motivation": motivation,
                    "evolution": {"total_variants": evolution.get("total_variants_found", 0),
                                  "mutation_patterns": evolution.get("mutation_patterns", [])}}})
        if kb_ctx:
            await cb({"event": "kb_assist", "data": {"match_count": len([s for s in similar if s["similarity"] >= 0.6]),
                       "top_similarity": similar[0]["similarity"] if similar else 0}})

        # ═══════════════════════════════════════════
        # 阶段1: 指纹研判团队 + 关键词提取 (合并为一次综合研判)
        # ═══════════════════════════════════════════
        await cb({"event": "agent_start", "agent": "fp_team",
                  "data": {"name": "恶意假设·指纹研判官", "status": "14维指纹 · 恶意评分 · 关键词提炼"}})

        fp_input = {"text": text, "kb_context": kb_ctx + date_ctx}
        fp_r = await asyncio.gather(
            self.fp_verifier.run(fp_input),
            self.evo_analyst.run({"text": text, "evolution_context": json.dumps(evolution, ensure_ascii=False)}),
            self.intent_miner.run({"text": text, "behavior_context": json.dumps(behavior, ensure_ascii=False),
                                   "motivation_context": json.dumps(motivation, ensure_ascii=False)}),
            self.risk_assessor.run({"text": text, "fingerprint_context": fp_sum, "intent_context": "", "attack_dimensions": ""}),
            return_exceptions=True)
        fp_v = fp_r[0] if not isinstance(fp_r[0], Exception) else {}
        evo_v = fp_r[1] if not isinstance(fp_r[1], Exception) else {}
        int_v = fp_r[2] if not isinstance(fp_r[2], Exception) else {}
        risk_v = fp_r[3] if not isinstance(fp_r[3], Exception) else {}

        malice = await self.synthesis_judge.run({"text": text, "fingerprint_result": fp_v, "evolution_result": evo_v,
                                                  "intent_result": int_v, "risk_result": risk_v})

        await cb({"event": "fp_team_complete", "data": {"fp_verdict": fp_v, "evo_verdict": evo_v,
                  "intent_verdict": int_v, "risk_verdict": risk_v}})
        await cb({"event": "agent_complete", "agent": "malice",
                  "data": {"evil_score": malice.get("evil_score", 0.5),
                           "malice_hypothesis": malice.get("malice_hypothesis", ""),
                           "attack_dimensions": malice.get("attack_dimensions", {}),
                           "primary_attack": malice.get("primary_attack", ""),
                           "synthesis_summary": malice.get("synthesis_summary", "")}})

        # 关键词已由SynthesisJudge一同输出，直接读取
        search_keywords = malice.get("search_keywords", {})
        search_keywords = _enforce_year_tags(search_keywords, text)
        logger.info(f"[Pipeline] 关键词: fact={search_keywords.get('fact_check_keywords')} | deep={search_keywords.get('deep_search_keywords')} | source={search_keywords.get('source_check_keywords')}")
        await cb({"event": "keywords_extracted", "data": search_keywords})

        # ═══════════════════════════════════════════
        # 阶段2: 三路侦察兵
        # ═══════════════════════════════════════════
        await cb({"event": "agent_start", "agent": "recon",
                  "data": {"name": "双路侦察·取证官", "status": "Claude事实核查 + Claude深度挖掘 + 来源验证"}})

        si = {"text": text + kb_ctx + kb_hint + date_ctx,
              "malice_hypothesis": malice.get("malice_hypothesis", ""), "tool_executor": execute_tool,
              "keywords_a": search_keywords.get("fact_check_keywords", []),
              "keywords_b": search_keywords.get("deep_search_keywords", []),
              "keywords_osint": search_keywords.get("source_check_keywords", [])}
        recon_r = await asyncio.gather(
            self.agent_a.run({**si, "tools_a": FULL_TOOLS}),
            self.agent_b.run({**si, "tools_b": FULL_TOOLS}),
            self.agent_osint.run({**si, "tools_osint": FULL_TOOLS}),
            return_exceptions=True)
        fa = recon_r[0] if not isinstance(recon_r[0], Exception) else {"agent": "Checker", "findings": [], "summary": "异常"}
        fb = recon_r[1] if not isinstance(recon_r[1], Exception) else {"agent": "Diver",  "findings": [], "summary": "异常"}
        fos = recon_r[2] if not isinstance(recon_r[2], Exception) else {"agent": "OSINT", "findings": [], "summary": "异常"}

        await asyncio.sleep(0.3)
        await cb({"event": "parallel_complete", "data": {"findings_checker": fa, "findings_diver": fb, "findings_osint": fos}})
        st = _build_search_trace(fa, fb, fos, {})
        await cb({"event": "search_trace", "data": st})

        # ═══════════════════════════════════════════
        # 阶段3: 合议庭仲裁 (3仲裁官独立裁定→首席综合)
        # ═══════════════════════════════════════════
        await cb({"event": "agent_start", "agent": "jury",
                  "data": {"name": "合议庭·真相仲裁官", "status": "3位仲裁官独立裁决 → 首席综合裁定"}})

        di = {"text": text + kb_ctx + kb_hint,
              "malice_hypothesis": malice.get("malice_hypothesis", ""),
              "findings_360": fa, "findings_fc_search": fb, "findings_fc_scrape": fos}
        jr = await asyncio.gather(
            self.debater.run(di), self.debater.run(di), self.debater.run(di), return_exceptions=True)
        v1 = jr[0] if not isinstance(jr[0], Exception) else {"final_verdict": {"conclusion": "error", "confidence": 0}}
        v2 = jr[1] if not isinstance(jr[1], Exception) else {"final_verdict": {"conclusion": "error", "confidence": 0}}
        v3 = jr[2] if not isinstance(jr[2], Exception) else {"final_verdict": {"conclusion": "error", "confidence": 0}}

        await cb({"event": "jury_complete", "data": {"verdict_1": v1, "verdict_2": v2, "verdict_3": v3}})

        # 首席仲裁官综合三份独立裁定
        await cb({"event": "agent_start", "agent": "chief_judge",
                  "data": {"name": "首席仲裁官", "status": "综合合议庭意见最终裁定"}})
        di["jury_verdicts"] = json.dumps({"仲裁官1": v1, "仲裁官2": v2, "仲裁官3": v3}, ensure_ascii=False)
        debate = await self.debater.run(di)
        await cb({"event": "agent_complete", "agent": "debater", "data": debate})

        # ═══════════════════════════════════════════
        # 阶段4: 品质审核官
        # ═══════════════════════════════════════════
        await cb({"event": "agent_start", "agent": "publisher",
                  "data": {"name": "品质审核·发布官", "status": "证据链+认知处方+辟谣卡片"}})

        merged = {"claims": [], "overall_factual_score": debate.get("final_verdict", {}).get("confidence", 0.5),
                  "cross_validation_count": debate.get("cross_validation", {}).get("agreeing_sources", 0),
                  "investigation_notes": debate.get("debate_summary", ""),
                  "summary": f"事实核查: {fa.get('summary','')} | 深度挖掘: {fb.get('summary','')} | 来源: {fos.get('summary','')}"}
        evidence_chain = _build_evidence_chain(fa, fb, fos)
        pub = await self.publisher.run({"text": text, "malice_result": malice, "investigator_result": merged})
        await cb({"event": "agent_complete", "agent": "publisher", "data": pub})

        await cb({"event": "agent_start", "agent": "evaluator",
                  "data": {"name": "品质审核·发布官", "status": "4维质量自评中..."}})
        report = self.report_gen.generate(report_id=report_id, text=text, malice_result=malice,
                                           investigator_result=merged, publisher_result=pub, escalation="deep")
        evaluation = await self.publisher.self_evaluate(report)
        await cb({"event": "agent_complete", "agent": "evaluator", "data": evaluation})
        report["debate"] = debate
        report["evidence_chain"] = evidence_chain
        report["fingerprint"] = fp; report["behavior"] = behavior; report["motivation"] = motivation
        report["evolution"] = evolution; report["cognitive_warfare"] = cw; report["search_trace"] = st

        await cb({"event": "report", "data": report})
        self.knowledge.add_case(text=text, verdict=report.get("overall_verdict", "suspicious"),
                                 category=pub.get("category", "none"),
                                 evidence_summary=pub.get("one_sentence_verdict", ""),
                                 evil_score=malice.get("evil_score", 0.5), report=report)
        await cb({"event": "done", "data": {"message": "核查完成"}})
        return report


def _build_evidence_chain(f360: dict, ffc: dict, fos: dict) -> list[dict]:
    """从三路侦察兵取证结果构建证据链(供vis.js网络图)"""
    chain = []
    for agent_name, findings in [("360搜索", f360), ("Claude考证", ffc), ("来源验证", fos)]:
        for f in (findings.get("findings") or []):
            sources = f.get("sources") or []
            chain.append({
                "claim_text": f.get("claim", "")[:80],
                "verdict": f.get("verdict", "unverifiable"),
                "confidence": f.get("confidence", 0.5),
                "description": f.get("claim", "")[:80],
                "source": sources[0].get("title", "") if sources else "",
                "source_url": sources[0].get("url", "") if sources else "",
                "evidence": f.get("evidence", ""),
                "agent": agent_name,
            })
    return chain


def _build_search_trace(f360: dict, ffc: dict, fos: dict, debate: dict) -> dict:
    """提取真实搜索URL — 严格过滤假URL"""
    from urllib.parse import urlparse
    def valid(url):
        if not url or not (url.startswith("http://") or url.startswith("https://")): return False
        # 黑名单：明显的假URL
        fakes = ["example.com","localhost","127.0.0.1","internal","fake","test.com","placeholder","sample","xxx",
                 "your-domain","unknown","null","undefined","none"]
        if any(f in url.lower() for f in fakes): return False
        # 白名单：真实搜索引擎结果URL
        allowed = ["so.com/link","stats.gov.cn","pbc.gov.cn","moe.gov.cn","xinhuanet","people.com.cn",
                   "cctv.com","baidu.com","zhihu.com","sina.com","qq.com","163.com","imf.org","worldbank",
                   "wikipedia.org","gov.cn",".edu"]
        if not any(a in url.lower() for a in allowed):
            # 未知域名需要更严格的验证
            try:
                p = urlparse(url)
                if not p.netloc or '.' not in p.netloc or len(p.netloc) < 4: return False
            except: return False
        return True

    trace = {"agents": []}
    for name, findings in [("360搜索", f360), ("Firecrawl搜索", ffc), ("OpenOSINT验证", fos)]:
        at = {"name": name, "summary": (findings.get("summary") or "")[:120], "sources": []}
        seen = set()
        for f in (findings.get("findings") or []):
            for s in (f.get("sources") or []):
                url = (s.get("url") or "").strip()
                if not valid(url) or url in seen: continue
                seen.add(url)
                at["sources"].append({"title": (s.get("title") or "")[:120], "url": url,
                    "snippet": ((s.get("snippet") or s.get("content") or "")[:200]),
                    "verdict": f.get("verdict", ""), "verified": True})
        trace["agents"].append(at)
    return trace


def _enforce_year_tags(keywords: dict, text: str) -> dict:
    """硬约束: 从原始文本提取年份，自动补齐到所有搜索关键词(防LLM不服从提示词)"""
    import re
    years = re.findall(r'(20\d{2})\s*年', text)
    if not years:
        years = re.findall(r'\b(20\d{2})\b', text)
    if not years:
        return keywords

    primary_year = years[0]

    def _tag(kw_list: list[str]) -> list[str]:
        tagged = []
        for kw in kw_list:
            if not re.search(r'20\d{2}', kw):
                kw = f"{primary_year} {kw}"
            tagged.append(kw)
        return tagged

    return {
        "fact_check_keywords": _tag(keywords.get("fact_check_keywords", [])),
        "deep_search_keywords": _tag(keywords.get("deep_search_keywords", [])),
        "source_check_keywords": _tag(keywords.get("source_check_keywords", [])),
    }
