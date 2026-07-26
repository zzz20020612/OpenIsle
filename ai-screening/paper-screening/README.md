# 论文初筛 AI Skill

基于《平台初审维度清单》9 个维度的论文自动/半自动初审工具。

## 功能特性

- 支持 PDF/DOCX/TXT/TEX 四种输入格式
- 9 维度自动扫描（格式/重复/图像/逻辑/伦理/敏感/署名/语言/综合）
- 批量收集待确认项后一次性呈现（高风险项人工确认）
- 结构化审核报告输出（Markdown + JSON）

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行解析
python scripts/parse_paper.py your_paper.pdf

# 运行测试
pytest tests/ -v
```

## 使用方法

在任意 AI agent 中调用此 Skill（OpenCode / Claude Code / Codex 等）：

```
请帮我初审这篇论文：path/to/paper.pdf
```

## HTTP 服务（文本初筛 MVP）

```bash
export AI_SCREENING_API_KEY=your-key
export AI_SCREENING_SERVICE_TOKEN=internal-token
uvicorn screening_service.api:app --host 0.0.0.0 --port 8090
```

调用 `POST /v1/screenings` 时使用 `Authorization: Bearer <token>`。文本 MVP
执行维度 01/04/05/06/07/08/09；联网查重（02）和图片完整性（03）会明确标记为
`skipped`，不会伪装成已通过。

## 输出示例

```
# 论文初审完善报告

## 概览
- 论文标题: A Study on ML
- 综合判定: ✅ 可直接发布

## 明细
### [✅] 维度1: 格式与结构 — 通过
...
```

## 架构

```
Parser → Pipeline (9 维度) → Reporter
```

## 依赖

- Python ≥ 3.10
- pypdf / pdfplumber / python-docx / httpx
- 免费 REST API（Semantic Scholar/OpenAlex/Europe PMC/arXiv/CrossRef）
