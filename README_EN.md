# 🛡️ EvilMind — Zero-Trust Multi-Agent Rumor Verification System

<div align="center">

**Zero-Trust Rumor Verification** · 4-Stage Pipeline · SSE Streaming · Verifiable Evidence

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek--v4-536DFE)](https://deepseek.com)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker)](https://docs.docker.com)
[![License](https://img.shields.io/badge/License-GPLv3-blue)](./LICENSE)

[中文版](./README.md)

</div>

---

## Overview

**EvilMind** is a zero-trust cognitive warfare defense system. It decomposes rumor verification into a 4-stage strict pipeline where multiple agents work in parallel within each stage, pushing real-time analysis progress to the frontend via SSE (Server-Sent Events).

### Highlights

- **4-Stage 10-Agent Collaboration**: Fingerprint Team (5 experts in parallel) → Reconnaissance Squad (3-way parallel investigation) → Jury Tribunal (3 judges deliberate independently) → Quality Reviewer
- **Precision Keyword Dispatching**: The Synthesis Judge extracts three sets of search keywords, each dispatched to a dedicated reconnaissance agent (fact-check / deep-dive / source-verify)
- **Full-Chain Evidence Traceability**: Every verdict comes with real search URLs. The vis.js interactive evidence graph allows double-clicking source nodes to open original pages
- **True SSE Streaming**: 4 agent panel progress bars update in real time — no waiting for the full pipeline to see intermediate results
- **Dual Input Modes**: Text paste + screenshot OCR (Baidu PaddleOCR remote API / Ctrl+V paste)
- **Cognitive Prescription + Debunk Card**: Reader-friendly deception analysis + one-click copy to share

---

## Quick Start

### Local

```bash
# 1. Install dependencies
uv sync

# 2. Configure API key
cp .env.example .env
# Edit .env and set DEEPSEEK_API_KEY

# 3. Launch
uv run python main.py
```

Pages:
- `http://localhost:8000/` — Landing page
- `http://localhost:8000/app` — Verification tool
- `http://localhost:8000/guide` — User guide

### Docker

```bash
cp .env.example .env           # Set DEEPSEEK_API_KEY
docker compose up -d           # Build & start
```

The image includes Claude Code CLI (agent search) and OpenCode CLI (page scraping fallback). OpenCode installation failures do not affect core functionality.

---

## Architecture

### 4-Stage Pipeline

```
User Input (text / screenshot)
  │
  ├─ Knowledge Base Retrieval (ChromaDB + Bigram similarity)
  ├─ 14-Dimension Fingerprint + Cognitive Warfare Detection
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 1: Fingerprint Team                               │
│  🧬 Verifier  🌳 Evolution  🔍 Intent  ⚠️ Risk          │
│  (4 experts in parallel)                                │
│          ↓                                               │
│  ⚖️ Synthesis Judge → evil_score + hypothesis + 3 keyword sets │
└─────────────────────────────────────────────────────────┘
  │  Keywords dispatched: fact_check → Fact Checker
  │                      deep_search → Deep Diver
  │                      source_check → OSINT Verifier
  ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 2: Reconnaissance Squad                           │
│  🔍 Claude Fact Checker  🕵️ Claude Deep Diver  🛡️ OSINT │
│  (3 agents in parallel, each with its own search tools)  │
│  Tools: 360 Search + Claude Code CLI + Source Credibility│
└─────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 3: Jury Tribunal                                  │
│  ⚖️ Judge 1  ⚖️ Judge 2  ⚖️ Judge 3                    │
│  (3 judges independently review all evidence)            │
│          ↓                                               │
│  👨‍⚖️ Chief Judge → confirms consensus + flags disputes  │
└─────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 4: Quality Reviewer                               │
│  📝 Report Generation → 🛡️ 4-Dimension Self-Evaluation   │
│  Output: verdict + evidence graph + prescription + card   │
└─────────────────────────────────────────────────────────┘
```

### Verdict Types

| Verdict | Meaning |
|---------|---------|
| `verdict_false` | ❌ False information |
| `verdict_true` | ✅ Verified true |
| `verdict_manipulative` | ⚠️ Cognitive manipulation |
| `verdict_suspicious` | 🟡 Suspicious |
| `verdict_unknown` | ⚪ Unverifiable |

---

## Features

| Feature | Description |
|---------|-------------|
| 📝 **Dual Input** | Text paste + screenshot OCR (upload or Ctrl+V) |
| 📡 **SSE Streaming** | 4-agent panel real-time progress, instant intermediate results |
| 🧬 **14-Dim Fingerprint** | Extreme numbers, urgency calls, emotional triggers, authority claims, etc. |
| 🛡️ **Cognitive Warfare Detection** | 4 attack templates: trust erosion, economic collapse, social division, policy sabotage |
| 🔍 **3-Way Parallel Investigation** | Fact checking + deep diving + source verification with independent keyword dispatch |
| ⚖️ **Jury Tribunal** | 3 independent judges + chief synthesis to prevent single-source bias |
| 🔗 **Evidence Traceability Graph** | Interactive vis.js node graph, double-click source nodes to open URLs |
| 🛡️ **Cognitive Prescription** | "How they deceive you" + "How to protect yourself" |
| 📤 **Debunk Card** | Rumor summary + truth + source, one-click copy to share |
| 🕸️ **Knowledge Graph** | 500+ verified cases visualized by attack dimension, tactic, and case |
| 💬 **User Feedback** | Accuracy feedback loop for continuous improvement |
| 🖼️ **Image Review** | Baidu PaddleOCR remote API, Chinese/English text recognition |

---

## Configuration

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `DEEPSEEK_API_KEY` | — | ✅ | DeepSeek API key |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | No | API endpoint |
| `PRIMARY_MODEL` | `deepseek-v4-pro` | No | Primary model |
| `SECONDARY_MODEL` | `deepseek-v4-pro` | No | Secondary model |
| `BAIDU_OCR_API_KEY` | — | Optional | Baidu OCR (image review) |
| `BAIDU_OCR_SECRET_KEY` | — | Optional | Baidu OCR secret |
| `ANTHROPIC_BASE_URL` | `https://api.deepseek.com/anthropic` | No | Claude CLI backend |
| `HOST` | `0.0.0.0` | No | Listen address |
| `PORT` | `8000` | No | Listen port |
| `SIMILARITY_THRESHOLD` | `0.3` | No | KB match threshold |
| `MAX_SEARCH_RESULTS` | `5` | No | Max search results per query |

---

## API

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| `POST` | `/api/analyze` | Submit text for verification | SSE stream (14 event types) |
| `POST` | `/api/analyze-image` | Submit image for review | SSE stream (OCR → verify) |
| `GET` | `/api/demo/cases` | Demo test cases | JSON |
| `GET` | `/api/knowledge/stats` | KB statistics | JSON |
| `GET` | `/api/knowledge/graph` | Knowledge graph data | JSON (vis.js format) |
| `POST` | `/api/fingerprint` | Fingerprint only (no pipeline) | JSON |
| `POST` | `/api/evolution` | Evolution tree + behavior + motivation | JSON |
| `POST` | `/api/benchmark` | Run benchmark on test set | JSON |
| `POST` | `/api/feedback` | Submit user feedback | JSON |

```bash
# Text verification
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Breaking news: economy in crisis"}'

# Image review
curl -X POST http://localhost:8000/api/analyze-image \
  -F "file=@screenshot.png"
```

### SSE Events

| Event | Trigger |
|-------|---------|
| `fingerprint` | 14-dim fingerprint extraction done |
| `cognitive_warfare` | Cognitive warfare template match done |
| `keywords_extracted` | Three keyword sets dispatched |
| `fp_team_complete` | 4 experts parallel analysis done |
| `agent_start` / `agent_complete` | Agent begin / finish |
| `parallel_complete` | Reconnaissance investigation done |
| `search_trace` | Real search URL list |
| `jury_complete` | 3 judges deliberation done |
| `report` | Complete verification report (final) |
| `ocr_start` / `ocr_complete` | OCR progress (image review only) |
| `done` | Pipeline finished |
| `error` | Error information |

---

## Project Structure

```
EvilMind/
├── main.py                  # Entry point
├── pyproject.toml           # Python project config (uv)
├── uv.lock                  # Dependency lockfile
├── requirements.txt         # pip dependencies (for Docker)
├── Dockerfile               # Docker build
├── docker-compose.yml       # Docker deployment
│
├── config/                  # Configuration (pydantic-settings)
├── llm/                     # LLM client (DeepSeek via OpenAI SDK)
├── agents/                  # Agent implementations
│   ├── fingerprint_team.py  #   Verifier + Evolution + Intent + Risk + Synthesis
│   ├── claude_checker.py    #   Fact Checker (precise claim-by-claim verification)
│   ├── claude_diver.py      #   Deep Diver (background + public sentiment)
│   ├── search_osint.py      #   Source Verifier (domain credibility rating)
│   ├── jury.py              #   Jury Deliberator (3 independent judges + chief)
│   └── publisher.py         #   Quality Reviewer (report + 4-dim self-eval)
├── pipeline/                # 4-stage pipeline orchestrator
├── knowledge/               # KB + 14-dim fingerprint + evolution + cognitive warfare
├── search/                  # 360 Search + Baidu PaddleOCR HTTP API
├── tools/                   # Claude Code CLI + OpenOSINT + Playwright
├── api/                     # FastAPI backend (SSE streaming)
├── web/                     # Frontend
│   ├── landing.html         #   Product landing page
│   ├── app.html             #   Verification tool UI
│   ├── app.js               #   SSE event handler logic
│   ├── guide.html           #   User guide
│   └── style.css            #   Styles
├── data/                    # Seed data + Weibo rumor database + test set
├── reports/                 # Report generation module
└── docs/                    # LaTeX user manual
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **LLM** | DeepSeek-v4-pro (OpenAI SDK) |
| **Backend** | FastAPI + uvicorn + SSE |
| **Frontend** | Vanilla JS + Tailwind CSS + vis.js |
| **Search** | 360 Search + Claude Code CLI + OpenOSINT |
| **OCR** | Baidu PaddleOCR Remote API |
| **Knowledge Base** | ChromaDB + Bigram similarity |
| **Containerization** | Docker + docker-compose |
| **Package Manager** | uv (Tsinghua PyPI mirror) |

---

## Performance

### Pipeline Latency

| Stage | API Calls | Parallelism | Typical Time |
|-------|-----------|-------------|--------------|
| Stage 1: Fingerprint | 5 (4 parallel + 1 serial) | 4 experts → synthesis | 15-30s |
| Stage 2: Reconnaissance | 3+ (with tool-call rounds) | 3 agents parallel search | 20-40s |
| Stage 3: Jury | 4 (3 parallel + 1 serial) | 3 judges → chief | 10-20s |
| Stage 4: Quality Review | 2 (1 report + 1 self-eval) | Serial | 15-25s |
| **Total** | **~15** | | **60-120s** |

### Knowledge Base

| Metric | Value |
|--------|-------|
| Case count | 500+ verified cases |
| Matching algorithm | Bigram character-level similarity |
| Match threshold | 0.3 (≥0.6 inject as context, ≥0.9 reference without shortcut) |
| Fingerprint dimensions | 14 (extreme numbers, urgency calls, emotional triggers, etc.) |

### Docker Image

| Metric | Value |
|--------|-------|
| Base image | Ubuntu 24.04 LTS |
| Image size | ~2.6 GB (Python + Node.js + Claude CLI) |
| Python packages | 103 (HTTP-only, zero local ML models) |
| Memory usage | ~800 MB (ChromaDB + uvicorn workers) |

---

## FAQ

<details>
<summary><b>Q: How long does a full verification take?</b></summary>

Approximately **60-120 seconds**. Fingerprint team: 5 API calls (4 parallel + 1 serial), reconnaissance: 3+ calls (parallel with tool-call rounds), jury: 4 calls (3 parallel + 1 serial), review: 2 calls (serial). Actual time depends on search rounds and network latency.
</details>

<details>
<summary><b>Q: Why might search results be empty?</b></summary>

- 360 Search has indexing delays for very recent content
- Social media platforms (Weibo, Xiaohongshu) restrict scraping
- The system uses Claude Code CLI search as a supplementary channel
- All accessed URLs are listed in the search trace panel
</details>

<details>
<summary><b>Q: Can the LLM fabricate search queries?</b></summary>

No. The Synthesis Judge extracts keywords which are year-tagged by `_enforce_year_tags()` and written into each agent's user prompt. v2.0.1 fixed a bug in `chat_with_tools` where the user prompt was not correctly added to the messages list.
</details>

<details>
<summary><b>Q: Does a KB match shortcut the pipeline?</b></summary>

**No.** Even with ≥0.9 similarity, every claim goes through the full 4-stage pipeline. The KB serves as supplementary context (kb_context/kb_hint) injected into agent prompts — it never replaces live search verification.
</details>

<details>
<summary><b>Q: What configuration is needed for image review?</b></summary>

Baidu PaddleOCR API Key and Secret Key (`BAIDU_OCR_API_KEY` and `BAIDU_OCR_SECRET_KEY` in `.env`). Text-only verification requires no OCR config. OCR uses HTTP API calls with zero local model dependencies.
</details>

<details>
<summary><b>Q: How does Claude Code CLI work in Docker?</b></summary>

The image includes the `@anthropic-ai/claude-code` npm package. It routes through `ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic` to DeepSeek's Anthropic-compatible endpoint, reusing `DEEPSEEK_API_KEY`. No separate Anthropic account required.
</details>

<details>
<summary><b>Q: Is private deployment supported?</b></summary>

Yes. The Docker image runs in government/corporate intranets requiring only DeepSeek API connectivity. All data (KB, reports, search cache) stays in mounted volumes — no data leaves the premises.
</details>

<details>
<summary><b>Q: Where can I view reports?</b></summary>

- Frontend `/app`: full visual report (verdict card + evidence graph + prescription + debunk card)
- `reports/` directory: complete JSON reports with all intermediate analysis
- Knowledge Graph: switch view in `/app` to see all historical cases
</details>

<details>
<summary><b>Q: How can I verify result accuracy?</b></summary>

Every piece of evidence carries a real search URL — click to open the original. The evidence graph supports double-click to open source URLs. The system includes 15 ground-truth-labeled test cases accessible via `/api/benchmark`.
</details>

---

## License

[GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html)
