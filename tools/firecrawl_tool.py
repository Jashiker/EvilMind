"""Firecrawl 网页抓取工具

使用 Firecrawl API 获取网页的干净 Markdown 内容，
比 BeautifulSoup 提取更准确，保留原文结构和关键信息。

API: https://api.firecrawl.dev
免费额度: 500 credits/月
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

FIRECRAWL_API_BASE = "https://api.firecrawl.dev"


async def firecrawl_scrape(url: str, api_key: str = "") -> str:
    """用 Firecrawl 抓取单个网页，返回干净的 Markdown 内容

    Args:
        url: 目标网页 URL
        api_key: Firecrawl API key

    Returns:
        网页的 Markdown 格式内容
    """
    if not api_key:
        return f"[Firecrawl 未配置 API Key，无法抓取] {url}"

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                f"{FIRECRAWL_API_BASE}/v1/scrape",
                json={"url": url, "formats": ["markdown"]},
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    markdown = data.get("data", {}).get("markdown", "")
                    if markdown:
                        logger.info(f"Firecrawl scrape: {len(markdown)} chars from {url[:60]}")
                        return markdown[:5000]  # 限制长度
                return f"Firecrawl 抓取失败: {data.get('error', 'unknown')}"
            elif resp.status_code == 402:
                return f"Firecrawl API 额度不足: {resp.text[:200]}"
            else:
                return f"Firecrawl HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            return f"Firecrawl 异常: {e}"


async def firecrawl_search(query: str, api_key: str = "", max_results: int = 3) -> str:
    """用 Firecrawl 搜索并抓取搜索结果页内容

    Args:
        query: 搜索关键词
        api_key: Firecrawl API key
        max_results: 最大结果数

    Returns:
        搜索结果 + 页面内容的 JSON
    """
    if not api_key:
        return f"[Firecrawl 未配置 API Key，无法搜索] query: {query}"

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                f"{FIRECRAWL_API_BASE}/v1/search",
                json={
                    "query": query,
                    "limit": max_results,
                    "scrapeOptions": {"formats": ["markdown"]},
                },
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    results = []
                    for item in data.get("data", [])[:max_results]:
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "content": (item.get("markdown", "") or item.get("description", ""))[:1500],
                        })
                    logger.info(f"Firecrawl search: '{query[:30]}' -> {len(results)} results")
                    return json.dumps(results, ensure_ascii=False, indent=2)
                return f"Firecrawl 搜索失败: {data.get('error', '')}"
            elif resp.status_code == 402:
                return f"Firecrawl API 额度不足: {resp.text[:200]}"
            else:
                return f"Firecrawl HTTP {resp.status_code}"
        except Exception as e:
            return f"Firecrawl 异常: {e}"


# ============================================================
# 供 DeepSeek function calling 使用的工具定义
# ============================================================

FIRECRAWL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "firecrawl_scrape",
            "description": "使用Firecrawl抓取指定网页的完整内容，返回干净的Markdown格式文本。适合读取官方公告、新闻报道、数据页面等。比普通抓取更准确、更干净。",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "要抓取的网页URL，例如'https://www.stats.gov.cn/...'",
                    }
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "firecrawl_search",
            "description": "使用Firecrawl搜索互联网并同时抓取搜索结果页面的完整内容（Markdown格式）。比普通搜索更强大，直接返回去噪后的页面正文。适合深度核查时需要阅读原始网页内容时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，例如'中国2024年GDP 国家统计局 官方数据'",
                    }
                },
                "required": ["query"],
            },
        },
    },
]


async def execute_firecrawl_tool(name: str, arguments: dict[str, Any], api_key: str = "") -> str:
    """执行 Firecrawl 工具调用"""
    if name == "firecrawl_scrape":
        url = arguments.get("url", "")
        if not url:
            return "错误: 未提供URL"
        return await firecrawl_scrape(url, api_key)

    elif name == "firecrawl_search":
        query = arguments.get("query", "")
        if not query:
            return "错误: 未提供搜索关键词"
        return await firecrawl_search(query, api_key)

    return f"未知 Firecrawl 工具: {name}"
