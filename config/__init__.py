"""全局配置管理"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


class Settings(BaseSettings):
    """应用配置，从 .env 文件读取"""

    # === DeepSeek API ===
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"

    # === 视觉模型 API (OCR用) ===
    vision_api_key: str = ""
    vision_base_url: str = "https://api.deepseek.com"
    vision_model: str = "deepseek-chat"

    # === Firecrawl API ===
    firecrawl_api_key: str = ""

    # === 百度飞桨 OCR API ===
    baidu_ocr_api_key: str = ""
    baidu_ocr_secret_key: str = ""
    aistudio_ocr_url: str = ""  # AI Studio 部署的 OCR API URL（含 /ocr 路径）

    # === 模型配置 ===
    primary_model: str = "deepseek-v4-pro"
    secondary_model: str = "deepseek-v4-pro"

    # === 服务配置 ===
    host: str = "0.0.0.0"
    port: int = 8000

    # === LLM 参数 ===
    max_retries: int = 2
    request_timeout: float = 90.0
    max_tokens: int = 4096
    temperature: float = 0.1

    # === 知识库配置 ===
    similarity_threshold: float = 0.3
    chroma_persist_dir: str = str(DATA_DIR / "chroma_db")

    # === 搜索配置 ===
    max_search_results: int = 5
    search_timeout: float = 10.0

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def api_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.deepseek_api_key}",
            "Content-Type": "application/json",
        }


settings = Settings()

# 确保数据目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
