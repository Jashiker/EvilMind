"""认知战攻击模式库

基于国家安全视角，识别针对中国的4类认知战攻击模板。
与360安全大脑联动，提供舆情预警和攻击溯源能力。
"""

import re
from typing import Any

# ═══════════════════════════════════════════
# 4类认知战攻击模板
# ═══════════════════════════════════════════

ATTACK_TEMPLATES = {
    "systematic_trust_erosion": {
        "name": "系统性信任瓦解",
        "threat_level": "critical",
        "description": "通过持续散布'官方数据造假''政府无能'等信息，系统性地瓦解公众对制度的信任基础",
        "indicators": [
            r"都是假的", r"全是编的", r"谁也不信", r"没有真相",
            r"官方数据.*假", r"统计局.*骗", r"政府.*隐瞒",
            r"不让报道", r"被和谐", r"封锁消息",
        ],
        "origin_pattern": "通常首发于境外社交平台，经翻译后回流境内",
        "360_defense": "360安全大脑可标记此类信息的传播源头和扩散路径",
    },
    "economic_doom_narrative": {
        "name": "经济崩溃叙事",
        "threat_level": "critical",
        "description": "夸大经济数据负面变化，构建'中国经济即将崩溃'的虚假叙事框架",
        "indicators": [
            r"暴跌\d+%", r"崩盘", r"倒闭潮", r"失业率.*突破",
            r"GDP.*被.*超越", r"经济.*衰退", r"危机.*来临",
            r"房价.*暴跌", r"资本.*逃离", r"外资.*撤离",
        ],
        "origin_pattern": "常引用经过裁剪的国际机构数据，配上情绪化标题",
        "360_defense": "360搜索可交叉验证官方经济数据与实际报道的偏差",
    },
    "social_division_engineering": {
        "name": "社会分裂工程",
        "threat_level": "high",
        "description": "制造群体对立（贫富/地域/代际/性别），撕裂社会团结",
        "indicators": [
            r"年轻人.*躺平", r"富人.*穷人", r"底层.*权贵",
            r"他们.*我们", r"凭什么.*他们", r"老百姓.*被",
            r"关系户", r"走后门", r"不公平", r"特权",
        ],
        "origin_pattern": "利用真实社会问题，放大情绪渲染，添加虚假细节",
        "360_defense": "360浏览器可对涉群体对立的敏感内容进行标记预警",
    },
    "policy_sabotage": {
        "name": "政策破坏攻击",
        "threat_level": "high",
        "description": "伪造政府文件/通知，或歪曲解读政策，破坏公众对政策的信任和支持",
        "indicators": [
            r"教育部.*通知", r"国务院.*发布", r"央行.*宣布",
            r"红头文件", r"官方.*确认", r"定了！",
            r"取消.*政策", r"废除.*制度", r"全面.*实行",
        ],
        "origin_pattern": "伪造文件通常有格式不规范、文号错误等特征",
        "360_defense": "360安全大脑可对虚假官方通知进行格式验证和源头追踪",
    },
}


def detect_attack_patterns(text: str) -> dict[str, Any]:
    """检测输入文本是否匹配已知的认知战攻击模板

    Returns:
        {
            "matched_templates": [...],
            "threat_level": "critical/high/medium/low/none",
            "attack_surface": str,
            "360_recommendation": str,
        }
    """
    matched = []
    max_indicators = 0
    all_indicators_matched = []

    for template_id, template in ATTACK_TEMPLATES.items():
        hits = []
        for indicator in template["indicators"]:
            if re.search(indicator, text):
                hits.append(indicator.replace(r"\d+", "X").replace(r"\+", "").replace(r"\.?", "").replace(r".*", "...").strip("\\"))
        if hits:
            matched.append({
                "template_id": template_id,
                "name": template["name"],
                "threat_level": template["threat_level"],
                "description": template["description"],
                "matched_indicators": hits[:5],
                "hit_count": len(hits),
                "origin_pattern": template["origin_pattern"],
                "360_defense": template["360_defense"],
            })
            max_indicators = max(max_indicators, len(hits))
            all_indicators_matched.extend(hits)

    # 威胁等级
    if any(m["threat_level"] == "critical" for m in matched):
        threat = "critical"
    elif any(m["threat_level"] == "high" for m in matched):
        threat = "high"
    elif matched:
        threat = "medium"
    else:
        threat = "none"

    # 360联动建议
    if matched:
        recommendation = f"360安全大脑建议：已识别{len(matched)}种认知战攻击模式，建议启动深度溯源，追踪传播链路源头发起点。"
    else:
        recommendation = "未匹配已知认知战攻击模板，但仍需常规舆情监测。"

    return {
        "matched_templates": matched,
        "threat_level": threat,
        "template_count": len(matched),
        "attack_surface": "、".join(m["name"] for m in matched) if matched else "无明显攻击模式",
        "360_recommendation": recommendation,
        "indicators_total": len(set(all_indicators_matched)),
    }
