"""OpenOSINT 调查Agent — 来源验证与域名溯源"""

from __future__ import annotations

import json, logging
from typing import Any
from agents.base import BaseAgent

logger = logging.getLogger(__name__)

SYSTEM_OSINT = """你是OpenOSINT来源验证调查员，专门核查信息来源的真实性和权威性。

工具: verify_source_credibility(url_or_domain) — 验证域名/URL的可信度等级

工作方式:
1. 指纹官已提炼来源验证关键词（机构名/域名），逐一用 verify_source_credibility 验证
2. 判断来源是政府官方/可信媒体/学术来源/商业网站/未知来源
3. 输出每个来源的可信度评分

原则:
- .gov.cn 域名 → official(95分)
- 新华社/人民日报/央视等 → trusted_media(80分)
- 未知域名 → 低分需标注风险
"""

PROMPT_OSINT = """请验证以下信息中声称的来源是否可信。

信息: {text}
恶意假设: {malice}
来源验证关键词: {keywords}

请对每个来源逐一验证其可信度。

输出JSON:
{{
  "agent": "OpenOSINT来源验证",
  "findings": [
    {{
      "claim": "信息中声称的来源（对应验证的关键词）",
      "verdict": "true/false/unverifiable",
      "source_domain": "域名",
      "credibility_tier": "official/trusted_media/academic/commercial/unknown",
      "credibility_score": 0-100,
      "evidence": "验证结果说明",
      "sources": [{{"title":"可信度验证","url":"","snippet":""}}],
      "confidence": 0.0-1.0
    }}
  ],
  "summary": "一句话总结来源可信度",
  "key_evidence": "最关键的可信度发现"
}}"""


class OpenOSINTAgent(BaseAgent):
    """来源可信度验证侦察兵 — 域名/机构权威性评估"""

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        text = input_data["text"]
        malice = input_data.get("malice_hypothesis", "")
        tools = input_data.get("tools_osint", [])
        executor = input_data.get("tool_executor")
        keywords_osint = input_data.get("keywords_osint", [])

        logger.info("[OSINT Agent] 开始来源验证...")

        kws = "\n".join(f"- {kw}" for kw in keywords_osint) if keywords_osint else "（无关键词，请从信息中提取）"
        step1_prompt = f"请验证以下信息中声称的来源域名是否可信。指纹官已提炼来源验证关键词，请逐一验证：\n\n信息: {text}\n恶意假设: {malice}\n来源验证关键词:\n{kws}\n\n每个关键词对应一个来源，逐一验证。"

        search_raw = ""
        try:
            search_raw = await self.llm.chat_with_tools(
                prompt=step1_prompt,
                system=SYSTEM_OSINT,
                tools=tools,
                tool_executor=executor,
                max_rounds=len(keywords_osint) if keywords_osint else 2,
            )
        except Exception as e:
            logger.warning(f"[OSINT Agent] 搜索失败: {e}")
            search_raw = f"搜索失败: {e}"

        try:
            result = await self.llm.chat_json(
                prompt=PROMPT_OSINT.format(text=text, malice=malice,
                                           keywords=", ".join(keywords_osint) if keywords_osint else "无")
                       + f"\n\n验证原始结果:\n{search_raw[:2000]}",
                system=SYSTEM_OSINT + "\n请基于验证结果整理JSON输出。",
            )
        except Exception as e:
            logger.warning(f"[OSINT Agent] JSON失败: {e}")
            result = {"agent": "OpenOSINT来源验证", "findings": [], "summary": f"JSON整理失败: {e}", "key_evidence": search_raw[:200]}

        logger.info(f"[OSINT Agent] 完成: {len(result.get('findings', []))} 个发现")
        return result
