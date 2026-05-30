"""谣言进化树 + 行为分析 + 动机分析

基于知识库构建谣言的演化关系图谱。
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from knowledge.fingerprint import extract_fingerprint, FINGERPRINT_DIMS

logger = logging.getLogger(__name__)


def build_evolution_tree(text: str, knowledge_store, max_variants: int = 20) -> dict:
    """构建谣言进化树

    从知识库中找到与输入相关的谣言及其变体，
    按发表时间排序，展示谣言的演变路径。

    Returns:
        {
            "root": {...},        # 最原始的版本
            "variants": [...],     # 所有变体
            "edges": [...],        # 进化关系
            "mutation_patterns": [...],  # 变异模式
        }
    """
    from knowledge.store import _similarity

    fp = extract_fingerprint(text)
    target_features = {k for k, v in fp["features"].items() if v}

    # 在知识库中找相似谣言
    variants = []
    for case_id, case in knowledge_store._cases.items():
        case_text = case.get("text", "")
        text_sim = _similarity(text, case_text)

        case_fp = extract_fingerprint(case_text)
        case_features = {k for k, v in case_fp["features"].items() if v}

        # 特征 Jaccard 相似度
        intersection = target_features & case_features
        union = target_features | case_features
        feature_sim = len(intersection) / len(union) if union else 0

        # 综合相似度
        combined_sim = text_sim * 0.4 + feature_sim * 0.6

        if combined_sim > 0.15:
            variants.append({
                "id": case_id,
                "text": case_text[:120],
                "category": case.get("category", ""),
                "verdict": case.get("verdict", ""),
                "date": case.get("date", ""),
                "evil_score": case.get("evil_score", 0),
                "text_similarity": round(text_sim, 3),
                "feature_similarity": round(feature_sim, 3),
                "combined_similarity": round(combined_sim, 3),
                "features": list(case_features & target_features)[:5],
            })

    # 按综合相似度排序
    variants.sort(key=lambda v: v["combined_similarity"], reverse=True)
    variants = variants[:max_variants]

    # 找到根节点（最早的）
    dated = [v for v in variants if v["date"]]
    root = min(dated, key=lambda v: v["date"]) if dated else (variants[0] if variants else None)

    # 构建进化边（按时间+相似度连接）
    edges = []
    sorted_by_date = sorted([v for v in variants if v["date"]], key=lambda v: v["date"])
    for i in range(len(sorted_by_date) - 1):
        if sorted_by_date[i + 1]["combined_similarity"] > 0.3:
            edges.append({
                "from": sorted_by_date[i]["id"],
                "to": sorted_by_date[i + 1]["id"],
                "type": "evolution",
            })

    # 分析变异模式
    mutation_patterns = _analyze_mutations(variants, fp)

    return {
        "root": root,
        "variants": variants,
        "edges": edges[:15],
        "total_variants_found": len(variants),
        "mutation_patterns": mutation_patterns,
        "input_fingerprint": {
            "feature_count": fp["feature_count"],
            "risk_level": fp["risk_level"],
            "dominant_category": fp["dominant_category"],
            "active_features": list(target_features)[:8],
        },
    }


def _analyze_mutations(variants: list, input_fp: dict) -> list[dict]:
    """分析谣言的变异模式"""
    patterns = []

    if len(variants) < 2:
        return patterns

    # 类别变化
    categories = [v["category"] for v in variants if v["category"]]
    if len(set(categories)) > 1:
        patterns.append({"type": "category_shift", "from": categories[0], "to": categories[-1], "description": "谣言在传播中切换了操纵手法"})

    # 特征数量变化
    if len(variants) >= 2:
        scores = [v["evil_score"] for v in variants]
        if max(scores) - min(scores) > 0.3:
            patterns.append({"type": "intensity_change", "min_score": min(scores), "max_score": max(scores), "description": "谣言在传播中邪恶程度发生了显著变化"})

    # 多版本并存
    categories_count = defaultdict(int)
    for v in variants:
        categories_count[v["category"]] += 1
    top_cats = sorted(categories_count.items(), key=lambda x: x[1], reverse=True)[:3]
    patterns.append({"type": "multi_strain", "categories": [c[0] for c in top_cats], "description": f"谣言存在多个变种，分布在不同类别中"})

    return patterns


def analyze_behavior(text: str, fingerprint: dict | None = None) -> dict:
    """分析谣言的行为模式

    Returns:
        {
            "manipulation_style": str,     # 操纵风格
            "cognitive_targets": [str],    # 攻击的认知弱点
            "spread_mechanism": str,       # 传播机制
            "emotional_levers": [str],     # 情感杠杆
        }
    """
    if fingerprint is None:
        fingerprint = extract_fingerprint(text)

    features = fingerprint["features"]
    fp = fingerprint

    # 操纵风格
    if features.get("has_extreme_numbers") and features.get("has_emotional_trigger"):
        style = "数据+情绪双杀：用极端数字冲击理性，用情绪绕过验证"
    elif features.get("has_authority_claim") and features.get("has_urgency_call"):
        style = "权威绑架+制造紧迫：假借官方名义催促行动"
    elif features.get("has_total_negation") or features.get("has_conspiracy_hint"):
        style = "信任腐蚀：系统性瓦解信息信任基础"
    elif features.get("has_visual_description") and features.get("has_vague_time_place"):
        style = "叙事移植：用真实素材构建虚假故事"
    else:
        style = "混合操纵：综合运用多种手法"

    # 认知目标
    cognitive_targets = []
    if features.get("has_extreme_numbers"): cognitive_targets.append("锚定效应")
    if features.get("has_emotional_trigger"): cognitive_targets.append("情绪启发式")
    if features.get("has_authority_claim"): cognitive_targets.append("权威偏见")
    if features.get("has_identity_binding"): cognitive_targets.append("群体认同")
    if features.get("has_health_fear"): cognitive_targets.append("生存本能恐惧")
    if features.get("has_moral_judgment"): cognitive_targets.append("道德义愤")
    if features.get("has_conspiracy_hint"): cognitive_targets.append("模式寻求本能")

    # 传播机制
    if features.get("has_call_to_action") and features.get("has_urgency_call"):
        mechanism = "社交裂变：通过'求转发'实现指数级扩散"
    elif features.get("has_emotional_trigger") and features.get("has_identity_binding"):
        mechanism = "群体共振：利用身份认同触发圈层传播"
    elif features.get("has_authority_claim"):
        mechanism = "信任传递：假借权威背书降低质疑"
    else:
        mechanism = "信息级联：通过多次曝光制造'多数人相信'的假象"

    # 情感杠杆
    emotional_levers = []
    if features.get("has_emotional_trigger"): emotional_levers.append("愤怒/恐惧/同情")
    if features.get("has_health_fear"): emotional_levers.append("生存焦虑")
    if features.get("has_moral_judgment"): emotional_levers.append("道德义愤")
    if features.get("has_us_vs_them"): emotional_levers.append("群体对立")
    if features.get("has_identity_binding"): emotional_levers.append("身份焦虑")

    return {
        "manipulation_style": style,
        "cognitive_targets": cognitive_targets or ["综合认知偏差"],
        "spread_mechanism": mechanism,
        "emotional_levers": emotional_levers or ["综合情绪触发"],
        "virality_score": min(1.0, fp["feature_count"] / 10),
        "behavior_summary": f"该谣言通过{mechanism}进行传播，主要攻击{'、'.join(cognitive_targets[:3])}等认知弱点。",
    }


def analyze_motivation(text: str, fingerprint: dict | None = None, malice_hypothesis: str = "") -> dict:
    """分析谣言的创作动机

    Returns:
        {
            "primary_motive": str,
            "motive_category": str,
            "intended_audience": str,
            "desired_effect": str,
            "beneficiary": str,
        }
    """
    if fingerprint is None:
        fingerprint = extract_fingerprint(text)

    features = fingerprint["features"]
    category = fingerprint.get("dominant_category", "none")

    # 动机分类
    motive_map = {
        "data_fabrication": {
            "primary": "数据操纵：通过伪造/篡改数据制造虚假现实感",
            "category": "认知战",
            "effect": "让受众接受虚假的'事实基础'，动摇对真实数据的信任",
            "beneficiary": "试图影响特定议题舆论方向的组织或个人",
        },
        "emotion_hijack": {
            "primary": "情绪操纵：利用强烈情绪绕过受众的理性判断",
            "category": "心理战",
            "effect": "制造群体性情绪反应（愤怒/恐慌/同情），驱动非理性行为",
            "beneficiary": "追求流量/关注的传播者，或试图制造社会情绪动荡的力量",
        },
        "narrative_transplant": {
            "primary": "叙事嫁接：将真实素材植入虚假背景，制造可信度更高的谎言",
            "category": "信息战",
            "effect": "利用'眼见为实'的认知偏差，让虚假叙事更难被识破",
            "beneficiary": "有组织的信息操纵者",
        },
        "authority_fake": {
            "primary": "权威劫持：伪造官方/专家身份，利用公众对权威的信任传播谎言",
            "category": "信任攻击",
            "effect": "直接损害公众对政府/专业机构的信任",
            "beneficiary": "试图瓦解制度信任的对立力量",
        },
        "trust_corrosion": {
            "primary": "信任瓦解：系统性否定一切信息源，制造认知瘫痪",
            "category": "认知战",
            "effect": "让受众进入'什么都不信'的虚无状态，丧失判断力",
            "beneficiary": "试图颠覆社会信息秩序的力量",
        },
        "selective_feeding": {
            "primary": "信息截流：选择性呈现部分真相，制造虚假整体印象",
            "category": "认知偏误利用",
            "effect": "让受众基于不完整信息做出错误判断",
            "beneficiary": "试图引导舆论朝向特定方向的信息操纵者",
        },
    }

    motive = motive_map.get(category, {
        "primary": "混合动机：综合运用多种操纵手法",
        "category": "综合信息操纵",
        "effect": "降低受众信息辨别能力",
        "beneficiary": "未知",
    })

    # 受众和目标
    audience_hints = {
        "has_identity_binding": "特定身份群体（如年轻人、家长、老年人）",
        "has_health_fear": "关注健康的普通公众",
        "has_call_to_action": "容易被动员的社交网络活跃用户",
        "has_conspiracy_hint": "对主流叙事持怀疑态度的群体",
    }
    audiences = [v for k, v in audience_hints.items() if features.get(k)]
    intended_audience = "；".join(audiences) if audiences else "普通公众"

    return {
        "primary_motive": motive["primary"],
        "motive_category": motive["category"],
        "intended_audience": intended_audience,
        "desired_effect": motive["effect"],
        "beneficiary": motive["beneficiary"],
        "motive_summary": f"动机分类：{motive['category']} | 目标受众：{intended_audience} | 目的：{motive['effect']}",
    }
