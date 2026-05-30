"""Agent 基类"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class BaseAgent:
    """所有 Agent 的基类"""

    def __init__(self, llm, knowledge):
        self.llm = llm
        self.knowledge = knowledge

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @staticmethod
    def _extract_json(text: str) -> dict:
        """从文本中提取 JSON"""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])

        start, end = text.find("{"), text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        return json.loads(text)
