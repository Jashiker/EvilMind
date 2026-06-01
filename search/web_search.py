"""360搜索 · 官方搜索引擎接入

360搜索 (so.com) 是360旗下的国产搜索引擎，对中文网页尤其是
国内官方数据源（.gov.cn、统计局、央行、教育部等）有最优的索引覆盖。

与360生态的联动价值：
- 360浏览器用户可直接调用搜索核查
- 搜索结果与360安全大脑威胁情报联动
- 中文官方数据源索引质量高于Google/Bing

技术实现: 通过360搜索Web接口进行结构化检索，支持官方来源标记、
搜索统计追踪、多级Fallback容错。
"""

from __future__ import annotations

import logging
import json
import time
from typing import Any
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from config import settings

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

_http = httpx.AsyncClient(
    headers=_HEADERS,
    timeout=httpx.Timeout(settings.search_timeout, connect=5.0),
    follow_redirects=True,
)

# 360搜索统计
_stats = {"searches": 0, "results": 0, "official_hits": 0, "last_search": ""}


def get_360_stats() -> dict:
    return dict(_stats)


# ============================================================
# 360搜索 — 核心搜索引擎
# ============================================================

async def search_360(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """360搜索 — 国产搜索引擎，专为中文官方数据源优化

    360搜索优势:
    - 对 .gov.cn 域名有优先索引策略
    - 中文分词和语义理解优于国际搜索引擎
    - 国内新闻和政策的时效性覆盖更全面
    - 与360安全浏览器天然打通，可实现内容安全联动

    Returns:
        [{"title": str, "url": str, "snippet": str, "source": "360搜索",
          "is_official": bool, "domain": str}]
    """
    results: list[dict[str, str]] = []
    encoded = quote_plus(query, safe='')
    url = f"https://www.so.com/s?q={encoded}&pn=1&src=truth_hunter"

    try:
        resp = await _http.get(url)
        if resp.status_code != 200:
            logger.warning(f"360搜索 HTTP {resp.status_code}")
            return results

        soup = BeautifulSoup(resp.text, "lxml")
        items = soup.select(".result, .res-list, li.res-list")[:max_results]

        for item in items:
            title_el = item.select_one("h3 a") or item.select_one(".res-title a")
            snippet_el = item.select_one(".res-desc") or item.select_one(".res-rich") or item.select_one("p")

            if title_el:
                href = title_el.get("href", "")
                # Resolve 360 redirect links to actual target URLs
                if "so.com/link" in href:
                    try:
                        import asyncio
                        r2 = await _http.get(href, follow_redirects=True)
                        if r2.status_code < 400 and str(r2.url) != href:
                            href = str(r2.url)
                    except Exception:
                        pass
                domain = _extract_domain(href)
                is_official = _is_official_source(href, title_el.get_text(strip=True))

                results.append({
                    "title": title_el.get_text(strip=True),
                    "url": href,
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                    "source": "360搜索",
                    "is_official": is_official,
                    "domain": domain,
                })

        # 更新统计
        _stats["searches"] += 1
        _stats["results"] += len(results)
        _stats["official_hits"] += sum(1 for r in results if r.get("is_official"))
        _stats["last_search"] = query[:50]

        if results:
            official_count = sum(1 for r in results if r.get("is_official"))
            logger.info(f"🔍 360搜索 '{query[:30]}': {len(results)}条 ({official_count}官方源)")

    except Exception as e:
        logger.warning(f"360搜索异常: {e}")

    return results


def _extract_domain(url: str) -> str:
    """提取域名"""
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc or ""
    except Exception:
        return ""


def _is_official_source(url: str, title: str) -> bool:
    """判定是否为官方权威来源

    360搜索对以下来源有优先索引:
    - .gov.cn 政府网站
    - 官方机构: 统计局、央行、教育部、民政部等
    - 官方媒体: 新华社、人民日报、央视
    """
    official_domains = [
        '.gov.cn', 'stats.gov.cn', 'pbc.gov.cn', 'moe.gov.cn', 'mca.gov.cn',
        'xinhuanet.com', 'people.com.cn', 'cctv.com', 'chinanews.com',
        'nhc.gov.cn', 'mofcom.gov.cn', 'customs.gov.cn',
    ]
    official_keywords = ['国家统计局', '中国人民银行', '教育部', '民政部', '国务院',
                         '新华社', '人民日报', '央视', '官方', '卫健委']

    domain = _extract_domain(url)
    if any(d in domain for d in official_domains):
        return True
    if any(kw in title for kw in official_keywords):
        return True
    return False


# ============================================================
# Bing Fallback
# ============================================================

async def search_bing(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Bing搜索 — Fallback 1"""
    results: list[dict[str, str]] = []
    try:
        resp = await _http.get(f"https://www.bing.com/search?q={quote_plus(query)}&setlang=zh-Hans")
        if resp.status_code != 200:
            return results
        soup = BeautifulSoup(resp.text, "lxml")
        for item in soup.select("li.b_algo")[:max_results]:
            t = item.select_one("h2 a")
            s = item.select_one(".b_caption p") or item.select_one("p")
            if t:
                results.append({"title": t.get_text(strip=True), "url": t.get("href",""),
                                "snippet": s.get_text(strip=True) if s else "", "source": "Bing",
                                "is_official": False, "domain": _extract_domain(t.get("href",""))})
    except Exception as e:
        logger.warning(f"Bing搜索异常: {e}")
    return results


async def search_google(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Google搜索 — Fallback 2"""
    results: list[dict[str, str]] = []
    try:
        resp = await _http.get(f"https://www.google.com/search?q={quote_plus(query)}&hl=zh-CN")
        if resp.status_code != 200:
            return results
        soup = BeautifulSoup(resp.text, "lxml")
        for item in soup.select("div.g")[:max_results]:
            t_el = item.select_one("h3"); l_el = item.select_one("a")
            s_el = item.select_one("div[data-sncf], .VwiC3b, span.st")
            if t_el and l_el:
                href = l_el.get("href","")
                if href.startswith("/url?q="): href = href.split("/url?q=")[1].split("&")[0]
                results.append({"title": t_el.get_text(strip=True), "url": href,
                                "snippet": s_el.get_text(strip=True) if s_el else "", "source": "Google",
                                "is_official": False, "domain": _extract_domain(href)})
    except Exception as e:
        logger.warning(f"Google搜索异常: {e}")
    return results


# ============================================================
# 统一搜索入口 — 360优先
# ============================================================

async def search_web(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """统一搜索: 360搜索(主) → Bing → Google"""
    max_results = max_results or settings.max_search_results

    # 1. 360搜索 (核心)
    results = await search_360(query, max_results)
    if results:
        return results

    # 2. Bing
    logger.info("360搜索无结果 → Bing")
    results = await search_bing(query, max_results)
    if results:
        return results

    # 3. Google
    logger.info("Bing无结果 → Google")
    return await search_google(query, max_results)


# ============================================================
# URL抓取
# ============================================================

async def fetch_url(url: str, max_chars: int = 3000) -> str:
    """抓取网页文本"""
    try:
        resp = await _http.get(url)
        if resp.status_code != 200:
            return f"HTTP {resp.status_code}"
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script","style","nav","footer","header","aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return "\n".join([l.strip() for l in text.splitlines() if l.strip()])[:max_chars]
    except Exception as e:
        return f"抓取异常: {e}"


# ============================================================
# 工具定义 (DeepSeek function calling)
# ============================================================

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "使用360搜索引擎搜索互联网。360搜索对中文官方数据源（.gov.cn、统计局、央行等）有最优索引，适合核查国内政策、数据、社会事件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词，加上官方机构名更精准，如'中国2024年结婚率 民政部 官方数据'"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "读取指定URL的网页全文，用于核对原始公告、官方数据原文。",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "网页URL"}
                },
                "required": ["url"],
            },
        },
    },
]

# 合并Firecrawl + OpenOSINT工具定义
from tools.firecrawl_tool import FIRECRAWL_TOOLS as _FC_TOOLS
from tools.openosint_tool import OPENOSINT_TOOLS as _OSINT_TOOLS
TOOL_DEFINITIONS = TOOL_DEFINITIONS + _FC_TOOLS + _OSINT_TOOLS


async def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """工具执行入口"""
    from tools.firecrawl_tool import FIRECRAWL_TOOLS as _FC_TOOLS, execute_firecrawl_tool

    if name.startswith("firecrawl_") or name.startswith("claude_"):
        return await execute_firecrawl_tool(name, arguments, settings.firecrawl_api_key)

    if name.startswith("verify_"):
        from tools.openosint_tool import execute_openosint_tool
        return await execute_openosint_tool(name, arguments)

    if name == "web_search":
        results = await search_web(arguments.get("query", ""))
        if not results:
            return "未找到结果，请尝试更精准的关键词。"
        return json.dumps(results, ensure_ascii=False, indent=2)

    if name == "fetch_url":
        url = arguments.get("url", "")
        return await fetch_url(url) if url else "错误: 未提供URL"

    return f"未知工具: {name}"
