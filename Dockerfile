# ── Truth Hunter (邪恶思潮) Dockerfile ──
# 构建: docker build -t truth-hunter .
# 运行: docker run -p 8000:8000 --env-file .env truth-hunter

FROM ubuntu:24.04

LABEL org.opencontainers.image.title="Truth Hunter (邪恶思潮)"
LABEL org.opencontainers.image.description="零信任多Agent谣言核查系统"
LABEL org.opencontainers.image.version="2.0"

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Shanghai

WORKDIR /app

# ── 系统依赖 ──
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    libxml2 libxslt1.1 \
    curl ca-certificates \
    ripgrep \
    nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# ── uv (Python 包管理器，通过 pip + 清华镜像安装) ──
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip && \
    pip install --break-system-packages -i https://pypi.tuna.tsinghua.edu.cn/simple uv && \
    apt-get purge -y --auto-remove python3-pip && \
    rm -rf /var/lib/apt/lists/*

# ── Claude Code CLI (Agent 搜索工具) ──
ENV ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
RUN npm install -g @anthropic-ai/claude-code@latest && \
    claude --version

# ── OpenCode CLI (Agent 抓取降级工具) ──
RUN curl -fsSL https://opencode.ai/install | sh 2>/dev/null && \
    opencode --version || \
    echo "⚠️ opencode 安装失败，页面抓取降级不可用（不影响核心核查）"

# ── Python 依赖 (uv sync 分层缓存) ──
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# ── 应用代码 ──
COPY main.py ./
COPY config/ ./config/
COPY llm/ ./llm/
COPY agents/ ./agents/
COPY pipeline/ ./pipeline/
COPY knowledge/ ./knowledge/
COPY search/ ./search/
COPY tools/ ./tools/
COPY reports/ ./reports/
COPY api/ ./api/
COPY web/ ./web/
COPY data/ ./data/

# 安装项目自身（flat layout，editable 非必须，直接安装）
RUN uv sync --frozen --no-dev

# ── 运行时目录 ──
RUN mkdir -p /app/reports /app/data/chroma_db

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD uv run python -c "import httpx; httpx.get('http://localhost:8000/', timeout=5).raise_for_status()" || exit 1

CMD ["uv", "run", "python", "main.py"]
