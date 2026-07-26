---
name: paper-screening
version: 1.1.0
description: >
  论文初筛 AI Skill — 基于《平台初审维度清单》9 个维度的论文自动/半自动初审工具。
  支持 PDF/DOCX/TXT/TEX 四种输入格式，输出结构化审核报告（Markdown + JSON）。
  当用户提交论文文件并请求初审、查重、格式检查、敏感内容审查时触发。
triggers:
  - 初审
  - 论文审核
  - paper screening
  - 帮我审这篇论文
  - 检查论文格式
  - 论文查重
  - 敏感内容检查
---

# 论文初筛 AI Skill

## 触发条件
当用户提交论文文件（PDF/DOCX/TXT/TEX）并请求初审时触发。

## 执行流程

### Step 1: 解析论文
调用 `scripts/parse_paper.py` 解析输入文件，生成结构化 JSON。

```bash
python scripts/parse_paper.py <paper-file>            # 仅文本解析
python scripts/parse_paper.py <paper-file> --images    # PDF 多模态：提取页面图像为 base64（用于 dim-03 图像完整性分析）
```

> **`--images` 说明**：仅对 PDF 有效。将前 10 页渲染为 1200px 宽的 PNG 并 base64 编码，输出到 `images` 字段。需要 `pdfplumber` + `Pillow` 依赖。Agent 在执行 dim-03 时可直接使用这些图像进行视觉分析。

**失败处理：**
| 触发条件 | 一线修复 | 仍失败兜底 |
|----------|---------|-----------|
| FileNotFoundError | 提示用户检查文件路径，列出当前目录文件 | 用 `ls` 列出用户可能的文件位置 |
| ValueError (不支持格式) | 告知支持格式：PDF/DOCX/TXT/TEX | 建议用户转换格式后重试 |
| ImportError (缺依赖) | 执行 `pip install pypdf pdfplumber python-docx` | 告知用户手动安装后重试 |
| 解析结果为空 | 检查文件是否损坏，尝试用其他格式打开 | 跳过解析，用文件名作为标题继续 |

🔴 **CHECKPOINT — 验证解析结果**：检查 parse_paper.py 输出是否包含 `metadata` 和 `segments` 字段。若缺失，停止执行并告知用户。

### Step 2: 9 维度自动扫描
按顺序执行以下分析器，每个维度独立输出 JSON。

**执行方式**：部分维度有专用脚本（dim-02/04/06/08），其余由 agent 按 `agents/dim-XX-*.md` 指令分析。

| # | 维度 | 执行方式 | 脚本/分析器 | 检查要点 |
|---|------|---------|------------|---------|
| 1 | 格式与结构 | agent 分析 | `agents/dim-01-format.md` | 摘要四段式、章节完整性、图表标题 |
| 2 | 重复文本 | **脚本** | `python scripts/check_plagiarism.py` | API 查重、语义相似度 > 0.85 标记 |
| 3 | 图像完整性 | agent 分析 | `agents/dim-03-image.md` | 图片清晰度、分辨率、标注完整性 |
| 4 | 科学逻辑 | **脚本** | `python scripts/check_logic.py` | 数值提取、摘要-结果一致性、P 值检查 |
| 5 | 伦理法规 | agent 分析 | `agents/dim-05-ethics.md` | 伦理审批、临床注册、隐私保护 |
| 6 | 敏感内容 | **脚本** | `python scripts/check_sensitive.py` | 敏感词匹配、领土表述、地图检测 |
| 7 | 署名版权 | agent 分析 | `agents/dim-07-authorship.md` | 作者贡献、利益冲突、版权声明 |
| 8 | 语言引用 | **脚本 + agent** | `python scripts/check_references.py` + `agents/dim-08-language.md` | 脚本：DOI 校验、自引率、引用格式；agent：摘要可读性、语法错误密度 |
| 9 | 综合分流 | agent 分析 | `agents/dim-09-report.md` | 汇总前 8 维度，生成最终判定 |

**脚本调用方式**（dim-02/04/06/08）：
```bash
echo '<parse_paper.json>' | python scripts/check_plagiarism.py   # dim-02
echo '<parse_paper.json>' | python scripts/check_logic.py        # dim-04
echo '<parse_paper.json>' | python scripts/check_sensitive.py    # dim-06
echo '<parse_paper.json>' | python scripts/check_references.py   # dim-08
```

**脚本输出格式**（所有 `check_*.py` 输出统一的维度结果 JSON，可直接拼接为数组传给 `generate_report.py`）：
```json
{
  "dimension_id": "02",
  "dimension_name": "重复文本",
  "status": "passed|warning|failed|skipped",
  "severity": "info|minor|major|critical",
  "findings": [
    {"item": "...", "expected": "...", "actual": "...", "suggestion": "..."}
  ],
  "interaction_needed": false,
  "user_response": null
}
```

**鲁棒性工具**（`generate_report.py` 提供）：
- `parse_dimension_json(raw)`：从 LLM 原始输出中提取维度结果 JSON，自动去除 Markdown 代码块包裹，失败时用正则兜底提取关键字段
- `normalize_dimension(result)`：校验并补全维度结果字段，非法 status/severity 自动修正为安全默认值
- `_compute_confidence(results)`：基于严重度分布计算 0-100 置信度分数（critical -25, major -15, warning -5）

**失败处理：**
| 触发条件 | 一线修复 | 仍失败兜底 |
|----------|---------|-----------|
| 单个维度分析超时 | 跳过该维度，标记 `status: "skipped"` | 继续执行后续维度 |
| API 调用失败 (dim-02) | 重试 1 次，间隔 3 秒 | 标记 `interaction_needed: true`，询问用户是否手动提供查重结果 |
| 维度输出格式异常 | 用 `parse_dimension_json()` 解析 + `normalize_dimension()` 校验 | 用默认 JSON 填充缺失字段，记录错误日志，继续执行 |

🔴 **CHECKPOINT — 扫描完整性验证**：检查是否 9 个维度全部返回结果。若 < 9 个，列出缺失维度并告知用户。

### Step 3: 汇总待确认项并一次性呈现

扫描完成后，**收集所有** `interaction_needed: true` 的维度发现，**一次性**呈现给用户，等待统一回复。

呈现格式：
```
⚠️ 以下问题需要你补充说明（共 N 项）：

【维度2: 重复文本】
- 方法段与 [DOI: xxx] 相似度 0.87 → 请问是否存在合理引用？

【维度4: 科学逻辑】
- 摘要 P<0.001 但结果段 P=0.03 → 请核实数据来源

请逐条回复，或回复 "全部跳过"：
```

🔴 **CHECKPOINT — 用户确认完整性**：检查用户回复是否覆盖所有 `interaction_needed: true` 的维度。若有维度未被回复，自动填入 `"用户未回应"` 并记录。

**失败处理：**
| 触发条件 | 一线修复 | 仍失败兜底 |
|----------|---------|-----------|
| 用户回复为空 | 自动填入 `"用户未回应"`，继续执行 | — |
| 用户回复「跳过」/「全部跳过」 | 该维度标记 `user_response: "跳过"` | — |

> **设计原则**：本 skill 采用批量收集模式而非逐步交互，避免打断用户工作流。所有待确认项在扫描完成后统一呈现，用户一次性回复。

### Step 4: 生成报告
调用 `scripts/generate_report.py` 生成最终审核报告。

```bash
python scripts/generate_report.py '<results-json>' '<title>' '<authors>'
```

**参数说明**：
- `results-json`：JSON 字符串，包含 9 个维度的分析结果数组
- `title`：论文标题（从 parse_paper.py 输出的 metadata.title 获取）
- `authors`：作者列表（从 parse_paper.py 输出的 metadata.authors 获取）

**输入示例**：
```json
[
  {"dimension_id": "01", "dimension_name": "格式与结构", "status": "passed", "severity": "info", "findings": [], "interaction_needed": false},
  {"dimension_id": "02", "dimension_name": "重复文本", "status": "warning", "severity": "minor", "findings": [{"item": "方法段", "actual": "相似度 0.87", "suggestion": "建议改写"}], "interaction_needed": true}
]
```

**失败处理：**
| 触发条件 | 一线修复 | 仍失败兜底 |
|----------|---------|-----------|
| JSON 解析失败 | 检查维度输出格式，修复后重试 | 用 Python 直接构造 Markdown 报告 |
| 报告生成异常 | 输出原始 JSON 结果供用户手动查看 | — |

### Step 5: 输出
将报告保存为 `审核报告_{论文标题}.md`，并向用户展示综合判定摘要。

🔴 **CHECKPOINT — 报告完整性**：检查报告是否包含「概览」「置信度」「维度明细」「分流建议」四个必要章节。若缺失，补充后重新保存。

**失败处理：**
| 触发条件 | 一线修复 | 仍失败兜底 |
|----------|---------|-----------|
| 文件保存失败（权限/磁盘满） | 检查目录权限，尝试保存到当前目录 | 将报告内容直接输出到对话中 |
| 论文标题含特殊字符（/ \ : * ? " < > \|） | 替换为下划线 `_` | 使用时间戳作为文件名 |
| 报告内容过长（> 100KB） | 截断超长 finding 的 suggestion 字段（保留前 200 字符） | 分章节保存为多个文件 |

## 状态管理
每个维度输出统一格式：
```json
{
  "dimension_id": "01",
  "dimension_name": "格式与结构",
  "status": "passed|warning|failed|skipped",
  "severity": "info|minor|major|critical",
  "findings": [...],
  "interaction_needed": true|false,
  "user_response": null|"..."
}
```

## 判定规则（五级分流）

基于 PaperDecision 分类法，按优先级从高到低判定：

| 原型 | 条件 | 操作 |
|------|------|------|
| ✅ 可直接发布 | 无 critical，无 major，warning ≤ 3 | 直接发布 |
| 🟡 需小修 | 无 critical，有 major 或 warning > 3 | 修改后发布 |
| 🔴 需大修 | 有 critical（非学术诚信），或 failed ≥ 3 | 重大修改后重新审核 |
| ❌ 存疑 | dim-02 failed + dim-04 critical（学术诚信嫌疑） | 暂缓，需管理员人工复核 |
| 🚫 退稿 | critical ≥ 2 或 failed ≥ 5 | 建议退稿 |

## 增强报告特性

### 置信度评分
报告包含 0-100 置信度分数，基于严重度分布计算：
- 初始分 100
- Critical 发现: -25/个
- Major 发现: -15/个
- Warning 发现: -5/个
- 全维度完成: +5
- 跳过维度: -10/个

### 反直觉发现检测
自动检测以下异常模式：
- 多维度 critical 同时出现 → 强烈建议人工核查
- 5+ 维度 warning 但无 critical/major → 系统性质量风险
- dim-02 failed + dim-04 critical → 学术诚信嫌疑
- dim-05 critical + dim-06 critical → 合规风险

### 增强推理链
每个维度分析器包含结构化推理链（CoT），确保分析过程可追溯：
- dim-01: 6 步格式检查 + 论文类型豁免
- dim-02: 5 步查重分析 + 空洞高分检测
- dim-03: 6 步图像完整性检测 + 视觉偏见穿透
- dim-04: 6 步逻辑验证 + 可证伪性检查
- dim-05: 7 步伦理审查 + 研究类型豁免
- dim-06: 6 步敏感内容检测 + 视觉偏见穿透
- dim-07: 6 步署名版权分析 + 致命缺陷核查
- dim-08: 6 步语言引用分析 + 共识量化

## 不要做（反例清单）

| # | 禁止操作 | 原因 |
|---|---------|------|
| 1 | 不要在未解析文件的情况下执行维度分析 | 分析器依赖 parse_paper.py 的输出结构 |
| 2 | 不要跳过 Step 3 待确认项汇总直接生成报告 | 高风险项必须经用户确认后才能纳入最终判定 |
| 3 | 不要修改用户的原始论文文件 | 本 skill 是只读审核工具 |
| 4 | 不要在单个维度内合并多个发现 | 每个 finding 必须独立，便于用户逐条处理 |
| 5 | 不要对 dim-02 (查重) 的 API 结果做最终判定 | API 结果仅供参考，最终判定需人工确认 |
| 6 | 不要忽略 `interaction_needed: true` 的维度 | 这些维度存在歧义，需要用户澄清 |
| 7 | 不要在报告中使用模糊措辞（「可能」「大概」「建议考虑」） | 每个发现必须有明确的 severity 和具体描述 |
| 8 | 不要同时执行多个维度的分析 | 按顺序执行，确保前一个维度的输出可被后续维度引用 |
