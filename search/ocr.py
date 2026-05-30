"""百度 AI Studio PP-OCRv5 远程 API

API 文档: https://ai.baidu.com/ai-doc/AISTUDIO/Kmfl2ycs0

认证方式: Authorization: token {TOKEN}
端点: POST {API_URL}  (从 https://aistudio.baidu.com/paddleocr/task 获取)
"""

from __future__ import annotations

import base64
import logging
import time
import httpx

logger = logging.getLogger(__name__)

# Token 缓存（百度智能云标准模式 OAuth）
_token_cache: dict = {"token": None, "expires_at": 0}

BAIDU_OAUTH_URL = "https://aip.baidubce.com/oauth/2.0/token"
BAIDU_OCR_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic"


async def _get_oauth_token(api_key: str, secret_key: str) -> str:
    """OAuth 获取 access_token（百度智能云标准模式）"""
    global _token_cache
    if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["token"]

    url = f"{BAIDU_OAUTH_URL}?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url)
        resp.raise_for_status()
        data = resp.json()

    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"获取百度 access_token 失败: {data}")

    _token_cache["token"] = token
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 2592000) - 3600
    logger.info("百度 OAuth token 已获取")
    return token


def _parse_pruned_result(pruned: dict) -> list[str]:
    """解析 PP-OCRv5 prunedResult 中的文字

    PP-OCRv5 输出格式:
      {
        "rec_texts": "第一行文字\n第二行文字...",
        "rec_scores": [0.99, 0.98, ...],
        "rec_polys": [...],
        "dt_polys": [...]
      }
    """
    lines = []

    # rec_texts 可能是字符串（换行分隔）或列表
    rec_texts = pruned.get("rec_texts", "")
    if isinstance(rec_texts, str) and rec_texts.strip():
        for line in rec_texts.split("\n"):
            line = line.strip()
            if line:
                lines.append(line)
    elif isinstance(rec_texts, list):
        for t in rec_texts:
            if isinstance(t, str) and t.strip():
                lines.append(t.strip())

    # 兼容旧格式: {texts: [...]}
    if not lines:
        texts = pruned.get("texts", [])
        for t in texts:
            txt = t.get("text", "") if isinstance(t, dict) else str(t)
            if txt.strip():
                lines.append(txt.strip())

    return lines


async def ocr_image(
    image_bytes: bytes,
    api_key: str = "",
    secret_key: str = "",
    api_url: str = "",
) -> str:
    """调用百度 PP-OCRv5 API 提取图片文字

    Args:
        image_bytes: 图片二进制数据
        api_key: AI Studio TOKEN（Authorization: token {TOKEN}）
        secret_key: 百度智能云 Secret Key（标准模式才需要）
        api_url: AI Studio 部署的完整 OCR URL（如 https://xxx/ocr）

    Returns:
        提取的文字
    """
    if not api_key:
        raise ValueError("百度 OCR Token 未配置，请在 .env 中设置 BAIDU_OCR_API_KEY")

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    # ── 方式1: AI Studio PP-OCRv5 模式 ──
    if api_url:
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(
                    api_url,
                    json={"file": image_b64, "fileType": 1},
                    headers={
                        "Authorization": f"token {api_key}",
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("errorCode") == 0:
                        lines = []
                        ocr_results = data.get("result", {}).get("ocrResults", [])
                        for ocr in ocr_results:
                            pruned = ocr.get("prunedResult", {})
                            lines.extend(_parse_pruned_result(pruned))

                        if lines:
                            text = "\n".join(lines)
                            logger.info(f"PP-OCRv5: {len(lines)} 行, {len(text)} 字符")
                            return text

                    logger.info(f"PP-OCRv5 errorCode={data.get('errorCode')}, msg={data.get('errorMsg')}")
                else:
                    logger.warning(f"AI Studio 返回 HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                logger.warning(f"AI Studio 异常: {e}")

    # ── 方式2: 百度智能云标准模式 ──
    if secret_key:
        token = await _get_oauth_token(api_key, secret_key)
    else:
        token = api_key

    url = f"{BAIDU_OCR_URL}?access_token={token}"
    payload = {
        "image": image_b64,
        "language_type": "CHN_ENG",
        "detect_direction": "true",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()

    if "error_code" in data:
        raise RuntimeError(f"百度 OCR 错误 ({data['error_code']}): {data.get('error_msg', '')}")

    words = data.get("words_result", [])
    lines = [w["words"] for w in words if w.get("words")]
    text = "\n".join(lines)
    logger.info(f"百度标准 OCR: {len(lines)} 行, {len(text)} 字符")
    return text
