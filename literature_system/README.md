# Literature System / 文献系统

### OpenIsle 本地集成

在 OpenIsle 仓库根目录执行：

```powershell
docker compose --profile dev -f docker/docker-compose.yaml up -d literature-system springboot
```

文献工作台默认运行在 `http://localhost:8088`，OpenIsle 登录用户可从
`/literature` 进入“Knowledge workflow”。SQLite 数据库、自动下载的开放 PDF
及解析结果保存在 Docker 卷 `openisle_literature-data` 中。

- LLM 提炼复用 OpenIsle 的 `AI_SCREENING_API_KEY`、`AI_SCREENING_BASE_URL` 和 `AI_SCREENING_MODEL`。
- MinerU 未配置时会自动回退到 PyMuPDF。
- 向量/混合检索需要单独配置 `EMBEDDING_API_KEY`、`EMBEDDING_BASE_URL` 和 `EMBEDDING_MODEL`；未配置时知识卡片、方法、数据点和普通检索仍可正常使用。

### 快速开始

```bash
# 1. 安装依赖
python -m venv .venv
.venv\Scripts\activate  # Windows
uv pip install -r requirements.txt

# 2. 配置环境
copy config\.env.example config\.env
# 编辑 config\.env 配置数据库和 API Key

# 3. 初始化数据库
python scripts/init_db.py --demo

# 4. 启动服务
cd code
python search/api.py
# 浏览器打开 http://localhost:8088
```

### 数据流程

```
┌─────────────────────────────────────────────────────────────┐
│                      多源数据采集                            │
│  Crossref · arXiv · PMC · PubMed · OpenAlex · SemScholar    │
│  Web of Science · Scopus                                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   清洗与核心处理                              │
│  字段规范化 · 去重 · 期刊分级 · 作者消歧 · 资助/链接提取      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
              ┌──────────────────┐
              │   papers 数据表   │
              └────────┬─────────┘
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
┌───────────────────┐       ┌──────────────────┐
│  PDF 与文本解析    │       │  图谱与可视化     │
│  全文/章节/图表   │       │  引用/作者网络    │
│  参考文献          │       │  分析             │
└─────────┬─────────┘       └──────────────────┘
          │
          ▼
┌───────────────────────────────────────────┐
│           LLM 知识提炼                     │
│  知识卡片 · 方法流程 · 数据点 · 质量评分    │
└─────────────────┬─────────────────────────┘
                  │
                  ▼
┌───────────────────────────────────────────┐
│         向量化 (sqlite-vec)                │
│  混合检索 (FTS5 + 向量)                    │
│  REST API + Web UI                        │
└───────────────────────────────────────────┘
```

### 功能特性

- **多源采集**：Crossref、arXiv、PMC、OpenAlex、Semantic Scholar、PubMed、Web of Science、Scopus
- **作者消歧**：ORCID/ResearcherID/ScopusID 精确匹配 + 姓名/机构模糊匹配
- **期刊分级**：可配置的 tier1/tier2/tier3 期刊分类体系
- **PDF 解析**：MinerU API → PyMuPDF → Marker 三级回退管道
- **大模型知识提炼**：知识卡片、方法流程、数据数值提取，含质量评分
- **向量检索**：基于 sqlite-vec 的混合检索（FTS5 + 向量）
- **图谱可视化**：引用/合著网络，含健康诊断
- **REST API**：完整 API + Python SDK 客户端

### 技术栈

- **后端**：Python 3.10+, Starlette, uvicorn
- **数据库**：SQLite（FTS5 + sqlite-vec）/ PostgreSQL
- **大模型**：OpenAI 兼容 API（DeepSeek、Qwen 等）
- **前端**：Vanilla JS, ECharts, D3.js
- **PDF**：PyMuPDF, MinerU API, Marker
