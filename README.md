# 🛡️ 邪恶思潮 — 零信任多Agent谣言核查系统

基于 DeepSeek-v4-pro 的4阶段10 Agent协作谣言核查系统。指纹研判→三路侦察取证→合议庭裁定→品质审核，全流程 SSE 实时推送。

## 快速开始

```bash
cp .env.example .env          # 填入 DEEPSEEK_API_KEY
uv sync                       # 安装依赖
uv run python main.py         # 启动 http://localhost:8000
```

访问 `/app` 使用研判工具，`/guide` 查看使用说明。

## 架构

```
用户输入 → 知识库检索
  → 阶段1: 指纹研判团队 (5专家并行 → 综合研判官 → 邪恶评分+关键词)
  → 阶段2: 三路侦察兵 (事实核查+深度挖掘+来源验证 并行取证)
  → 阶段3: 合议庭仲裁 (3仲裁官独立裁定 → 首席综合)
  → 阶段4: 品质审核官 (报告生成 → 4维质量自评)
  → 输出: 综合判定 + 证据溯源网络 + 认知处方 + 辟谣卡片
```

## Docker 部署

```bash
docker compose up -d           # 需要 .env 中配置 DEEPSEEK_API_KEY
```

镜像包含 Claude Code CLI (Agent 搜索) 和 OpenCode CLI (页面抓取降级)。

## 技术栈

- **LLM**: DeepSeek-v4-pro (OpenAI SDK 兼容)
- **前端**: Vanilla JS + Tailwind CSS + vis.js + SSE
- **后端**: FastAPI + uvicorn
- **搜索**: 360搜索 + Claude Code CLI + OpenOSINT
- **OCR**: 百度飞桨 (远程 API)
- **知识库**: ChromaDB + Bigram 相似度

## 配置

| 变量 | 说明 | 必填 |
|------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | ✅ |
| `BAIDU_OCR_API_KEY` | 百度飞桨 OCR (图片审查) | 可选 |
| `BAIDU_OCR_SECRET_KEY` | 百度飞桨 OCR Secret | 可选 |

## 项目结构

```
├── main.py              # 启动入口
├── config/              # 配置 (pydantic-settings)
├── llm/                 # LLM 客户端 (DeepSeek via OpenAI SDK)
├── agents/              # 10 Agent 实现
│   ├── fingerprint_team.py  # 指纹对比+进化树+意图挖掘+风险评估+综合
│   ├── claude_checker.py    # 事实核查官
│   ├── claude_diver.py      # 深度挖掘官
│   ├── search_osint.py      # 来源验证官
│   ├── jury.py              # 合议庭仲裁官
│   └── publisher.py         # 品质审核+发布官
├── pipeline/            # 4阶段管道编排
├── knowledge/           # 知识库+指纹+进化树+认知战检测
├── search/              # 360搜索 + OCR
├── tools/               # Claude CLI + OpenOSINT 工具
├── api/                 # FastAPI (SSE 流式)
├── web/                 # 前端 (landing + app + guide)
├── data/                # 种子数据 + 测试集
├── reports/             # 报告生成
├── docs/                # 文档 (LaTeX 手册)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## License

MIT
