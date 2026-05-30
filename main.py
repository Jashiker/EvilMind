"""邪恶思潮 — 启动入口"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def check_env():
    """检查环境配置"""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        logger.error("❌ 未找到 .env 配置文件，请: cp .env.example .env")
        sys.exit(1)

    from config import settings

    if not settings.deepseek_api_key:
        logger.error("❌ DEEPSEEK_API_KEY 未配置，请在 .env 中设置")
        sys.exit(1)
    logger.info(f"✓ API Key 已配置")
    logger.info(f"✓ 模型: {settings.primary_model}")


def init():
    """初始化所有组件"""
    from config import settings
    from llm.client import LLMClient
    from knowledge.store import KnowledgeStore
    from pipeline.orchestrator import PipelineOrchestrator
    from output.report import ReportGenerator
    from api.server import app, set_pipeline

    logger.info("🔧 正在初始化邪恶思潮...")

    # LLM
    llm = LLMClient()
    logger.info(f"  ✓ LLM 客户端 ({settings.primary_model})")

    # 知识库
    kb = KnowledgeStore()

    # 加载基础种子数据
    seed = Path(__file__).parent / "data" / "seed_patterns.json"
    if seed.exists():
        n = kb.load_seed_data(seed)
        logger.info(f"  ✓ 基础种子库 ({n} 条)")

    # 加载微博谣言数据库
    weibo_seed = Path(__file__).parent / "data" / "weibo_seed.json"
    if weibo_seed.exists():
        n2 = kb.load_seed_data(weibo_seed)
        logger.info(f"  ✓ 微博谣言库 ({n2} 条)")

    total = len(kb._cases)
    logger.info(f"  ✓ 知识库总计: {total} 条案例, {len(kb._patterns)} 条模式")

    # 管道
    pipeline = PipelineOrchestrator(llm, kb, ReportGenerator())
    set_pipeline(pipeline)
    logger.info("  ✓ 3Agent 管道就绪 (恶意假设官 → 核查记者 → 真相发布官)")

    return app


def main():
    """启动服务"""
    print("""
╔══════════════════════════════════════════════╗
║   🛡️  邪恶思潮 — 恶意假设驱动的核查Agent     ║
║                                              ║
║   👁️  恶意假设官 → 🔍 核查记者 → 📋 发布官    ║
║   🧠 DeepSeek-V3  |  🔗 360搜索             ║
╚══════════════════════════════════════════════╝
""")
    check_env()
    app = init()
    from config import settings

    logger.info(f"🚀 启动服务: http://{settings.host}:{settings.port}")
    logger.info("📋 打开浏览器访问上方地址即可使用")

    uvicorn.run(app, host=settings.host, port=settings.port, log_level="warning")


if __name__ == "__main__":
    main()
