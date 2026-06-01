"""辩论合成 Agent — 汇总多路调查结果，通过讨论辩论达成共识"""

from __future__ import annotations

import json
import logging
from typing import Any

from agents.base import BaseAgent

logger = logging.getLogger(__name__)

DEBATE_SYSTEM = """你是真相调查的首席编辑。3个独立调查员各自完成了调查，现在由你主持讨论并达成共识。

⚠️ 严格规则:
1. 只使用调查员提供的真实搜索证据
2. 绝对禁止编造来源URL或引用不存在的证据
3. 交叉验证必须基于实际搜索结果
4. 证据不足时必须标注"证据不足"，严禁臆断
5. 每个结论必须有至少1个可验证来源支撑

你的工作：
1. 仔细对比3路调查结果
2. 找出证据一致的地方 → 这些是确定结论
3. 找出证据矛盾的地方 → 分析谁更可信
4. 找出单一来源的发现 → 标注可信度降低
5. 综合所有证据，给出最终判定

辩论原则：
- 交叉验证优先：2个以上独立来源支持的结论可信度高
- 官方数据优先：.gov.cn 来源 > 媒体报道 > 单一来源
- 证据不足就明确说"证据不足"
- 如果3路调查都没找到确凿证据，降低置信度
"""

DEBATE_PROMPT = """请主持以下3路调查结果的辩论：

原始信息：{text}
恶意假设：{malice}

===== 调查员1: 360搜索引擎 =====
{findings_360}

===== 调查员2: Firecrawl搜索 =====
{findings_fc_search}

===== 调查员3: Firecrawl抓取 =====
{findings_fc_scrape}

===== 第二轮: 交叉审查(各Agent拿到他人发现后的验证) =====

===== 360搜索交叉审查 =====
{cross_360}

===== Firecrawl交叉审查 =====
{cross_fc}

===== OpenOSINT交叉审查 =====
{cross_osint}

请进行辩论分析并输出JSON：

{{
  "debate_summary": "一段话总结3路调查的辩论过程",
  "consensus": {{
    "confirmed": ["多方证据一致确认的事实"],
    "disputed": ["证据存在矛盾的发现"],
    "single_source": ["只有一个来源支持的发现"]
  }},
  "cross_validation": {{
    "total_sources": 独立信源总数,
    "agreeing_sources": 相互印证的信源数,
    "quality": "high/medium/low"
  }},
  "final_verdict": {{
    "conclusion": "true/false/manipulative/unverifiable",
    "confidence": 0.0-1.0（综合3路调查后的置信度）,
    "reasoning": "综合判定理由"
  }},
  "key_evidence_chain": [
    {{"step":1, "from":"360搜索/Firecrawl搜索/Firecrawl抓取", "evidence":"证据内容", "strength":"strong/medium/weak"}}
  ]
}}"""


class JuryDeliberator(BaseAgent):
    """辩论合成官 — 多路调查结果对比辩论"""

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        text = input_data["text"]
        malice = input_data.get("malice_hypothesis", "")
        findings_360 = json.dumps(input_data.get("findings_360", {}), ensure_ascii=False, indent=2)
        findings_fc_search = json.dumps(input_data.get("findings_fc_search", {}), ensure_ascii=False, indent=2)
        findings_fc_scrape = json.dumps(input_data.get("findings_fc_scrape", {}), ensure_ascii=False, indent=2)
        cross_360 = json.dumps(input_data.get("cross_360", {}), ensure_ascii=False, indent=2)
        cross_fc = json.dumps(input_data.get("cross_fc", {}), ensure_ascii=False, indent=2)
        cross_osint = json.dumps(input_data.get("cross_osint", {}), ensure_ascii=False, indent=2)
        jury_verdicts = input_data.get("jury_verdicts", "")

        # 首席仲裁官模式：综合合议庭意见
        if jury_verdicts:
            prompt = f"""你是首席仲裁官。3位仲裁官已完成独立审议，请综合他们的意见达成最终裁定。

原始信息: {text[:500]}
恶意假设: {malice[:300]}
3位仲裁官独立裁定:
{jury_verdicts[:2000]}

请输出最终裁定JSON(格式与标准辩论相同)。"""
            logger.info("[Chief Judge] 综合合议庭意见...")
        else:
            prompt = DEBATE_PROMPT.format(
                text=text, malice=malice,
                findings_360=findings_360[:1500],
                findings_fc_search=findings_fc_search[:1500],
                findings_fc_scrape=findings_fc_scrape[:1500],
                cross_360=cross_360[:1000],
                cross_fc=cross_fc[:1000],
                cross_osint=cross_osint[:1000],
            )
            logger.info("[Debate] 开始3路辩论...")

        try:
            result = await self.llm.chat_json(
                prompt=prompt,
                system=DEBATE_SYSTEM,
            )
        except Exception as e:
            logger.warning(f"[Debate] 失败: {e}")
            result = {
                "debate_summary": f"辩论未完成: {e}",
                "consensus": {"confirmed": [], "disputed": [], "single_source": []},
                "cross_validation": {"total_sources": 0, "agreeing_sources": 0, "quality": "low"},
                "final_verdict": {"conclusion": "unverifiable", "confidence": 0.3, "reasoning": "辩论失败"},
                "key_evidence_chain": [],
            }

        logger.info(f"[Debate] 完成: {result.get('final_verdict', {}).get('conclusion', '?')} "
                     f"confidence={result.get('final_verdict', {}).get('confidence', 0):.0%}")
        return result
