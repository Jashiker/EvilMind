# 🛡️ 邪恶思潮 EvilMind

<div align="center">

**零信任多 Agent 谣言核查系统** · 4 阶段严格管道 · SSE 实时流式 · 证据可溯源

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek--v4-536DFE)](https://deepseek.com)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker)](https://docs.docker.com)
[![License](https://img.shields.io/badge/License-MIT-green)](./LICENSE)

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

## License

MIT
