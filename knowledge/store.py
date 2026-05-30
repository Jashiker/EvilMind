"""知识库 — 案例存储与检索

三层记忆体系：
1. 案例库 — 已核查案例 + 结论
2. 模式库 — 6类操纵手法识别模式
3. 联动 — 多Agent共享同一知识库实例
"""

from __future__ import annotations

import json
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _similarity(s1: str, s2: str) -> float:
    """文本相似度（Jaccard on character bigrams）— 零依赖，启动零延迟"""
    if not s1 or not s2:
        return 0.0

    def bigrams(s: str) -> set[str]:
        return {s[i:i + 2] for i in range(len(s) - 1)}

    b1, b2 = bigrams(s1), bigrams(s2)
    if not b1 or not b2:
        return 0.0

    intersection = b1 & b2
    union = b1 | b2
    return len(intersection) / len(union)


class KnowledgeStore:
    """轻量知识库，内存存储 + 文本相似度匹配 + JSON持久化

    特性：
    - 零启动延迟（无需下载模型）
    - 持久化到 JSON 文件
    - 文本 bigram 相似度检索
    - 多Agent共享同一实例，实现数据联动
    - 支持用户反馈修正
    """

    def __init__(self, persist_dir: str = "data"):
        self._cases: dict[str, dict[str, Any]] = {}
        self._patterns: dict[str, dict[str, Any]] = {}
        self._feedback_log: list[dict] = []
        self._persist_path = Path(persist_dir) / "knowledge_db.json"
        self._load_from_disk()
        logger.info(f"知识库: 案例 {len(self._cases)} 条, 模式 {len(self._patterns)} 条")

    def _load_from_disk(self):
        if self._persist_path.exists():
            try:
                with open(self._persist_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._cases = data.get("cases", {})
                self._patterns = data.get("patterns", {})
                self._feedback_log = data.get("feedback", [])
            except Exception as e:
                logger.warning(f"知识库加载失败: {e}")

    def _save_to_disk(self):
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persist_path, "w", encoding="utf-8") as f:
                json.dump({
                    "cases": self._cases,
                    "patterns": self._patterns,
                    "feedback": self._feedback_log[-100:],  # 只保留最近100条反馈
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"知识库持久化失败: {e}")

    @staticmethod
    def _gen_id(text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()[:12]

    # ── 案例操作 ──

    def add_case(
        self,
        text: str,
        verdict: str,
        category: str,
        evidence_summary: str,
        evil_score: float = 0.5,
        report: dict | None = None,
    ) -> str:
        case_id = self._gen_id(text)
        self._cases[case_id] = {
            "text": text,
            "verdict": verdict,
            "category": category,
            "evidence_summary": evidence_summary,
            "evil_score": evil_score,
            "report": report or {},
            "date": datetime.now().isoformat(),
            "feedback_correct": 0,
            "feedback_incorrect": 0,
        }
        self._save_to_disk()
        logger.info(f"案例入库: {case_id} ({category}/{verdict})")
        return case_id

    def search_similar(
        self,
        text: str,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """搜索相似案例"""
        threshold = 0.3
        results = []
        for case_id, case in self._cases.items():
            sim = _similarity(text, case["text"])
            if sim >= threshold:
                results.append({
                    "id": case_id,
                    "document": case.get("text", ""),
                    "metadata": {
                        "verdict": case["verdict"],
                        "category": case["category"],
                        "evil_score": case.get("evil_score", 0),
                    },
                    "similarity": round(sim, 4),
                })
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    # ── 模式操作 ──

    def add_pattern(self, pattern_id: str, category: str, pattern_text: str, description: str) -> None:
        self._patterns[pattern_id] = {
            "text": pattern_text,
            "category": category,
            "description": description,
        }
        self._save_to_disk()

    def search_patterns(self, text: str, top_k: int = 3) -> list[dict[str, Any]]:
        """搜索匹配的操纵模式"""
        results = []
        for pid, pattern in self._patterns.items():
            sim = _similarity(text, pattern["text"])
            if sim >= 0.1:
                results.append({
                    "id": pid,
                    "document": pattern["text"],
                    "metadata": {
                        "category": pattern["category"],
                        "description": pattern["description"],
                    },
                    "similarity": round(sim, 4),
                })
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    # ── 用户反馈修正 ──

    def record_feedback(self, text: str, is_correct: bool, comment: str = "") -> None:
        """记录用户反馈，修正案例置信度"""
        case_id = self._gen_id(text)
        if case_id in self._cases:
            if is_correct:
                self._cases[case_id]["feedback_correct"] += 1
            else:
                self._cases[case_id]["feedback_incorrect"] += 1

        self._feedback_log.append({
            "case_id": case_id,
            "is_correct": is_correct,
            "comment": comment,
            "date": datetime.now().isoformat(),
        })
        self._save_to_disk()
        logger.info(f"反馈记录: {case_id} -> {'正确' if is_correct else '错误'}")

    # ── 种子数据 ──

    def load_seed_data(self, seed_path: Path) -> int:
        if not seed_path.exists():
            return 0

        with open(seed_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        for case in data.get("cases", []):
            self.add_case(
                text=case["text"],
                verdict=case["verdict"],
                category=case["category"],
                evidence_summary=case.get("evidence_summary", ""),
                evil_score=case.get("evil_score", 0.5),
            )
            count += 1

        for pattern in data.get("patterns", []):
            self.add_pattern(
                pattern_id=pattern["id"],
                category=pattern["category"],
                pattern_text=pattern["text"],
                description=pattern.get("description", ""),
            )

        logger.info(f"种子数据加载: {count} 案例, {len(data.get('patterns', []))} 模式")
        return count

    # ── 知识图谱数据 ──

    def get_graph_data(self) -> dict[str, Any]:
        """生成知识图谱的节点和边数据

        Returns:
            {
                "nodes": [{"id": str, "label": str, "category": str, "evil_score": float, "group": str}],
                "edges": [{"from": str, "to": str, "label": str}]
            }
        """
        nodes = []
        edges = []
        seen_texts = set()

        # 1. 攻击维度作为中心节点
        dimensions = {
            "economic_confidence": "经济信心",
            "social_cohesion": "社会团结",
            "political_stability": "政治稳定",
            "institutional_trust": "制度信任",
        }
        for dim_id, dim_label in dimensions.items():
            nodes.append({
                "id": f"dim_{dim_id}",
                "label": dim_label,
                "group": "attack_dimension",
                "shape": "diamond",
                "size": 35,
                "color": "#a78bfa",
                "font": {"color": "#c4b5fd", "size": 14},
            })

        # 2. 6类操纵手法作为分类节点
        from config.categories import CATEGORIES
        for cat_id, cat_info in CATEGORIES.items():
            nodes.append({
                "id": f"cat_{cat_id}",
                "label": cat_info["name"],
                "group": "category",
                "shape": "dot",
                "size": 28,
                "color": "#60a5fa",
                "font": {"color": "#93c5fd", "size": 13},
            })
            # 分类 → 攻击维度
            dim_map = {
                "data_fabrication": "economic_confidence",
                "emotion_hijack": "social_cohesion",
                "narrative_transplant": "social_cohesion",
                "authority_fake": "political_stability",
                "trust_corrosion": "institutional_trust",
                "selective_feeding": "economic_confidence",
            }
            target_dim = dim_map.get(cat_id, "institutional_trust")
            edges.append({
                "from": f"cat_{cat_id}",
                "to": f"dim_{target_dim}",
                "dashes": True,
                "color": {"opacity": 0.4},
            })

        # 3. 案例节点
        category_colors = {
            "data_fabrication": "#f87171",
            "emotion_hijack": "#fbbf24",
            "narrative_transplant": "#a78bfa",
            "authority_fake": "#60a5fa",
            "trust_corrosion": "#9ca3af",
            "selective_feeding": "#34d399",
        }

        for case_id, case in self._cases.items():
            text = case["text"][:30]
            if text in seen_texts:
                continue
            seen_texts.add(text)

            cat = case.get("category", "none")
            evil = case.get("evil_score", 0.5)
            verdict = case.get("verdict", "")

            # 节点大小基于邪恶评分
            size = 15 + evil * 20

            # 判定图标
            icon = "🔴" if "false" in verdict else "🟡" if "manipulative" in verdict else "🟢"

            node_id = f"case_{case_id}"
            nodes.append({
                "id": node_id,
                "label": f"{icon} {text}",
                "group": "case",
                "shape": "box",
                "size": size,
                "evil_score": evil,
                "color": category_colors.get(cat, "#6b7280"),
                "font": {"color": "#e5e7eb", "size": 12},
                "title": f"<b>{case['text'][:80]}</b><br>判定: {verdict}<br>邪恶评分: {evil:.0%}<br>分类: {cat}",
            })

            # 案例 → 分类
            edges.append({
                "from": node_id,
                "to": f"cat_{cat}",
                "color": {"color": category_colors.get(cat, "#6b7280"), "opacity": 0.6},
            })

            # 案例 → 攻击维度（基于邪恶评分）
            dim_target = {
                "data_fabrication": "economic_confidence",
                "emotion_hijack": "social_cohesion",
                "narrative_transplant": "social_cohesion",
                "authority_fake": "political_stability",
                "trust_corrosion": "institutional_trust",
                "selective_feeding": "economic_confidence",
            }.get(cat, "institutional_trust")

            edges.append({
                "from": node_id,
                "to": f"dim_{dim_target}",
                "dashes": True,
                "color": {"opacity": 0.2},
                "width": evil,  # 线宽基于邪恶评分
            })

        return {"nodes": nodes, "edges": edges}

    # ── 统计 ──

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_cases": len(self._cases),
            "total_patterns": len(self._patterns),
        }
