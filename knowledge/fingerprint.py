"""谣言指纹特征提取 — 基于知识库构建谣言模式识别

从已核查案例中提取14维指纹特征，用于快速识别和匹配谣言模式。
"""

from __future__ import annotations

import re
import logging
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)

# ============================================================
# 14维谣言指纹特征
# ============================================================

FINGERPRINT_DIMS = [
    "has_extreme_numbers",      # 包含极端数字（暴跌90%、突破30%等）
    "has_urgency_call",         # 包含紧急呼吁（紧急扩散、求转发、速看）
    "has_emotional_trigger",    # 包含情绪触发词（愤怒、泪目、震惊、可怕）
    "has_authority_claim",      # 声称来自权威（央视报道、官方通知、专家说）
    "has_identity_binding",     # 身份绑定（年轻人、父母、中国人、作为XX你必须）
    "has_visual_description",   # 画面感描述（排长队、血淋淋、哭成一片）
    "has_conspiracy_hint",      # 阴谋暗示（背后、黑幕、掩盖、不让说）
    "has_total_negation",       # 全称否定（都是假的、没有真相、谁也不信）
    "has_vague_time_place",     # 模糊时空（某地、近日、据说、网传）
    "has_call_to_action",       # 行动号召（转起来、让更多人看到、必须曝光）
    "has_numeric_claim",        # 包含具体数据声明
    "has_moral_judgment",       # 道德评判（无耻、天理难容、丧尽天良）
    "has_us_vs_them",           # 对立叙事（他们vs我们、底层vs权贵）
    "has_health_fear",          # 健康恐慌（致癌、有毒、超标、辐射）
]

# 特征关键词词典
FEATURE_KEYWORDS = {
    "has_extreme_numbers": [
        r"暴跌\d+%", r"暴涨\d+%", r"突破\d+", r"不足\d*\.?\d+%", r"超过\d+%",
        r"\d+倍", r"暴跌", r"狂跌", r"飙升", r"崩盘", r"断崖式",
    ],
    "has_urgency_call": [
        r"紧急扩散", r"求转发", r"速看", r"马上删", r"快看", r"再不.*就",
        r"紧急通知", r"赶紧", r"立刻", r"马上", r"火速",
    ],
    "has_emotional_trigger": [
        r"愤怒", r"泪目", r"震惊", r"可怕", r"吓人", r"恐怖", r"惨",
        r"看哭", r"心碎", r"崩溃", r"疯传", r"不敢相信", r"气死",
    ],
    "has_authority_claim": [
        r"央视", r"官方", r"通知", r"发布", r"规定", r"文件", r"宣布",
        r"专家", r"院士", r"教授", r"医生", r"医院", r"教育部", r"央行",
        r"国务院", r"政府", r"公安部", r"确认", r"证实",
    ],
    "has_identity_binding": [
        r"年轻人", r"父母", r"中国人", r"作为.*必须", r"是中国人就",
        r"家长", r"孩子", r"老人", r"女性", r"打工人", r"老百姓",
    ],
    "has_visual_description": [
        r"排长队", r"血淋淋", r"哭成一片", r"满地", r"亲眼", r"监控",
        r"现场", r"画面", r"截图", r"视频",
    ],
    "has_conspiracy_hint": [
        r"背后", r"黑幕", r"掩盖", r"隐瞒", r"不让说", r"内幕", r"真相",
        r"不能说", r"被封杀", r"被删", r"被和谐",
    ],
    "has_total_negation": [
        r"都是假的", r"没有真相", r"谁也不信", r"全都.*假", r"没有一个",
        r"别信", r"不可信", r"编的", r"骗人", r"不要相信",
    ],
    "has_vague_time_place": [
        r"某地", r"近日", r"据说", r"网传", r"爆料", r"有消息称",
        r"据知情", r"听说", r"据说", r"传.*消息",
    ],
    "has_call_to_action": [
        r"转起来", r"让更多人看到", r"必须曝光", r"扩散", r"转起来",
        r"顶起来", r"转发", r"分享", r"接力",
    ],
    "has_numeric_claim": [
        r"\d+万", r"\d+亿", r"\d+%", r"\d+倍", r"\d+人",
        r"\d+元", r"\d+年", r"\d+月\d+日",
    ],
    "has_moral_judgment": [
        r"无耻", r"天理难容", r"丧尽天良", r"人渣", r"败类",
        r"不得好死", r"罪该万死", r"禽兽", r"丧心病狂",
    ],
    "has_us_vs_them": [
        r"他们", r"我们老百姓", r"底层", r"权贵", r"富人", r"穷人",
        r"当官的", r"资本家", r"既得利益", r"官商勾结",
    ],
    "has_health_fear": [
        r"致癌", r"有毒", r"超标", r"辐射", r"感染", r"病毒",
        r"细菌", r"污染", r"白血病", r"癌症", r"畸形", r"猝死",
    ],
}


def extract_fingerprint(text: str) -> dict[str, Any]:
    """从文本中提取14维谣言指纹特征

    Returns:
        {
            "features": {feature_name: bool},
            "feature_count": int,        # 命中特征数
            "risk_level": "high/medium/low",
            "matched_keywords": [str],   # 命中的具体关键词
            "dominant_category": str,     # 主导分类
        }
    """
    features = {}
    matched_keywords = []
    category_scores = {
        "data_fabrication": 0,
        "emotion_hijack": 0,
        "narrative_transplant": 0,
        "authority_fake": 0,
        "trust_corrosion": 0,
        "selective_feeding": 0,
    }

    for feat_name in FINGERPRINT_DIMS:
        patterns = FEATURE_KEYWORDS.get(feat_name, [])
        matched = False
        for pat in patterns:
            if re.search(pat, text):
                matched = True
                matched_keywords.append(pat.replace(r"\d+", "X").replace(r"\+", "").replace(r"\.?", "").replace(r"\w", "").strip("\\"))
                break
        features[feat_name] = matched

    # 特征 → 分类映射
    feature_to_category = {
        "has_extreme_numbers": "data_fabrication",
        "has_numeric_claim": "data_fabrication",
        "has_urgency_call": "emotion_hijack",
        "has_emotional_trigger": "emotion_hijack",
        "has_health_fear": "emotion_hijack",
        "has_call_to_action": "emotion_hijack",
        "has_moral_judgment": "emotion_hijack",
        "has_visual_description": "narrative_transplant",
        "has_vague_time_place": "narrative_transplant",
        "has_authority_claim": "authority_fake",
        "has_total_negation": "trust_corrosion",
        "has_conspiracy_hint": "trust_corrosion",
        "has_us_vs_them": "trust_corrosion",
        "has_identity_binding": "selective_feeding",
    }

    for feat, matched in features.items():
        if matched and feat in feature_to_category:
            category_scores[feature_to_category[feat]] += 1

    feature_count = sum(1 for v in features.values() if v)
    risk_level = "high" if feature_count >= 6 else "medium" if feature_count >= 3 else "low"

    # 主导分类
    dominant = max(category_scores, key=category_scores.get) if max(category_scores.values()) > 0 else "none"

    # 去重关键词
    unique_kw = list(set(matched_keywords))[:10]

    return {
        "features": features,
        "feature_count": feature_count,
        "risk_level": risk_level,
        "matched_keywords": unique_kw,
        "dominant_category": dominant,
        "category_scores": category_scores,
    }


def find_similar_fingerprints(fingerprint: dict, knowledge_store) -> list[dict]:
    """在知识库中查找指纹相似的案例

    通过对比特征向量找到最相似的已核查案例。
    """
    from knowledge.store import _similarity

    results = []
    target_features = fingerprint.get("features", {})

    for case_id, case in knowledge_store._cases.items():
        case_text = case.get("text", "")
        case_fp = extract_fingerprint(case_text)
        case_features = case_fp.get("features", {})

        # 计算特征 Jaccard 相似度
        target_set = {k for k, v in target_features.items() if v}
        case_set = {k for k, v in case_features.items() if v}

        if not target_set or not case_set:
            continue

        intersection = target_set & case_set
        union = target_set | case_set
        feature_sim = len(intersection) / len(union) if union else 0

        if feature_sim >= 0.3:
            results.append({
                "case_id": case_id,
                "text": case_text[:80],
                "verdict": case.get("verdict", ""),
                "category": case.get("category", ""),
                "feature_similarity": round(feature_sim, 3),
                "shared_features": list(intersection)[:5],
            })

    results.sort(key=lambda x: x["feature_similarity"], reverse=True)
    return results[:5]


def fingerprint_summary(fingerprint: dict) -> str:
    """生成指纹特征的可读摘要"""
    features = fingerprint.get("features", {})
    active = [k for k, v in features.items() if v]

    labels = {
        "has_extreme_numbers": "极端数字",
        "has_urgency_call": "紧急呼吁",
        "has_emotional_trigger": "情绪触发",
        "has_authority_claim": "声称权威",
        "has_identity_binding": "身份绑定",
        "has_visual_description": "画面感描述",
        "has_conspiracy_hint": "阴谋暗示",
        "has_total_negation": "全称否定",
        "has_vague_time_place": "时空模糊",
        "has_call_to_action": "行动号召",
        "has_numeric_claim": "数据声明",
        "has_moral_judgment": "道德评判",
        "has_us_vs_them": "对立叙事",
        "has_health_fear": "健康恐慌",
    }

    active_labels = [labels.get(k, k) for k in active]
    risk = fingerprint.get("risk_level", "low")
    risk_emoji = "🔴" if risk == "high" else "🟡" if risk == "medium" else "🟢"

    return f"{risk_emoji} {risk} | {fingerprint.get('feature_count', 0)}个特征 | {', '.join(active_labels[:5])}"
