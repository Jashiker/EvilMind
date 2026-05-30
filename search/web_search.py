"""网页搜索与抓取

核心搜索源：360搜索 (so.com) — 国产搜索引擎，中文索引覆盖全面
Fallback：Bing → Google
"""

from __future__ import annotations

import logging
import json
from typing import Any
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from config import settings

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

_http = httpx.AsyncClient(
    headers=_HEADERS,
    timeout=httpx.Timeout(settings.search_timeout, connect=5.0),
    follow_redirects=True,
)


# ============================================================
# 360搜索 (核心搜索源)
# ============================================================

async def search_360(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """360 搜索 — 国产搜索引擎，中文官方数据源索引最优

    Args:
        query: 搜索关键词
        max_results: 最大返回结果数

    Returns:
        [{"title": "...", "url": "...", "snippet": "...", "source": "360搜索"}]
    """
    results: list[dict[str, str]] = []
    encoded = quote_plus(query)
    url = f"https://www.so.com/s?q={encoded}&pn=1&src=truth_hunter"

    try:
        resp = await _http.get(url)
        if resp.status_code != 200:
            logger.warning(f"360搜索请求失败: HTTP {resp.status_code}")
            return results

        soup = BeautifulSoup(resp.text, "lxml")

        # 360搜索结果在 .result 或 .res-list 中
        for item in soup.select(".result, .res-list, li.res-list")[:max_results]:
            title_el = item.select_one("h3 a") or item.select_one(".res-title a")
            snippet_el = item.select_one(".res-desc") or item.select_one(".res-rich") or item.select_one("p")

            if title_el:
                results.append({
                    "title": title_el.get_text(strip=True),
                    "url": title_el.get("href", ""),
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                    "source": "360搜索",
                })

        if results:
            logger.info(f"🔍 360搜索 '{query[:30]}': 获得 {len(results)} 条结果")

    except Exception as e:
        logger.warning(f"360搜索异常: {e}")

    return results


# ============================================================
# Bing (fallback 1)
# ============================================================

async def search_bing(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Bing 搜索 — fallback"""
    results: list[dict[str, str]] = []
    encoded = quote_plus(query)
    url = f"https://www.bing.com/search?q={encoded}&setlang=zh-Hans"

    try:
        resp = await _http.get(url)
        if resp.status_code != 200:
            return results

        soup = BeautifulSoup(resp.text, "lxml")
        for item in soup.select("li.b_algo")[:max_results]:
            title_el = item.select_one("h2 a")
            snippet_el = item.select_one(".b_caption p") or item.select_one("p")
            if title_el:
                results.append({
                    "title": title_el.get_text(strip=True),
                    "url": title_el.get("href", ""),
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                    "source": "Bing",
                })
        if results:
            logger.info(f"🔍 Bing '{query[:30]}': 获得 {len(results)} 条")
    except Exception as e:
        logger.warning(f"Bing搜索异常: {e}")

    return results


# ============================================================
# Google (fallback 2)
# ============================================================

async def search_google(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Google 搜索 — fallback"""
    results: list[dict[str, str]] = []
    encoded = quote_plus(query)
    url = f"https://www.google.com/search?q={encoded}&hl=zh-CN"

    try:
        resp = await _http.get(url)
        if resp.status_code != 200:
            return results

        soup = BeautifulSoup(resp.text, "lxml")
        for item in soup.select("div.g")[:max_results]:
            title_el = item.select_one("h3")
            link_el = item.select_one("a")
            snippet_el = item.select_one("div[data-sncf], .VwiC3b, span.st")
            if title_el and link_el:
                href = link_el.get("href", "")
                if href.startswith("/url?q="):
                    href = href.split("/url?q=")[1].split("&")[0]
                results.append({
                    "title": title_el.get_text(strip=True),
                    "url": href,
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                    "source": "Google",
                })
        if results:
            logger.info(f"🔍 Google '{query[:30]}': 获得 {len(results)} 条")
    except Exception as e:
        logger.warning(f"Google搜索异常: {e}")

    return results


# ============================================================
# 统一搜索入口 — 360优先，自动fallback
# ============================================================

async def search_web(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """统一搜索入口：360 → Bing → Google

    Returns:
        [{"title": "...", "url": "...", "snippet": "...", "source": "360搜索|Bing|Google"}]
    """
    max_results = max_results or settings.max_search_results

    # 1. 先尝试 360 搜索
    results = await search_360(query, max_results)
    if results:
        return results

    # 2. Fallback: Bing
    logger.info("360搜索无结果，fallback到Bing...")
    results = await search_bing(query, max_results)
    if results:
        return results

    # 3. Fallback: Google
    logger.info("Bing无结果，fallback到Google...")
    results = await search_google(query, max_results)
    if results:
        return results

    logger.warning(f"所有搜索引擎均无结果: '{query}'")
    return []


# ============================================================
# URL 抓取
# ============================================================

async def fetch_url(url: str, max_chars: int = 3000) -> str:
    """抓取指定 URL 的文本内容

    Returns:
        网页正文文本（截断到 max_chars）
    """
    try:
        resp = await _http.get(url)
        if resp.status_code != 200:
            return f"抓取失败: HTTP {resp.status_code}"

        soup = BeautifulSoup(resp.text, "lxml")

        # 移除无关标签
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        text = "\n".join(lines)

        return text[:max_chars]

    except Exception as e:
        return f"抓取异常: {e}"


# ============================================================
# 工具定义（供 DeepSeek function calling 使用）
# ============================================================

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "使用360搜索引擎搜索互联网获取最新信息和权威数据。优先搜索中文官方数据源（国家统计局、教育部、央行等）。当需要核实某个事实、数据或事件时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，尽量具体。例如'中国2024年结婚率 国家统计局 官方数据'"
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "获取指定URL网页的文本内容，用于读取完整的新闻报道、官方公告或数据来源原文。",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "要抓取内容的网页URL",
                    }
                },
                "required": ["url"],
            },
        },
    },
]


# 合并 Firecrawl 工具定义
from tools.firecrawl_tool import FIRECRAWL_TOOLS as _FC_TOOLS, execute_firecrawl_tool
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "使用360搜索引擎搜索互联网获取最新信息和权威数据。优先搜索中文官方数据源（国家统计局、教育部、央行等）。当需要核实某个事实、数据或事件时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，尽量具体。例如'中国2024年结婚率 国家统计局 官方数据'",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "获取指定URL网页的文本内容，用于读取完整的新闻报道、官方公告或数据来源原文。",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "要抓取内容的网页URL",
                    }
                },
                "required": ["url"],
            },
        },
    },
] + _FC_TOOLS


async def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """执行工具调用，返回结果字符串"""
    # 先尝试 Firecrawl 工具
    if name.startswith("firecrawl_"):
        from config import settings
        return await execute_firecrawl_tool(name, arguments, settings.firecrawl_api_key)

    if name == "web_search":
        query = arguments.get("query", "")
        results = await search_web(query)
        if not results:
            return "未找到相关搜索结果。请尝试不同的搜索关键词。"
        return json.dumps(results, ensure_ascii=False, indent=2)

    elif name == "fetch_url":
        url = arguments.get("url", "")
        if not url:
            return "错误：未提供URL"
        content = await fetch_url(url)
        return content

    else:
        return f"未知工具: {name}"
