"""指纹官团队 — 5个专职Agent分工协作"""

from __future__ import annotations
import json, logging
from typing import Any
from agents.base import BaseAgent

logger = logging.getLogger(__name__)

# ── Agent 1: 指纹对比官 ──
FINGERPRINT_SYSTEM = """你是谣言指纹对比分析师。职责：
1. 提取14维指纹特征
2. 在知识库中匹配相似案例
3. 对比指纹相似度和特征重叠
4. 输出指纹对比报告"""

FINGERPRINT_PROMPT = """分析以下信息的指纹特征并与知识库对比：

信息: {text}
知识库参考: {kb_context}

输出JSON:
{{
  "agent": "指纹对比官",
  "fingerprint_matches": [{{"feature":"特征名","detected":true/false,"evidence":"原文证据"}}],
  "kb_similarity": {{"matched_cases":数量,"top_similarity":0.0-1.0}},
  "fingerprint_verdict": "该信息的指纹特征表明...",
  "risk_indicators": ["风险信号1","风险信号2"]
}}"""


# ── Agent 2: 进化树分析师 ──
EVOLUTION_SYSTEM = """你是谣言进化树分析师。职责：
1. 在知识库中追溯谣言的演变历史
2. 识别变异模式和传播路径
3. 分析谣言的时间演化特征"""

EVOLUTION_PROMPT = """分析以下信息在知识库中的进化关系：

信息: {text}
进化树数据: {evolution_context}

输出JSON:
{{
  "agent": "进化树分析师",
  "variant_count": 变体数量,
  "mutation_patterns": ["变异模式1","变异模式2"],
  "evolution_stage": "initial/mutated/adapted/resurgent",
  "evolution_analysis": "该谣言的进化特征分析..."
}}"""


# ── Agent 3: 意图挖掘官 ──
INTENT_SYSTEM = """你是认知意图深度挖掘分析师。职责：
1. 深入分析信息发布者的真实意图
2. 识别隐藏的认知操纵手法
3. 分析信息背后的心理战策略"""

INTENT_PROMPT = """深度挖掘以下信息的意图和认知操纵：

信息: {text}
行为分析: {behavior_context}
动机分析: {motivation_context}

输出JSON:
{{
  "agent": "意图挖掘官",
  "primary_intent": "主要意图(一段话)",
  "cognitive_manipulation_depth": "shallow/medium/deep",
  "hidden_agenda": ["隐藏议程1","隐藏议程2"],
  "target_cognitive_bias": ["攻击的认知偏差"],
  "psychological_warfare_tactic": "心理战术描述"
}}"""


# ── Agent 4: 风险评估官 ──
RISK_SYSTEM = """你是舆论风险评估分析师。职责：
1. 评估信息的舆论风险等级
2. 预测可能的社会影响
3. 评估传播扩散风险"""

RISK_PROMPT = """评估以下信息的舆论风险：

信息: {text}
指纹分析: {fingerprint_context}
意图分析: {intent_context}
攻击维度: {attack_dimensions}

输出JSON:
{{
  "agent": "风险评估官",
  "public_opinion_risk": "critical/high/medium/low",
  "spread_potential": "极强/强/中/弱",
  "social_impact": ["可能的社会影响1","影响2"],
  "vulnerable_groups": ["易受影响群体"],
  "urgency_level": "立即处置/重点关注/常规监控/低优先级",
  "mitigation_suggestion": "处置建议"
}}"""


# ── Agent 5: 综合研判官 ──
SYNTHESIS_SYSTEM = """你是指纹研判综合官。4位专家已完成各自分析，请综合他们的发现形成统一研判报告。"""

SYNTHESIS_PROMPT = """综合4位专家的分析，形成统一研判：

信息: {text}

===== 指纹对比官 =====
{fingerprint_result}

===== 进化树分析师 =====
{evolution_result}

===== 意图挖掘官 =====
{intent_result}

===== 风险评估官 =====
{risk_result}

请输出综合研判JSON(格式与恶意假设官相同):
{{
  "evil_score": 0.0-1.0,
  "escalation": "deep",
  "malice_hypothesis": "综合研判的恶意假设",
  "attack_dimensions": {{"political_stability":0.0,"economic_confidence":0.0,"social_cohesion":0.0,"institutional_trust":0.0}},
  "primary_attack": "主要攻击维度",
  "thinking_visible": "研判思考过程",
  "likely_category": "最可能的操纵手法",
  "synthesis_summary": "综合研判摘要",
  "search_keywords": {{
    "fact_check_keywords": ["百度360搜索关键词1","关键词2"],
    "deep_search_keywords": ["深度搜索Firecrawl词1","词2"],
    "source_check_keywords": ["来源域名验证词1","词2"]
  }}
}}

search_keywords 必须包含:
- fact_check_keywords: 2-3组搜事实核查关键词(用于360搜索)，包含官方数据源如"国家统计局""央行""教育部"，每组必须包含信息中涉及的年份或日期
- deep_search_keywords: 2-3组深度搜索词(用于Claude CLI)，聚焦具体政策/数据/事件名称，必须包含年份
- source_check_keywords: 2-3组来源验证词(用于OpenOSINT)，提取信息中声称的机构名/域名
每组关键词4-12字，精准简洁，可直接作为搜索引擎输入。务必包含信息中的具体年份。"""


# ── Agent Classes ──

class FingerprintVerifier(BaseAgent):
    """指纹对比官 — 14维指纹提取与知识库匹配"""
    async def run(self, input_data: dict) -> dict:
        text = input_data["text"]
        kb = input_data.get("kb_context", "")
        try:
            raw = await self.llm.chat_json(prompt=FINGERPRINT_PROMPT.format(text=text, kb_context=kb), system=FINGERPRINT_SYSTEM)
        except Exception as e:
            raw = {"agent": "指纹对比官", "fingerprint_verdict": f"分析失败: {e}"}
        return raw


class EvolutionAnalyst(BaseAgent):
    """进化树分析师 — 谣言变异溯源"""
    async def run(self, input_data: dict) -> dict:
        text = input_data["text"]
        evo = input_data.get("evolution_context", "")
        try:
            raw = await self.llm.chat_json(prompt=EVOLUTION_PROMPT.format(text=text, evolution_context=evo), system=EVOLUTION_SYSTEM)
        except Exception as e:
            raw = {"agent": "进化树分析师", "evolution_analysis": f"分析失败: {e}"}
        return raw


class IntentMiner(BaseAgent):
    """意图挖掘官 — 认知操纵深度分析"""
    async def run(self, input_data: dict) -> dict:
        text = input_data["text"]
        beh = input_data.get("behavior_context", "")
        mot = input_data.get("motivation_context", "")
        try:
            raw = await self.llm.chat_json(prompt=INTENT_PROMPT.format(text=text, behavior_context=beh, motivation_context=mot), system=INTENT_SYSTEM)
        except Exception as e:
            raw = {"agent": "意图挖掘官", "primary_intent": f"分析失败: {e}"}
        return raw


class RiskAssessor(BaseAgent):
    """风险评估官 — 舆情风险分级"""
    async def run(self, input_data: dict) -> dict:
        text = input_data["text"]
        fp = input_data.get("fingerprint_context", "")
        it = input_data.get("intent_context", "")
        ad = input_data.get("attack_dimensions", "")
        try:
            raw = await self.llm.chat_json(prompt=RISK_PROMPT.format(text=text, fingerprint_context=fp, intent_context=it, attack_dimensions=ad), system=RISK_SYSTEM)
        except Exception as e:
            raw = {"agent": "风险评估官", "public_opinion_risk": f"分析失败: {e}"}
        return raw


class SynthesisJudge(BaseAgent):
    """综合研判官 — 恶意评分 + 关键词提炼"""
    async def run(self, input_data: dict) -> dict:
        text = input_data["text"]
        fp = json.dumps(input_data.get("fingerprint_result", {}), ensure_ascii=False)
        ev = json.dumps(input_data.get("evolution_result", {}), ensure_ascii=False)
        it = json.dumps(input_data.get("intent_result", {}), ensure_ascii=False)
        ri = json.dumps(input_data.get("risk_result", {}), ensure_ascii=False)
        try:
            raw = await self.llm.chat_json(
                prompt=SYNTHESIS_PROMPT.format(text=text, fingerprint_result=fp[:1500], evolution_result=ev[:1000], intent_result=it[:1500], risk_result=ri[:1500]),
                system=SYNTHESIS_SYSTEM)
        except Exception as e:
            raw = {"evil_score": 0.5, "malice_hypothesis": f"研判失败: {e}"}
        return raw
