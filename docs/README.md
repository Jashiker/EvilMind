# 邪恶思潮 — 技术文档

> 零信任多Agent认知战防御与舆情治理平台

---

## 目录

1. [产品概述](#1-产品概述)
2. [系统架构](#2-系统架构)
3. [多Agent协作管道](#3-多agent协作管道)
4. [14维谣言指纹识别](#4-14维谣言指纹识别)
5. [认知战攻击检测](#5-认知战攻击检测)
6. [多源搜索与验证](#6-多源搜索与验证)
7. [合议庭辩论裁定](#7-合议庭辩论裁定)
8. [证据溯源与可视化](#8-证据溯源与可视化)
9. [知识库体系](#9-知识库体系)
10. [图片OCR审查](#10-图片ocr审查)
11. [360生态联动](#11-360生态联动)
12. [API参考](#12-api参考)
13. [部署方案](#13-部署方案)
14. [配置参考](#14-配置参考)
15. [常见问题](#15-常见问题)

---

## 1. 产品概述

### 1.1 产品定位

**邪恶思潮**是一款基于零信任模型的认知战防御系统，专为政府舆情监管部门和企业安全团队设计。系统采用 **14个专职Agent协作架构**，实现从指纹提取、多源并行搜索、证据辩论合成到品质自我评估的全自动化核查流水线。

### 1.2 核心能力

| 能力 | 说明 |
|------|------|
| 指纹研判团队 | 5位专家并行分析：指纹对比、进化树、意图挖掘、风险评估、综合研判 |
| 三路侦察兵 | 360搜索 + Firecrawl + OpenOSINT 并行取证 + 交叉辩论 |
| 合议庭裁定 | 3位仲裁官独立审议 + 首席仲裁官综合判决 |
| 14维指纹 | 极端数字、紧急呼吁、情绪触发、权威伪装等14种特征自动检测 |
| 认知战检测 | 4种攻击模板(信任瓦解/经济崩溃/社会分裂/政策破坏) |
| 证据溯源 | 每条判定附带可点击URL，vis.js网络图可视化交叉验证 |
| 认知处方 | 面向普通读者的通俗防骗指南 |
| 知识库 | 583条案例 + 指纹匹配 + 进化树分析 |
| 图片审查 | 百度飞桨OCR远程API + 核查流水线 |

### 1.3 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 大模型 | DeepSeek-v4-pro | 全部14个Agent推理引擎 |
| 搜索 | 360搜索(so.com) | 中文官方数据源索引 |
| 抓取 | Firecrawl(本地:3002) | 网页Markdown提取 |
| 验证 | OpenOSINT | 域名可信度5级评级 |
| OCR | 百度飞桨OCR | 图片文字提取 |
| 后端 | FastAPI + SSE | 流式推送 |
| 前端 | Vanilla JS + Tailwind CSS | 4面板实时显示 |
| 知识库 | JSON + Bigram相似度 | 583条案例存储 |
| 图谱 | vis.js | 证据网络 + 知识图谱 |

---

## 2. 系统架构

### 2.1 整体架构图

```
用户输入(文本/图片)
    │
    ▼
┌─────────────────────────────────────────────┐
│  阶段一: 指纹研判团队 (5 Agent 并行)         │
│                                              │
│  🧬 指纹对比官 ──→ 14维指纹 + KB匹配        │
│  🌳 进化树分析师 ──→ 变异模式 + 演化阶段     │
│  🔍 意图挖掘官 ──→ 认知操纵 + 心理战术       │
│  ⚠️ 风险评估官 ──→ 舆论风险 + 影响判定      │
│       │                                      │
│       ▼                                      │
│  ⚖️ 综合研判官 ──→ 综合4专家形成研判报告    │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│  阶段二: 三路侦察兵 (3+3 Agent)             │
│                                              │
│  🔍 360搜索 ──→ web_search + fetch_url      │
│  🔥 Firecrawl ──→ search + scrape           │
│  🛡️ OpenOSINT ──→ verify_source_credibility │
│       │                                      │
│       ▼ 交叉辩论                             │
│  360审查FC+OSINT │ FC审查360+OSINT           │
│  OSINT审查360+FC                             │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│  阶段三: 合议庭 (3+1 Agent)                 │
│                                              │
│  仲裁官1 ──→ 独立裁定                       │
│  仲裁官2 ──→ 独立裁定  (并行)               │
│  仲裁官3 ──→ 独立裁定                       │
│       │                                      │
│       ▼                                      │
│  首席仲裁官 ──→ 综合3方意见，最终判决       │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│  阶段四: 品质审核官                          │
│  四维质量评估: 证据充分·置信合理·核查完整    │
│  ·结论严谨                                   │
└─────────────────────────────────────────────┘
    │
    ▼
  输出: 证据链 + 认知处方 + 辟谣卡片 + 品质报告
```

### 2.2 文件结构

```
MindHacks/
├── main.py                        # 启动入口
├── config/
│   ├── __init__.py                # 全局配置(DeepSeek/360/OCR)
│   └── categories.py              # 6类操纵手法定义
├── llm/
│   └── client.py                  # DeepSeek API客户端(chat/chat_json/chat_with_tools)
├── agents/
│   ├── base.py                    # Agent基类
│   ├── verification_agents.py     # 指纹研判团队(5 Agent)
│   ├── search_360.py              # 360搜索Agent
│   ├── search_firecrawl.py        # Firecrawl搜索Agent
│   ├── search_osint.py            # OpenOSINT验证Agent
│   ├── debate_synthesizer.py      # 辩论合成官(仲裁官+首席)
│   └── truth_publisher.py         # 报告生成+品质审核
├── pipeline/
│   └── orchestrator.py            # 14 Agent编排器
├── search/
│   ├── web_search.py              # 360搜索(so.com) + Bing/Google fallback
│   └── ocr.py                     # 百度飞桨OCR远程API
├── knowledge/
│   ├── store.py                   # 知识库(案例+模式+BGram相似度)
│   ├── fingerprint.py             # 14维指纹提取
│   ├── evolution.py               # 进化树+行为动机分析
│   └── cognitive_warfare.py       # 认知战攻击模板
├── tools/
│   ├── firecrawl_tool.py          # Firecrawl本地部署+混合搜索
│   └── openosint_tool.py          # OpenOSINT域名验证
├── api/
│   └── server.py                  # FastAPI路由+SSE流式
└── frontend/
    ├── landing.html               # 产品宣传页
    ├── app.html                   # 审查研判工具
    ├── app.js                     # 前端逻辑(SSE+DOM更新)
    ├── guide.html                 # 使用说明
    └── style.css                  # 样式(浅色/深色主题)
```

---

## 3. 多Agent协作管道

### 3.1 LLM客户端 (`llm/client.py`)

所有Agent统一通过 `LLMClient` 调用 DeepSeek-v4-pro API：

```python
class LLMClient:
    async def chat(prompt, system, model, json_mode) -> str
    async def chat_json(prompt, system, model) -> dict     # JSON模式+降级
    async def chat_with_tools(prompt, system, tools, executor, max_rounds) -> str
    async def chat_stream(prompt, system, model) -> AsyncIterator[str]
```

- `chat_json`: 先尝试 `response_format: json_object`，失败后降级为普通模式手动提取JSON
- `chat_with_tools`: 执行工具调用循环，工具执行后移除tools强制输出文本

### 3.2 BaseAgent (`agents/base.py`)

```python
class BaseAgent:
    def __init__(self, llm, knowledge):  # llm = LLMClient实例
    async def run(self, input_data: dict) -> dict
    @staticmethod _extract_json(text: str) -> dict  # 从文本提取JSON
```

### 3.3 管道编排器 (`pipeline/orchestrator.py`)

```python
class PipelineOrchestrator:
    def __init__(self, llm, knowledge, report_gen):
        # 指纹团队: 5 Agent
        self.fp_verifier = FingerprintVerifier(llm, knowledge)
        self.evo_analyst = EvolutionAnalyst(llm, knowledge)
        self.intent_miner = IntentMiner(llm, knowledge)
        self.risk_assessor = RiskAssessor(llm, knowledge)
        self.synthesis_judge = SynthesisJudge(llm, knowledge)
        # 搜索团队: 3 Agent
        self.agent_360 = Search360Agent(llm, knowledge)
        self.agent_fc = FirecrawlSearchAgent(llm, knowledge)
        self.agent_osint = OpenOSINTAgent(llm, knowledge)
        # 辩论: 1 Agent(复用3+1次)
        self.debater = DebateSynthesizer(llm, knowledge)
        # 发布: 1 Agent
        self.publisher = TruthPublisherAgent(llm, knowledge)
```

**管道流程**:
1. 知识库检索(583条) + KB上下文构建
2. 指纹提取(14维) + 行为动机分析 + 进化树
3. 认知战攻击模式检测(4种模板)
4. **指纹研判团队**: 4专家并行 → 综合研判官
5. **三路侦察兵**: 3路并行取证 → 交叉辩论(各Agent审查他人)
6. **合议庭**: 3仲裁官并行裁定 → 首席仲裁官最终判决
7. 报告生成 + 品质审核 + 入库

**每个Agent有完整工具链**: `web_search + fetch_url + firecrawl_search + firecrawl_scrape + verify_source_credibility`

管道通过 `asyncio.gather` 实现Agent间的并行执行，SSE事件实时推送到前端。

### 3.4 SSE事件流

| 事件 | 携带数据 | 触发时机 |
|------|---------|---------|
| `fingerprint` | 14维特征+风险等级 | 指纹提取后 |
| `behavior_motivation` | 行为分析+动机分析 | 动机分析后 |
| `cognitive_warfare` | 认知战模板匹配 | 攻击检测后 |
| `kb_assist` | KB匹配统计 | KB匹配时 |
| `fp_team_complete` | 4专家分析结果 | 指纹团队完成 |
| `agent_start` | Agent名称+状态 | 每个Agent开始时 |
| `agent_complete` | Agent输出数据 | 每个Agent完成时 |
| `parallel_start` | 并行取证开始 | 三路搜索开始时 |
| `parallel_complete` | 3路搜索结果 | 三路搜索完成时 |
| `cross_debate_complete` | 交叉审查结果 | 交叉辩论完成时 |
| `jury_complete` | 3位仲裁官裁定 | 合议庭完成时 |
| `search_trace` | 可点击URL列表 | 搜索结果提取后 |
| `report` | 完整核查报告 | 全部完成后 |
| `done` | 完成标识 | 流程结束 |

**总计约20+个SSE事件**，前端通过 `fetch + ReadableStream` 消费。

---

## 4. 14维谣言指纹识别

### 4.1 指纹特征表

| # | 特征 | 检测关键词 | 关联分类 |
|---|------|---------|---------|
| 1 | 极端数字 | `暴跌\d+%` `暴涨\d+` `突破\d+` `不足.*%` | 数据伪造 |
| 2 | 紧急呼吁 | `紧急扩散` `求转发` `速看` `马上删` | 情绪劫持 |
| 3 | 情绪触发 | `愤怒` `泪目` `震惊` `可怕` `崩溃` | 情绪劫持 |
| 4 | 声称权威 | `央视` `官方` `通知` `教育部` `央行` `国务院` | 权威伪装 |
| 5 | 身份绑定 | `年轻人` `父母` `中国人` `作为XX必须` | 信息投喂 |
| 6 | 画面描述 | `排长队` `血淋淋` `哭成一片` `监控画面` | 叙事移植 |
| 7 | 阴谋暗示 | `背后` `黑幕` `掩盖` `不让说` `被和谐` | 信任腐蚀 |
| 8 | 全称否定 | `都是假的` `没有真相` `谁也不信` | 信任腐蚀 |
| 9 | 时空模糊 | `某地` `近日` `据说` `网传` `有消息称` | 叙事移植 |
| 10 | 行动号召 | `转起来` `让更多人看到` `必须曝光` `扩散` | 情绪劫持 |
| 11 | 数据声明 | `\d+万` `\d+亿` `\d+%` `\d+倍` | 数据伪造 |
| 12 | 道德评判 | `无耻` `天理难容` `丧尽天良` | 情绪劫持 |
| 13 | 对立叙事 | `他们vs我们` `底层vs权贵` `穷人vs富人` | 信任腐蚀 |
| 14 | 健康恐慌 | `致癌` `有毒` `超标` `辐射` `感染` | 情绪劫持 |

### 4.2 风险分级

- **高风险(🔴)**: ≥6个特征命中
- **中风险(🟡)**: ≥3个特征命中
- **低风险(🟢)**: <3个特征命中

### 4.3 指纹研判团队

每个特征由专门的Agent负责深度分析：

| Agent | 职责 | LLM调用 |
|-------|------|---------|
| 指纹对比官 | 14维特征提取 + 知识库相似案例匹配 | `chat_json` |
| 进化树分析师 | 谣言演变历史追溯 + 变异模式识别 | `chat_json` |
| 意图挖掘官 | 认知操纵深度挖掘 + 心理战术识别 | `chat_json` |
| 风险评估官 | 舆论风险等级 + 社会影响预测 | `chat_json` |
| 综合研判官 | 综合4专家分析 → 邪恶评分 + 恶意假设 | `chat_json` |

---

## 5. 认知战攻击检测

### 5.1 攻击模板

内置4种认知战攻击模板(`knowledge/cognitive_warfare.py`)，通过正则匹配识别：

| 模板 | 威胁等级 | 检测指标 | 360联动 |
|------|---------|---------|---------|
| 系统性信任瓦解 | Critical | `都是假的` `官方数据.*假` `政府.*隐瞒` | 360安全大脑标记传播源头 |
| 经济崩溃叙事 | Critical | `暴跌\d+%` `崩盘` `GDP.*被.*超越` | 360搜索交叉验证经济数据 |
| 社会分裂工程 | High | `年轻人.*躺平` `富人.*穷人` `他们.*我们` | 360浏览器内容预警 |
| 政策破坏攻击 | High | `教育部.*通知` `国务院.*发布` `红头文件` | 360安全大脑格式验证 |

### 5.2 检测流程

```python
def detect_attack_patterns(text: str) -> dict:
    # 1. 遍历4个模板，正则匹配
    # 2. 统计命中指标数
    # 3. 评估威胁等级(critical/high/medium/none)
    # 4. 生成360联动建议
    return {
        "matched_templates": [...],
        "threat_level": "critical",
        "template_count": 2,
        "360_recommendation": "360安全大脑建议..."
    }
```

---

## 6. 多源搜索与验证

### 6.1 360搜索 (`search/web_search.py`)

- **主引擎**: 360搜索(so.com)，HTML解析
- **优势**: 中文官方数据源(.gov.cn)优先索引
- **Fallback链**: 360 → Bing → Google
- **官方来源识别**: `.gov.cn`域名 + 官方关键词匹配
- **搜索统计**: `_stats`追踪搜索次数、结果数、官方命中数

```python
async def search_360(query, max_results=5):
    # 1. GET so.com/s?q=query
    # 2. BeautifulSoup解析 .result .res-list
    # 3. 提取 title/url/snippet + is_official标记
    return [{"title":"...","url":"...","snippet":"...","source":"360搜索","is_official":True}]
```

### 6.2 Firecrawl (`tools/firecrawl_tool.py`)

- **本地部署**: `http://localhost:3002`
- **Redis**: `localhost:6379` (BullMQ队列)
- **混合策略**: 360搜索发现URL → Firecrawl `/v1/scrape` 精读原文
- **超时**: 60秒
- **内容限制**: 5000字符(scrape) / 1500字符(search)

```python
async def firecrawl_search(query, api_key="", max_results=3):
    # 1. 调用360搜索获取URL列表
    # 2. 对每个URL调用 /v1/scrape 获取Markdown
    # 3. 返回 title + url + content
```

### 6.3 OpenOSINT (`tools/openosint_tool.py`)

- **域名可信度评级**: 5级(official/trusted_media/academic/commercial/unknown)
- **官方域名库**: `.gov.cn`、统计局、央行、教育部等30+官方域名
- **可信媒体库**: 新华社、人民日报、央视等8个媒体域名
- **评分**: official=95, trusted_media=80, academic=65, commercial=35, unknown=30

```python
def verify_source_credibility(url_or_domain: str) -> dict:
    return {
        "domain": "stats.gov.cn",
        "tier": "official",
        "score": 95,
        "is_gov": True,
        "verified": True
    }
```

### 6.4 三路并行协作

3个Agent各自拥有完整工具链(`full_tools = search_tools + fc_tools + osint_tools`)，可独立完成搜索→抓取→验证全流程：

```
Agent 1 (360搜索):
  web_search("2026年GDP 国家统计局") → 找到stats.gov.cn
  → firecrawl_scrape("stats.gov.cn/...") → 获取原文
  → verify_source_credibility("stats.gov.cn") → official/95分

Agent 2 (Firecrawl):
  firecrawl_search("2026年GDP") → 360搜索+FC精读
  → web_search("IMF 中国GDP") → 交叉验证
  → verify_source_credibility("imf.org") → academic/65分

Agent 3 (OpenOSINT):
  verify_source_credibility(all_domains) → 可信度评级
  → web_search("GDP数据 官方来源") → 补充搜索
  → firecrawl_scrape("stats.gov.cn/...") → 深度验证
```

---

## 7. 合议庭辩论裁定

### 7.1 辩论合成官 (`agents/debate_synthesizer.py`)

**第一轮: 仲裁官独立裁定**

3个仲裁官并行审议两轮证据(首轮+交叉审查)，各自独立判决：

```python
jury_results = await asyncio.gather(
    self.debater.run(debate_input),  # 仲裁官1
    self.debater.run(debate_input),  # 仲裁官2
    self.debater.run(debate_input),  # 仲裁官3
)
```

每个仲裁官输出:
```json
{
  "cross_validation": {"total_sources":4, "agreeing_sources":3, "quality":"high"},
  "final_verdict": {"conclusion":"false", "confidence":0.95},
  "consensus": {"confirmed":["多方印证的事实"], "disputed":["存在争议的发现"]}
}
```

**第二轮: 首席仲裁官综合判决**

首席仲裁官拿到3位仲裁官的独立裁定，综合形成最终判决。

### 7.2 辩论原则

- **多方印证优先**: ≥2个信源支持的结论置信度高
- **官方数据优先**: `.gov.cn` > 官方媒体 > 商业网站
- **证据不足即标注**: 不确定的不硬判
- **交叉验证加分**: 不同来源相互印证时提升置信度

---

## 8. 证据溯源与可视化

### 8.1 搜索溯源 (`search_trace` SSE事件)

每次核查后，`_build_search_trace`函数从3路Agent的原始搜索结果中提取真实URL：

```python
def _build_search_trace(findings_360, findings_fc, findings_osint, debate):
    # 1. 遍历每个Agent的findings→sources
    # 2. 过滤: 只保留http/https开头的真实URL
    # 3. 去重: URL去重
    # 4. 附加: 辩论中的强证据源
    return {"agents": [
        {"name":"360搜索", "sources":[{"title":"...","url":"...","snippet":"..."}]},
        {"name":"Firecrawl搜索", "sources":[...]},
        {"name":"OpenOSINT验证", "sources":[...]},
    ]}
```

### 8.2 证据网络图 (`renderEvidenceNetwork`)

使用vis.js渲染节点网络图：

```
📋 待核查信息 (蓝色方块)
  ├── 🔍 声明1 (深色方块·红色边框=虚假)
  │     └── 📎 来源 (青色圆点·双击打开URL)
  │           └── ❌ 虚假 (红色菱形)
  ├── 🔍 声明2
  │     └── 📎 来源
  │           └── ❌ 虚假
  │                 ↑ 虚线=交叉验证(同判定)
```

图配置:
- `forceAtlas2Based` 物理引擎
- `curvedCW` 曲线连线
- 双击来源节点 `window.open(url)` 打开真实网页
- 同判定节点虚线连接表示交叉验证

### 8.3 证据链详情

每条证据以节点卡片形式展示：

```
#1  ❌ 虚假
  📝 原文声明: "结婚率不足1%"
  🔍 溯源搜索: 360搜索 "结婚率 国家统计局 2024"
  🔗 stats.gov.cn/... (可点击)
  💡 发现: 官方数据结婚率4.3‰，原文偏差5.4倍
  ↕ 交叉验证: 2个独立信源一致确认
```

### 8.4 来源可信度评分

| 来源类型 | 评分 | 说明 |
|---------|------|------|
| 官方数据(.gov.cn) | 90% | 政府网站域名验证 |
| 多源交叉验证(≥2源) | 85% | 多方独立来源印证 |
| Firecrawl深度抓取 | 80% | 原文Markdown提取确认 |
| 知识库案例匹配 | 50-90% | 取决于相似度 |
| LLM逻辑推演 | 60-65% | 辅助推理 |

---

## 9. 知识库体系

### 9.1 案例存储 (`knowledge/store.py`)

```python
class KnowledgeStore:
    def __init__(self):
        self._cases: dict     # 583条案例
        self._patterns: dict  # 8种操纵模式
        self._feedback_log    # 用户反馈记录

    def add_case(text, verdict, category, evil_score, report)
    def search_similar(text, top_k=3)    # Bigram相似度检索
    def search_patterns(text, top_k=3)   # 模式匹配
    def record_feedback(text, is_correct) # 反馈记录
    def load_seed_data(seed_path)         # 种子数据加载
```

- **相似度算法**: Jaccard on character bigrams (零依赖,启动零延迟)
- **持久化**: JSON文件 `data/knowledge_db.json`
- **种子数据**: 20条基础案例 + 500条微博谣言

### 9.2 进化树 (`knowledge/evolution.py`)

```python
def build_evolution_tree(text, knowledge_store, max_variants=20):
    # 1. 在583条案例中搜索指纹相似的变体
    # 2. 按综合相似度排序(text_sim*0.4 + feature_sim*0.6)
    # 3. 找到根节点(最早变体)
    # 4. 构建进化边(时间+相似度)
    # 5. 分析变异模式(category_shift/intensity_change/multi_strain)
```

### 9.3 行为动机分析

```python
def analyze_behavior(text, fingerprint) -> dict:
    # 操纵风格: 数据+情绪双杀 / 权威绑架 / 信任腐蚀 / 叙事移植
    # 传播机制: 社交裂变 / 群体共振 / 信任传递 / 信息级联
    # 认知目标: 锚定效应 / 情绪启发式 / 权威偏见 / 道德义愤
```

---

## 10. 图片OCR审查

### 10.1 OCR流程 (`search/ocr.py`)

```python
async def ocr_image(image_bytes, api_key="", secret_key=""):
    # 1. 图片→base64编码
    # 2. OAuth获取access_token (缓存30天)
    # 3. POST /rest/2.0/ocr/v1/accurate_basic
    # 4. CHN_ENG语言 + 方向检测
    # 5. 返回提取文字
```

### 10.2 前端流程

1. 用户上传图片(点击/Ctrl+V/拖拽)
2. 图片预览显示
3. 点击"图片审查" → `/api/analyze-image` (multipart)
4. OCR提取文字 → 送入完整核查流水线
5. 前端OCR卡片显示提取结果

---

## 11. 360生态联动

### 11.1 已实现联动

| 产品 | 联动方式 | 实现细节 |
|------|---------|---------|
| 360搜索 | 核心搜索引擎 | HTML解析so.com，官方来源标记，搜索统计 |
| 360安全大脑 | 认知战检测 | 攻击模板含360联动建议，标记传播源头 |
| 360浏览器 | 架构预留 | 插件接口设计，浏览时一键提交核查 |

### 11.2 360搜索优势

- 对 `.gov.cn` 域名优先索引策略
- 中文分词和语义理解优于国际搜索引擎
- 国内新闻和政策时效性覆盖更全面
- 搜索词自动包含当前年份(管道注入日期上下文)
- `_is_official_source()` 函数自动识别官方来源

---

## 12. API参考

### 12.1 端点列表

| 方法 | 端点 | 说明 | 响应 |
|------|------|------|------|
| POST | `/api/analyze` | 文本核查 | SSE流式 |
| POST | `/api/analyze-image` | 图片审查 | SSE流式(multipart) |
| GET | `/api/knowledge/stats` | 知识库统计 | JSON |
| GET | `/api/knowledge/graph` | 知识图谱 | JSON(vis.js) |
| POST | `/api/fingerprint` | 指纹分析 | JSON |
| POST | `/api/evolution` | 进化树+行为动机 | JSON |
| POST | `/api/benchmark` | 基准测试 | JSON |
| POST | `/api/feedback` | 用户反馈 | JSON |

### 12.2 文本核查请求

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "中国结婚率不足1%，离婚排长队"}'
```

响应为SSE流，`Content-Type: text/event-stream`。

### 12.3 图片审查请求

```bash
curl -X POST http://localhost:8000/api/analyze-image \
  -F "file=@screenshot.png"
```

---

## 13. 部署方案

### 13.1 环境要求

- Python ≥ 3.11
- uv (Python包管理器)
- DeepSeek API Key (必需)
- Redis (Firecrawl本地部署需要)
- Node.js + pnpm (Firecrawl本地部署需要)

### 13.2 安装步骤

```bash
# 1. 克隆项目
git clone <repo-url> MindHacks && cd MindHacks

# 2. 安装Python依赖
uv sync

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 4. (可选)启动Redis
redis-server --daemonize yes

# 5. (可选)启动本地Firecrawl
cd /path/to/firecrawl/apps/api
pnpm install && npx tsc --skipLibCheck
REDIS_URL=redis://localhost:6379 USE_DB_AUTHENTICATION=false PORT=3002 \
  nohup node dist/src/index.js &

# 6. 启动主服务
uv run python main.py
# 访问 http://localhost:8000
```

### 13.3 部署模式

| 模式 | 适用场景 | 数据安全 |
|------|---------|---------|
| ☁️ SaaS云端 | 中小团队、快速验证 | 标准 |
| 🏛️ 私有化 | 政务内网、企业专网 | 高(数据不出域) |
| 🔗 混合云 | 360生态集成 | 可控 |

---

## 14. 配置参考

| 变量 | 默认值 | 说明 | 必填 |
|------|--------|------|------|
| `DEEPSEEK_API_KEY` | — | DeepSeek API密钥 | ✅ |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | API地址 | 否 |
| `PRIMARY_MODEL` | `deepseek-v4-pro` | 模型名 | 否 |
| `HOST` | `0.0.0.0` | 监听地址 | 否 |
| `PORT` | `8000` | 监听端口 | 否 |
| `BAIDU_OCR_API_KEY` | — | 百度OCR Key | OCR需要 |
| `BAIDU_OCR_SECRET_KEY` | — | 百度OCR Secret | OCR需要 |
| `FIRECRAWL_API_KEY` | — | Firecrawl Key(本地部署无需) | 否 |
| `MAX_SEARCH_RESULTS` | `5` | 搜索结果数 | 否 |
| `REQUEST_TIMEOUT` | `90.0` | LLM超时(秒) | 否 |

---

## 15. 常见问题

**Q: 图片审查报错"百度OCR错误(18)"?**
A: 百度免费API有QPS限制(2次/秒)，等待几秒重试即可。

**Q: 360搜索返回0结果?**
A: 系统自动降级到Bing→Google Fallback链，不影响核查。

**Q: Firecrawl搜索不到结果?**
A: 本地Firecrawl搜索需要额外配置搜索引擎后端。当前使用混合策略：360搜索发现URL → Firecrawl精读内容。

**Q: LLM输出无法解析为JSON?**
A: 系统内置双重降级机制：先尝试`json_mode`，失败后自动用普通模式重试并手动提取JSON。同时strip掉`<function_calls>`等工具调用标记。

**Q: 知识库案例太多导致启动慢?**
A: 当前583条案例启动约3秒。Bigram相似度为O(n)，每次搜索<30ms。如需重置，删除`data/knowledge_db.json`。

**Q: 管道为什么需要~120秒?**
A: 14个Agent各自调用DeepSeek-v4-pro API，每组并行执行。指纹团队5次调用、侦察兵3+3次、合议庭3+1次、发布+审核2次，总计约10组并行API调用。

---

> 邪恶思潮 v2.0 · 零信任多Agent认知战防御与舆情治理平台 · MindHacks 赛道三
