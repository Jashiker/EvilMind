"""FastAPI 后端 — SSE 流式 + 静态文件 + 用户反馈 + 图片审查"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse

from pipeline.orchestrator import PipelineOrchestrator

logger = logging.getLogger(__name__)

app = FastAPI(title="邪恶思潮", version="1.0.0")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_pipeline: PipelineOrchestrator | None = None


def set_pipeline(pipeline: PipelineOrchestrator):
    global _pipeline
    _pipeline = pipeline


def get_pipeline() -> PipelineOrchestrator:
    assert _pipeline is not None, "管道未初始化"
    return _pipeline


# ============================================================
# 静态文件
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def index():
    return (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/style.css")
async def style():
    return FileResponse(FRONTEND_DIR / "style.css", media_type="text/css")


@app.get("/app.js")
async def js():
    return FileResponse(FRONTEND_DIR / "app.js", media_type="application/javascript")


# ============================================================
# API
# ============================================================

@app.get("/api/demo/cases")
async def get_demo_cases():
    """获取预设测试案例"""
    test_file = DATA_DIR / "test_rumors.json"
    if not test_file.exists():
        return {"cases": []}
    with open(test_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    cases = [
        {"id": r["id"], "text": r["text"], "category": r["category"], "difficulty": r["difficulty"]}
        for r in data.get("rumors", [])
    ]
    return {"cases": cases[:12]}


@app.post("/api/analyze")
async def analyze(request: Request):
    """提交文本分析 — SSE 真流式"""
    body = await request.json()
    text = body.get("text", "").strip()
    if not text:
        return {"error": "请输入待分析文本"}

    pipeline = get_pipeline()

    async def event_stream():
        queue: asyncio.Queue = asyncio.Queue()

        async def collector(event_data: dict):
            await queue.put(event_data)

        async def run_pipeline():
            try:
                await pipeline.analyze(text, stream_callback=collector)
            except Exception as e:
                logger.error(f"分析失败: {e}", exc_info=True)
                await queue.put({"event": "error", "message": str(e)})
            finally:
                await queue.put(None)  # 哨兵

        task = asyncio.create_task(run_pipeline())

        try:
            while True:
                event_data = await queue.get()
                if event_data is None:
                    break
                yield f"data: {json.dumps(event_data, ensure_ascii=False, default=str)}\n\n"
        finally:
            task.cancel()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/analyze-image")
async def analyze_image(file: UploadFile = File(...), prompt: str = Form("")):
    """图片审查 — OCR 提取文字 → 3Agent 核查流水线"""
    pipeline = get_pipeline()

    # 读取图片并转 base64
    contents = await file.read()
    image_b64 = base64.b64encode(contents).decode("utf-8")
    mime_type = file.content_type or "image/png"

    async def event_stream():
        queue: asyncio.Queue = asyncio.Queue()

        async def collector(event_data: dict):
            await queue.put(event_data)

        async def run_pipeline():
            try:
                # Step 0: OCR 提取文字
                extracted_text = ""
                ocr_method = ""

                # 使用百度飞桨 OCR 远程 API
                from config import settings

                await queue.put({
                    "event": "ocr_start",
                    "data": {"message": "🔍 正在调用百度飞桨OCR识别图片文字...", "filename": file.filename},
                })

                from search.ocr import ocr_image as baidu_ocr

                try:
                    extracted_text = await baidu_ocr(
                        contents,
                        api_key=settings.baidu_ocr_api_key,
                        secret_key=settings.baidu_ocr_secret_key,
                        api_url=settings.aistudio_ocr_url,
                    )
                    ocr_method = "百度飞桨OCR (远程API)"
                except Exception as ocr_err:
                    logger.error(f"百度OCR失败: {ocr_err}")
                    await queue.put({
                        "event": "error",
                        "message": f"OCR识别失败: {ocr_err}。请检查百度OCR API Key和Secret Key是否正确配置（.env 中 BAIDU_OCR_API_KEY 和 BAIDU_OCR_SECRET_KEY）",
                    })
                    await queue.put(None)
                    return

                if not extracted_text.strip():
                    await queue.put({"event": "error", "message": "未能从图片中提取到文字，请确认图片包含清晰的中文文字"})
                    await queue.put(None)
                    return

                await queue.put({
                    "event": "ocr_complete",
                    "data": {"text": extracted_text, "length": len(extracted_text), "method": ocr_method},
                })

                # Step 1-3: 送入核查流水线
                await pipeline.analyze(extracted_text, stream_callback=collector)

            except Exception as e:
                logger.error(f"图片审查失败: {e}", exc_info=True)
                await queue.put({"event": "error", "message": f"图片审查失败: {e}"})
            finally:
                await queue.put(None)

        task = asyncio.create_task(run_pipeline())

        try:
            while True:
                event_data = await queue.get()
                if event_data is None:
                    break
                yield f"data: {json.dumps(event_data, ensure_ascii=False, default=str)}\n\n"
        finally:
            task.cancel()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.post("/api/fingerprint")
async def analyze_fingerprint(request: Request):
    """提取谣言指纹特征"""
    body = await request.json()
    text = body.get("text", "").strip()
    if not text:
        return {"error": "请输入文本"}

    from knowledge.fingerprint import extract_fingerprint, find_similar_fingerprints, fingerprint_summary

    fp = extract_fingerprint(text)
    pipeline = get_pipeline()
    similar = find_similar_fingerprints(fp, pipeline.knowledge)

    return {
        "fingerprint": fp,
        "summary": fingerprint_summary(fp),
        "similar_cases": similar,
    }


@app.post("/api/evolution")
async def get_evolution(request: Request):
    """谣言进化树 + 行为分析 + 动机分析"""
    body = await request.json()
    text = body.get("text", "").strip()
    if not text:
        return {"error": "请输入文本"}

    from knowledge.evolution import build_evolution_tree, analyze_behavior, analyze_motivation
    from knowledge.fingerprint import extract_fingerprint

    pipeline = get_pipeline()
    fp = extract_fingerprint(text)
    tree = build_evolution_tree(text, pipeline.knowledge)
    behavior = analyze_behavior(text, fp)
    motivation = analyze_motivation(text, fp)

    return {
        "evolution_tree": tree,
        "behavior": behavior,
        "motivation": motivation,
        "fingerprint_summary": fp,
    }


@app.get("/api/knowledge/stats")
async def get_knowledge_stats():
    """知识库统计"""
    pipeline = get_pipeline()
    return pipeline.knowledge.get_stats()


@app.get("/api/knowledge/graph")
async def get_knowledge_graph():
    """知识图谱数据 — vis.js 格式"""
    pipeline = get_pipeline()
    return pipeline.knowledge.get_graph_data()


@app.post("/api/feedback")
async def submit_feedback(request: Request):
    """用户反馈 — 修正知识库"""
    body = await request.json()
    text = body.get("text", "")
    is_correct = body.get("is_correct", True)
    comment = body.get("comment", "")

    pipeline = get_pipeline()
    pipeline.knowledge.record_feedback(text, is_correct, comment)

    return {"status": "ok", "message": "反馈已记录，感谢！"}
