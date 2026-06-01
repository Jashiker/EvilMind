# 🛡️ 邪恶思潮 EvilMind

<div align="center">

**零信任多 Agent 谣言核查系统** · 4 阶段严格管道 · SSE 实时流式 · 证据可溯源

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek--v4-536DFE)](https://deepseek.com)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker)](https://docs.docker.com)
[![License](https://img.shields.io/badge/License-GPLv3-blue)](./LICENSE)

</div>

---

## 概述

**邪恶思潮 (EvilMind)** 是一个零信任认知战防御系统。系统将谣言核查分解为 4 个严格顺序的阶段，每阶段内多个 Agent 并行工作，通过 SSE（Server-Sent Events）将每个 Agent 的分析进度实时推送到前端。

### 核心亮点

- **4 阶段 10 Agent 协作**：指纹研判团队（5 专家并行）→ 三路侦察兵（3 路并行取证）→ 合议庭（3 仲裁官独立裁定）→ 品质审核官
- **关键词精准分流**：指纹研判官提炼三组搜索关键词，分别传递给事实核查/深度挖掘/来源验证三个 Agent
- **全链路证据溯源**：每条判定附带真实搜索 URL，vis.js 交互式证据网络图可双击打开原文
- **SSE 真流式**：4 个 Agent 面板进度条实时更新，无需等待全部完成即可看到中间结果
- **双模输入**：支持文字粘贴 + 图片截图 OCR（百度飞桨远程 API / Ctrl+V 粘贴）
- **认知处方 + 辟谣卡片**：面向普通读者的防骗指南 + 一键复制分享

---

## 快速开始

### 本地运行

```bash
# 1. 安装依赖
uv sync

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 3. 启动
uv run python main.py
```

访问：
- `http://localhost:8000/` — 产品宣传首页
- `http://localhost:8000/app` — 审查研判工具
- `http://localhost:8000/guide` — 使用说明

### Docker 部署

```bash
cp .env.example .env          # 填入 DEEPSEEK_API_KEY
docker compose up -d          # 构建并启动
```

镜像内置 Claude Code CLI（Agent 搜索）和 OpenCode CLI（页面抓取降级）。如 OpenCode 安装失败不影响核心核查功能。

---

## 架构

### 4 阶段管道

```
用户输入（文字/截图）
  │
  ├─ 知识库检索（Chromadb + Bigram 相似度）
  ├─ 14 维指纹提取 + 认知战攻击检测
  │
  ▼
┌─────────────────────────────────────────────────────┐
│ 阶段 1：指纹研判团队                                  │
│  🧬 指纹对比官  🌳 进化树分析师  🔍 意图挖掘官  ⚠️ 风险评估官  │
│  （4 专家并行）                                        │
│          ↓                                            │
│  ⚖️ 综合研判官 → evil_score + malice_hypothesis + 三组搜索关键词 │
└─────────────────────────────────────────────────────┘
  │  关键词分流：fact_check → 事实核查官
  │             deep_search → 深度挖掘官
  │             source_check → 来源验证官
  ▼
┌─────────────────────────────────────────────────────┐
│ 阶段 2：三路侦察兵                                    │
│  🔍 Claude 事实核查官  🕵️ Claude 深度挖掘官  🛡️ OpenOSINT 验证官 │
│  （3 Agent 并行取证，各自调用搜索工具链）                 │
│  工具：360 搜索 + Claude Code CLI + 来源可信度评级       │
└─────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────┐
│ 阶段 3：合议庭仲裁                                     │
│  ⚖️ 仲裁官 1  ⚖️ 仲裁官 2  ⚖️ 仲裁官 3              │
│  （3 人独立审议全部证据 → 各自裁定 true/false/unverifiable）│
│          ↓                                            │
│  👨‍⚖️ 首席仲裁官 → 确认共识 + 标记争议 + 最终裁定        │
└─────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────┐
│ 阶段 4：品质审核官                                     │
│  📝 报告生成 → 🛡️ 4 维质量自评                        │
│  输出：综合判定 + 证据溯源网络 + 认知处方 + 辟谣卡片      │
└─────────────────────────────────────────────────────┘
```

### 判定结论

| 结论 | 说明 |
|------|------|
| `verdict_false` | ❌ 虚假信息 |
| `verdict_true` | ✅ 信息属实 |
| `verdict_manipulative` | ⚠️ 认知操纵 |
| `verdict_suspicious` | 🟡 信息存疑 |
| `verdict_unknown` | ⚪ 无法判定 |

---

## 功能

| 功能 | 说明 |
|------|------|
| 📝 **双模输入** | 文字粘贴 + 截图 OCR（上传或 Ctrl+V） |
| 📡 **SSE 流式推送** | 4 面板进度条实时更新，每阶段结果即时可见 |
| 🧬 **14 维指纹** | 极端数字、紧急呼吁、情绪触发、权威伪装、阴谋暗示等 |
| 🛡️ **认知战检测** | 信任瓦解 / 经济崩溃 / 社会分裂 / 政策破坏 4 种攻击模板 |
| 🔍 **三路并行取证** | 事实核查 + 深度挖掘 + 来源验证，独立关键词精准分流 |
| ⚖️ **合议庭裁定** | 3 仲裁官独立裁定 + 首席综合，防止单一偏见 |
| 🔗 **证据溯源网络** | vis.js 交互式节点图，双击来源节点打开真实 URL |
| 🛡️ **认知处方** | "怎么骗你的" + "怎么防"，面向普通读者的防骗指南 |
| 📤 **辟谣卡片** | 谣言摘要 + 真相 + 来源，一键复制分享 |
| 🕸️ **知识图谱** | 500+ 已核查案例可视化，按攻击维度/操纵手法/案例分类 |
| 💬 **用户反馈** | 准确/不准确评价，持续优化判定策略 |
| 🖼️ **图片审查** | 百度飞桨 OCR 远程 API，中英文混合识别 |

---

## 配置

### 环境变量

| 变量 | 默认值 | 必填 | 说明 |
|------|--------|------|------|
| `DEEPSEEK_API_KEY` | — | ✅ | DeepSeek API 密钥 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | 否 | API 端点 |
| `PRIMARY_MODEL` | `deepseek-v4-pro` | 否 | 主模型 |
| `SECONDARY_MODEL` | `deepseek-v4-pro` | 否 | 辅助模型 |
| `BAIDU_OCR_API_KEY` | — | 可选 | 百度飞桨 OCR（图片审查） |
| `BAIDU_OCR_SECRET_KEY` | — | 可选 | 百度飞桨 OCR Secret |
| `ANTHROPIC_BASE_URL` | `https://api.deepseek.com/anthropic` | 否 | Claude CLI 后端 |
| `HOST` | `0.0.0.0` | 否 | 服务监听地址 |
| `PORT` | `8000` | 否 | 服务端口 |
| `SIMILARITY_THRESHOLD` | `0.3` | 否 | 知识库匹配阈值 |
| `MAX_SEARCH_RESULTS` | `5` | 否 | 单次搜索最大结果数 |

---

## API

| 方法 | 端点 | 说明 | 响应 |
|------|------|------|------|
| `POST` | `/api/analyze` | 提交文本核查 | SSE 流式 (14 种事件) |
| `POST` | `/api/analyze-image` | 提交图片审查 | SSE 流式 (OCR → 核查) |
| `GET` | `/api/demo/cases` | 预设测试案例 | JSON |
| `GET` | `/api/knowledge/stats` | 知识库统计 | JSON |
| `GET` | `/api/knowledge/graph` | 知识图谱数据 | JSON (vis.js 格式) |
| `POST` | `/api/fingerprint` | 单独指纹提取 | JSON |
| `POST` | `/api/evolution` | 进化树+行为+动机 | JSON |
| `POST` | `/api/benchmark` | 基准测试 | JSON |
| `POST` | `/api/feedback` | 用户反馈 | JSON |

```bash
# 文本核查
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "中国结婚率不足1%，离婚排长队"}'

# 图片审查
curl -X POST http://localhost:8000/api/analyze-image \
  -F "file=@screenshot.png"
```

### SSE 事件类型

| 事件 | 触发时机 |
|------|---------|
| `fingerprint` | 14 维指纹提取完成 |
| `cognitive_warfare` | 认知战模板匹配完成 |
| `keywords_extracted` | 三组搜索关键词提炼完成 |
| `fp_team_complete` | 4 专家并行研判完成 |
| `agent_start` / `agent_complete` | 每个 Agent 开始/完成 |
| `parallel_complete` | 三路侦察取证完成 |
| `search_trace` | 真实搜索 URL 列表 |
| `jury_complete` | 3 仲裁官独立裁定完成 |
| `report` | 完整核查报告（最终） |
| `ocr_start` / `ocr_complete` | 图片 OCR 进度（图片审查专用） |
| `done` | 流程结束 |
| `error` | 异常信息 |

---

## 项目结构

```
EvilMind/
├── main.py                  # 启动入口
├── pyproject.toml           # Python 项目配置 (uv)
├── uv.lock                  # 依赖锁定
├── requirements.txt         # pip 依赖 (Docker 用)
├── Dockerfile               # Docker 构建
├── docker-compose.yml       # Docker 部署编排
│
├── config/                  # 配置管理 (pydantic-settings)
├── llm/                     # LLM 客户端 (DeepSeek via OpenAI SDK)
├── agents/                  # Agent 实现
│   ├── fingerprint_team.py  #   指纹对比 + 进化树 + 意图挖掘 + 风险评估 + 综合研判
│   ├── claude_checker.py    #   事实核查官（精准逐条验证）
│   ├── claude_diver.py      #   深度挖掘官（背景 + 舆论趋势）
│   ├── search_osint.py      #   来源验证官（域名可信度评级）
│   ├── jury.py              #   合议庭仲裁官（独立裁定 + 首席综合）
│   └── publisher.py         #   品质审核官（报告 + 4 维自评）
├── pipeline/                # 4 阶段管道编排
├── knowledge/               # 知识库 + 14 维指纹 + 进化树 + 认知战检测
├── search/                  # 360 搜索 + 百度飞桨 OCR HTTP API
├── tools/                   # Claude Code CLI + OpenOSINT + Playwright
├── api/                     # FastAPI 后端 (SSE 流式)
├── web/                     # 前端
│   ├── landing.html         #   产品宣传首页
│   ├── app.html             #   审查研判工具
│   ├── app.js               #   前端逻辑 (SSE 事件处理)
│   ├── guide.html           #   使用说明文档
│   └── style.css            #   样式
├── data/                    # 种子数据 + 微博谣言库 + 测试集
├── reports/                 # 报告生成模块
└── docs/                    # LaTeX 使用手册
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **LLM** | DeepSeek-v4-pro (OpenAI SDK) |
| **后端** | FastAPI + uvicorn + SSE |
| **前端** | Vanilla JS + Tailwind CSS + vis.js |
| **搜索引擎** | 360 搜索 + Claude Code CLI + OpenOSINT |
| **OCR** | 百度飞桨远程 API |
| **知识库** | Chromadb + Bigram 相似度 |
| **容器化** | Docker + docker-compose |
| **包管理** | uv (PyPI 清华镜像) |

---

## 性能指标

### 管道耗时

| 阶段 | API 调用 | 并行模式 | 典型耗时 |
|------|---------|---------|---------|
| 阶段 1：指纹研判 | 5 次（4 并行 + 1 串行） | 4 Agent 并行 → 综合 | 15-30s |
| 阶段 2：三路侦察 | 3+ 次（含工具调用轮次） | 3 Agent 并行各自搜索 | 20-40s |
| 阶段 3：合议庭仲裁 | 4 次（3 并行 + 1 串行） | 3 仲裁官并行 → 首席 | 10-20s |
| 阶段 4：品质审核 | 2 次（1 报告 + 1 自评） | 串行 | 15-25s |
| **总计** | **~15 次** | | **60-120s** |

### 知识库性能

| 指标 | 数值 |
|------|------|
| 案例库规模 | 500+ 条已核查案例 |
| 匹配算法 | Bigram 字符级相似度 |
| 匹配阈值 | 0.3（相似度 ≥0.6 注入上下文，≥0.9 给出参考但不短路） |
| 指纹维度 | 14 维（极端数字/紧急呼吁/情绪触发/权威伪装等） |

### Docker 镜像

| 指标 | 数值 |
|------|------|
| 基础镜像 | Ubuntu 24.04 LTS |
| 镜像体积 | ~2.6 GB（含 Python + Node.js + Claude CLI） |
| Python 包 | 103 个（纯 HTTP 调用，无本地 ML 模型） |
| 内存占用 | ~800MB（ChromaDB + uvicorn workers） |

---

## FAQ

<details>
<summary><b>Q: 一次完整核查需要多长时间？</b></summary>

约 **60-120 秒**。指纹团队 5 次 API 调用（4 并行 + 1 串行）、侦察兵 3 次（并行，含多轮工具调用）、合议庭 4 次（3 并行 + 1 串行）、审核 2 次（串行）。实际耗时取决于搜索轮数和网络延迟。
</details>

<details>
<summary><b>Q: 搜索结果为什么可能查不到内容？</b></summary>

- 360 搜索引擎对最新发布的内容有索引延迟
- 社交媒体平台（微博/小红书）的封闭性限制内容被抓取
- 系统通过 Claude Code CLI 搜索作为补充渠道
- 在搜索结果页可查看所有实际访问过的 URL
</details>

<details>
<summary><b>Q: LLM 会不会编造搜索关键词？</b></summary>

不会。指纹研判官提炼关键词后，经 `_enforce_year_tags()` 自动注入年份标签，写入各侦察兵的 user prompt。v2.0.1 已修复 `chat_with_tools` 中 user prompt 未正确加入 messages 的 Bug，确保 LLM 使用正确的搜索关键词。
</details>

<details>
<summary><b>Q: 知识库匹配到案例后会短路管道吗？</b></summary>

**不会**。即使 KB 相似度 ≥0.9，信息仍走完整 4 阶段管道。知识库作为辅助上下文（kb_context/kb_hint）注入各 Agent prompt，不替代实际搜索验证。这确保每一条信息都经过实时搜索验证。
</details>

<details>
<summary><b>Q: 图片审查需要什么配置？</b></summary>

需要百度飞桨 OCR 的 API Key 和 Secret Key（在 `.env` 中配置 `BAIDU_OCR_API_KEY` 和 `BAIDU_OCR_SECRET_KEY`）。纯文字核查不需要。OCR 采用 HTTP API 调用，不依赖本地模型。
</details>

<details>
<summary><b>Q: Docker 中 Claude Code CLI 如何工作？</b></summary>

镜像内置 `@anthropic-ai/claude-code` npm 包，通过环境变量 `ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic` 路由到 DeepSeek 的 Anthropic 兼容端点，复用 `DEEPSEEK_API_KEY`。无需独立 Anthropic 账号。
</details>

<details>
<summary><b>Q: 支持私有化部署吗？</b></summary>

支持。Docker 镜像可在政务内网/企业专网中运行，仅需 DeepSeek API 连通性。所有数据（知识库、报告、搜索缓存）存储在容器挂载卷中，数据不出域。
</details>

<details>
<summary><b>Q: 报告可以在哪些地方查看？</b></summary>

- 前端 `/app` 页面：完整可视化报告（判定卡片 + 证据网络图 + 认知处方 + 辟谣卡片）
- `reports/` 目录：JSON 格式完整报告（含所有中间分析结果）
- 知识图谱 `/app` → 点击"知识图谱"可查看所有历史核查案例
</details>

<details>
<summary><b>Q: 如何验证核查结果的准确性？</b></summary>

每条证据附带真实搜索 URL，可直接点击打开原文验证。前端证据网络图双击来源节点可直接跳转。系统内置 15 条标注了 ground_truth 的测试集，可通过 `/api/benchmark` 运行基准测试评估准确率。
</details>

---

## License

[GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html)
