"""OpenOSINT 集成 — 信息来源验证

集成场景:
- 核查"官方通知"类谣言时验证声称的域名是否真实
- 评估信息源的权威性(.gov.cn / 官方媒体 / 未知来源)
- 为搜索溯源提供额外的来源可信度评分
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# 已知官方域名和可信媒体
OFFICIAL_DOMAINS = [
    '.gov.cn', 'stats.gov.cn', 'pbc.gov.cn', 'moe.gov.cn', 'mca.gov.cn',
    'nhc.gov.cn', 'mofcom.gov.cn', 'customs.gov.cn', 'mfa.gov.cn',
    'mod.gov.cn', 'most.gov.cn', 'mwr.gov.cn', 'ndrc.gov.cn',
]
TRUSTED_MEDIA = [
    'xinhuanet.com', 'people.com.cn', 'cctv.com', 'chinanews.com',
    'gmw.cn', 'youth.cn', 'chinadaily.com.cn', 'peopledaily.com.cn',
]
ACADEMIC_SOURCES = ['.edu.cn', '.ac.cn', 'cnki.net']


def verify_source_credibility(url_or_domain: str) -> dict:
    """评估信息来源的可信度

    Returns:
        {"domain": str, "tier": "official"|"trusted_media"|"academic"|"unknown",
         "score": 0-100, "is_gov": bool, "verified": bool}
    """
    # 提取域名
    domain = url_or_domain
    if '://' in domain:
        domain = urlparse(domain).netloc or domain
    domain = domain.lower().strip()

    result = {"domain": domain, "tier": "unknown", "score": 30, "is_gov": False, "verified": False}

    # Tier 1: 政府官方
    if any(domain.endswith(d) or d in domain for d in OFFICIAL_DOMAINS):
        result["tier"] = "official"
        result["score"] = 95
        result["is_gov"] = True
        result["verified"] = True
        return result

    # Tier 2: 官方媒体
    if any(d in domain for d in TRUSTED_MEDIA):
        result["tier"] = "trusted_media"
        result["score"] = 80
        result["verified"] = True
        return result

    # Tier 3: 学术来源
    if any(domain.endswith(d) or d in domain for d in ACADEMIC_SOURCES):
        result["tier"] = "academic"
        result["score"] = 65
        result["verified"] = True
        return result

    # Tier 4: 通用域名(有常见TLD，基本可信)
    if any(domain.endswith(t) for t in ['.com', '.cn', '.org', '.net', '.com.cn', '.org.cn']):
        result["tier"] = "commercial"
        result["score"] = 35
        result["verified"] = True
        return result

    # 尝试 OpenOSINT WHOIS 验证
    try:
        from openosint.tools.search_whois import lookup
        whois_data = lookup(domain)
        if whois_data:
            result["verified"] = True
            result["score"] = 40
            result["whois"] = str(whois_data)[:300]
            logger.info(f"OpenOSINT WHOIS: {domain} 已验证")
    except Exception:
        pass

    return result


# ============================================================
# DeepSeek function calling 工具定义
# ============================================================

OPENOSINT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "verify_source_credibility",
            "description": "验证信息来源域名的可信度等级。用于核查'官方通知''政府文件'类信息时，判断声称的来源是否真实可信。返回tier等级(official/trusted_media/academic/commercial/unknown)和可信度评分(0-100)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "url_or_domain": {
                        "type": "string",
                        "description": "要验证的URL或域名，如'https://stats.gov.cn/xxx'或'stats.gov.cn'"
                    }
                },
                "required": ["url_or_domain"],
            },
        },
    },
]


async def execute_openosint_tool(name: str, arguments: dict) -> str:
    """执行 OpenOSINT 工具(同步包装为异步)"""
    import json
    if name == "verify_source_credibility":
        url = arguments.get("url_or_domain", "")
        if not url:
            return json.dumps({"error": "未提供URL或域名"}, ensure_ascii=False)
        result = verify_source_credibility(url)
        logger.info(f"来源验证: {result['domain']} → {result['tier']} (score:{result['score']})")
        return json.dumps(result, ensure_ascii=False, indent=2)
    return json.dumps({"error": f"未知工具: {name}"})
