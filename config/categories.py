"""6类认知操纵手法分类体系

面向舆论治理场景，按操纵手法分类。
"""

from typing import Any

CATEGORIES: dict[str, dict[str, Any]] = {
    "data_fabrication": {
        "id": "data_fabrication",
        "name": "假数据，真吓人",
        "internal_name": "数据伪造型",
        "icon": "📊",
        "description": "编造统计数字、篡改图表、断章取义数据，用虚假数据制造事实感",
        "indicators": [
            "包含具体数字（百分比、倍数、排名）",
            "声称数据来自某机构但无法溯源",
            "数据与公众认知严重不符",
            "使用'突破''暴跌''暴增'等极端量词",
        ],
        "cognitive_targets": ["锚定效应", "权威偏见"],
        "governance_impact": "侵蚀公众对官方统计数据的信任，制造社会恐慌",
        "example": "中国结婚率不足1%，离婚排长队",
        "check_focus": "数据溯源至官方原始发布",
        "attack_dimension": "经济信心",
    },
    "emotion_hijack": {
        "id": "emotion_hijack",
        "name": "气死你了？先冷静",
        "internal_name": "情绪劫持型",
        "icon": "🔥",
        "description": "利用愤怒、恐惧、同情等强烈情绪绕过理性判断",
        "indicators": [
            "使用极端情绪化语言",
            "刻意制造对立（'他们'vs'我们'）",
            "引用极端个案代替普遍现象",
            "要求立即转发/扩散",
        ],
        "cognitive_targets": ["情绪启发式", "群体认同", "可用性偏差"],
        "governance_impact": "激化社会矛盾，制造群体对立，干扰社会稳定",
        "example": "某地老人被当街殴打，路人无人敢管！",
        "check_focus": "事件真实性、背景完整性、是否有意省略关键信息",
        "attack_dimension": "社会团结",
    },
    "narrative_transplant": {
        "id": "narrative_transplant",
        "name": "真的图，配的假故事",
        "internal_name": "叙事移植型",
        "icon": "🔀",
        "description": "使用真实素材（图片/视频）搭配虚假的时间、地点或背景描述",
        "indicators": [
            "图片/视频真实但背景信息无法验证",
            "关键时空信息模糊或矛盾",
            "缺少可溯源的原始发布者",
            "与已知的真实事件高度相似但细节不同",
        ],
        "cognitive_targets": ["图式一致性", "眼见为实偏见"],
        "governance_impact": "制造虚假社会事件认知，引发局部恐慌或舆情危机",
        "example": "国外骚乱视频标注为'国内某地发生暴乱'",
        "check_focus": "素材反向搜索、时空信息交叉验证",
        "attack_dimension": "社会恐慌",
    },
    "authority_fake": {
        "id": "authority_fake",
        "name": "这个'官方文件'是假的",
        "internal_name": "权威伪装型",
        "icon": "📜",
        "description": "伪造政府公文、冒充专家、仿造媒体账号发布虚假信息",
        "indicators": [
            "声称来自官方但格式不规范",
            "引用的专家/机构不存在或未发表过相关声明",
            "文件编号、公章等细节可疑",
            "仅在非官方渠道传播",
        ],
        "cognitive_targets": ["权威偏见", "信任传递"],
        "governance_impact": "严重损害政府公信力，误导公众政策认知",
        "example": "伪造教育部'取消中考'红头文件",
        "check_focus": "官方渠道原文比对、文件格式规范验证",
        "attack_dimension": "政治信任",
    },
    "trust_corrosion": {
        "id": "trust_corrosion",
        "name": "让你啥都不信，也是套路",
        "internal_name": "信任腐蚀型",
        "icon": "🕳️",
        "description": "不直接造谣，而是系统性地否定一切信息来源，制造认知瘫痪",
        "indicators": [
            "否定所有官方或主流信息来源",
            "暗示'真相不可知'",
            "使用'都是骗局''谁都不信'等极端否定表述",
            "将合理怀疑推向极端怀疑主义",
        ],
        "cognitive_targets": ["虚无主义倾向", "怀疑链传播"],
        "governance_impact": "瓦解社会信任基础，使公众进入认知瘫痪状态",
        "example": "'所有官方数据都是假的，统计局全是编的'",
        "check_focus": "论证逻辑是否自洽、是否存在可验证的反例",
        "attack_dimension": "制度信任",
    },
    "selective_feeding": {
        "id": "selective_feeding",
        "name": "只告诉你一半真相",
        "internal_name": "信息投喂型",
        "icon": "🎯",
        "description": "每句话都是真的，但通过选择性呈现制造虚假的整体认知",
        "indicators": [
            "单一数据点代替完整趋势",
            "省略关键背景或对比数据",
            "真实事件但时间线被裁剪",
            "选择性引用研究结论",
        ],
        "cognitive_targets": ["框架效应", "确认偏误", "锚定效应"],
        "governance_impact": "扭曲公众对重大议题的准确认知，干扰理性公共讨论",
        "example": "'某市犯罪案件同比上升15%'（隐藏了人口增长12%和破案率98%）",
        "check_focus": "信息完整性检查、统计全貌还原、遗漏数据补充",
        "attack_dimension": "认知扭曲",
    },
}

CATEGORY_IDS = list(CATEGORIES.keys())
DISPLAY_NAMES = {k: v["name"] for k, v in CATEGORIES.items()}
ICONS = {k: v["icon"] for k, v in CATEGORIES.items()}
