# 维度9: 综合分流分析器

## 职责
汇总前 8 维度结果，生成最终分流判定。

## 决策原型

基于 PaperDecision 的五级分类法，适配本平台 9 维度审核体系：

| 原型 | 信号 | 操作 |
|------|------|------|
| ✅ 可直接发布 (Publish) | 无 critical，无 major，warning ≤ 3 | 直接发布 |
| 🟡 需小修 (Minor Revision) | 无 critical，有 major 或 warning > 3，但所有 major 问题都有明确修复路径 | 修改后发布 |
| 🔴 需大修 (Major Revision) | 有 critical 但非学术诚信问题，或 failed 维度 ≥ 3 | 重大修改后重新审核 |
| ❌ 存疑 (Conditional) | 涉及学术诚信（dim-02 重复文本 failed 或 dim-04 科学逻辑 critical） | 暂缓，需人工判定 |
| 🚫 退稿 (Reject) | critical ≥ 2 或 failed 维度 ≥ 5 | 建议退稿 |

## 执行逻辑

### Step 1: 统计各状态维度数量
- `passed_count` = status == "passed" 的维度数
- `warning_count` = status == "warning" 的维度数
- `failed_count` = status == "failed" 的维度数
- `critical_count` = severity == "critical" 的维度数
- `major_count` = severity == "major" 的维度数

### Step 2: 检查特定维度组合（优先级最高）
1. **dim-02 failed + dim-04 critical** → ❌ 存疑（学术诚信嫌疑）
2. **dim-06 critical** → 🔴 需大修（敏感内容是硬性红线）
3. **dim-05 critical + dim-07 critical** → 🔴 需大修（伦理+署名双重问题）

### Step 3: 应用决策原型映射（按优先级从高到低）
1. 🚫 退稿：critical ≥ 2 或 failed 维度 ≥ 5
2. ❌ 存疑：涉及学术诚信（Step 2 中的组合判定）
3. 🔴 需大修：有 critical 但非学术诚信问题，或 failed ≥ 3
4. 🟡 需小修：无 critical，有 major 或 warning > 3，但 major 有明确修复路径
5. ✅ 可直接发布：无 critical，无 major，warning ≤ 3

### Step 4: 生成推理链
列出每个维度的状态和严重级别，说明哪些维度触发了当前原型判定。

## 输出
```json
{
  "dimension_id": "09",
  "dimension_name": "综合分流",
  "status": "passed|warning|failed",
  "severity": "info|minor|major|critical",
  "findings": [],
  "interaction_needed": false,
  "verdict": "publish|minor_revision|major_revision|conditional|reject",
  "verdict_archetype": "可直接发布|需小修|需大修|存疑|退稿",
  "verdict_reason": "...",
  "triggered_dimensions": ["02", "04"]
}
```

## 常见误判
- **误判1**: 单个 critical 直接判退稿 → 应先检查 critical 数量是否 ≥ 2，单个 critical 应为需大修
- **误判2**: dim-02 warning + dim-04 warning 直接判存疑 → 存疑仅在 dim-02 failed 或 dim-04 critical 时触发
- **误判3**: warning 数量多但无 critical/major 直接判退稿 → 无 critical 时 warning 多只应判需小修
