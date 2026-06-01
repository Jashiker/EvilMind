"""Firecrawl 工具 — 本地部署 + Claude Code CLI 搜索 + 360搜索混合策略"""

from __future__ import annotations
import asyncio, json, logging, re
from typing import Any
import httpx

logger = logging.getLogger(__name__)
FIRECRAWL_API_BASE = "http://localhost:3002"

CLAUDECLI_TIMEOUT = 45
URL_PATTERN = re.compile(r'https?://[^\s\)\]\"\']+', re.IGNORECASE)


def _extract_opencode_text(raw: str) -> str:
    """从 opencode --format json 输出中提取文字内容"""
    parts = []
    for line in raw.splitlines():
        try:
            obj = json.loads(line)
            if obj.get("type") == "text" and obj.get("part", {}).get("type") == "text":
                parts.append(obj["part"].get("text", ""))
        except (json.JSONDecodeError, KeyError):
            continue
    return "\n".join(parts).strip()


async def firecrawl_scrape(url: str, api_key: str = "") -> str:
    """抓取单个URL的网页文字 — 直接HTTP抓取 + opencode降级"""
    try:
        from search.web_search import fetch_url
        text = await fetch_url(url, max_chars=5000)
        if text and len(text) > 200:
            logger.info(f"fetch_url: {len(text)} chars from {url[:60]}")
            return text
    except Exception:
        pass

    try:
        proc = await asyncio.create_subprocess_exec(
            "opencode", "run", "--format", "json",
            f"仅使用WebFetch工具获取{url}的页面文字，不分析不总结，只输出文字",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        text = _extract_opencode_text(stdout.decode("utf-8", errors="replace"))
        if text:
            logger.info(f"opencode scrape: {len(text)} chars from {url[:60]}")
            return text[:5000]
    except Exception as e:
        logger.debug(f"opencode scrape fallback failed: {e}")

    return f"无法获取: {url}"


async def claude_web_search(query: str, context: str = "") -> str:
    """Claude Code CLI 无交互模式 Web 搜索 — 返回搜索结果文本+URL"""
    prompt = f"""请用 web_search 搜索以下内容，返回搜索结果列表，每行包含标题和URL:

查询: {query}"""
    if context:
        prompt += f"\n上下文: {context}"
    prompt += "\n\n请简要返回搜索结果，每条包含标题和完整URL。"

    try:
        proc = await asyncio.create_subprocess_exec(
            "claude", "-p", prompt, "--print", "--output-format", "text",
            "--fork-session",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=CLAUDECLI_TIMEOUT)
        output = stdout.decode("utf-8", errors="replace").strip()
        if stderr:
            logger.debug(f"Claude CLI stderr: {stderr.decode('utf-8', errors='replace')[:200]}")
        if not output:
            return f"Claude CLI 搜索无结果 (exit={proc.returncode})"
        logger.info(f"Claude CLI search '{query[:30]}': {len(output)} chars")
        return output[:4000]
    except asyncio.TimeoutError:
        return f"Claude CLI 搜索超时 ({CLAUDECLI_TIMEOUT}s)"
    except FileNotFoundError:
        return "Claude CLI 未安装 (claude 命令不可用)"
    except Exception as e:
        return f"Claude CLI 异常: {e}"


async def claude_web_search_and_scrape(query: str, context: str = "", max_urls: int = 3) -> str:
    """Claude Code CLI 搜索 → 返回搜索结果(含URL和摘要)"""
    search_output = await claude_web_search(query, context)
    if search_output.startswith("Claude CLI") or search_output.startswith("Claude CLI 未安装"):
        return json.dumps([{"error": search_output}], ensure_ascii=False)

    urls = list(dict.fromkeys(URL_PATTERN.findall(search_output)))[:max_urls]

    if not urls:
        return json.dumps([{"source": "claude_cli", "query": query,
                            "summary": search_output[:1000]}], ensure_ascii=False)

    logger.info(f"Claude CLI → {len(urls)} URLs → 返回搜索摘要")
    results = [{"source": "claude_cli", "query": query, "urls_found": urls,
                "summary": search_output[:2000]}]
    return json.dumps(results, ensure_ascii=False, indent=2)


async def firecrawl_search(query: str, api_key: str = "", max_results: int = 3) -> str:
    """混合搜索: 360搜索发现URL → Firecrawl精读内容"""
    results = []
    try:
        from search.web_search import search_web
        web_results = await search_web(query, max_results)
        if not web_results:
            return json.dumps([], ensure_ascii=False)

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient(timeout=60) as client:
            for r in web_results[:max_results]:
                url = r.get("url", "")
                title = r.get("title", "")
                snippet = r.get("snippet", "")
                if not url:
                    continue
                try:
                    resp = await client.post(
                        f"{FIRECRAWL_API_BASE}/v1/scrape",
                        json={"url": url, "formats": ["markdown"]},
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        d = resp.json()
                        if d.get("success"):
                            md = d.get("data", {}).get("markdown", "") or snippet
                            results.append({"title": title, "url": url, "content": md[:1500]})
                        else:
                            results.append({"title": title, "url": url, "content": snippet[:1000]})
                    else:
                        results.append({"title": title, "url": url, "content": snippet[:1000]})
                except Exception:
                    results.append({"title": title, "url": url, "content": snippet[:1000]})

        logger.info(f"FC混合搜索 '{query[:30]}': {len(results)} results")
        return json.dumps(results, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps([{"error": str(e)}], ensure_ascii=False)


FIRECRAWL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "firecrawl_scrape",
            "description": "Firecrawl抓取指定网页的干净Markdown内容，适合深度阅读官方公告、数据页面原文。",
            "parameters": {"type": "object", "properties": {"url": {"type": "string", "description": "网页URL"}}, "required": ["url"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "firecrawl_search",
            "description": "Firecrawl混合搜索: 360搜索引擎发现 → Firecrawl深度抓取原文。搜索最新网页信息并用Firecrawl提取完整Markdown。",
            "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "搜索关键词"}}, "required": ["query"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "claude_web_search_deep",
            "description": "Claude Code CLI 深度考证: 由Claude自主设计搜索策略 → 获取URL → Firecrawl精读原文。适合需要多角度交叉验证的复杂事实核查。",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string", "description": "搜索关键词(4-10个中文字)"},
                "context": {"type": "string", "description": "搜索上下文: 原始信息的关键事实和需要验证的数据点"}
            }, "required": ["query"]},
        },
    },
]


async def execute_firecrawl_tool(name: str, arguments: dict[str, Any], api_key: str = "") -> str:
    if name == "firecrawl_scrape":
        url = arguments.get("url", "")
        if not url: return "错误: 未提供URL"
        return await firecrawl_scrape(url, api_key)
    elif name == "firecrawl_search":
        query = arguments.get("query", "")
        if not query: return "错误: 未提供搜索关键词"
        return await firecrawl_search(query, api_key)
    elif name == "claude_web_search_deep":
        query = arguments.get("query", "")
        context = arguments.get("context", "")
        if not query: return "错误: 未提供搜索关键词"
        return await claude_web_search_and_scrape(query, context)
    return f"未知工具: {name}"
