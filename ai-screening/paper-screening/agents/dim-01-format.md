# 维度1: 格式与结构分析器

## 检查项
1. 摘要四段式（目的/方法/结果/结论）
2. 章节完整性（引言/方法/结果/讨论/参考文献）
3. 图表标题清单
4. 文件格式合规
5. 页眉页脚/行号

## 执行逻辑
1. 遍历 segments，检查摘要是否包含四要素：
   - **目的**：搜索 "purpose/objective/aim/goal" 或类似表述
   - **方法**：搜索 "method/approach/technique" 或类似表述
   - **结果**：搜索 "result/find/outcome" 或类似表述
   - **结论**：搜索 "conclusion/conclude" 或类似表述
2. 检查必要章节是否存在（至少 4/5：引言/方法/结果/讨论/参考文献）
3. 检查 images/tables 是否有标题（每个图/表必须有 caption）

## 推理链
1. 识别论文类型（原创研究/综述/短文/病例报告）
2. 根据论文类型确定适用的格式要求
3. 逐项检查摘要四要素
4. 逐项检查必要章节
5. 检查图表标题完整性
6. 综合判定（考虑论文类型的豁免项）

## 输出
```json
{
  "dimension_id": "01",
  "dimension_name": "格式与结构",
  "status": "passed|warning|failed",
  "severity": "info|minor|major|critical",
  "findings": [
    {
      "item": "摘要四段式",
      "actual": "缺少「结论」要素",
      "suggestion": "在摘要末尾补充结论段落"
    }
  ],
  "interaction_needed": false
}
```

## 判定标准
- **passed**: 摘要四要素齐全 + 章节 ≥4/5 + 图表有标题
- **warning**: 缺少 1 个摘要要素 或 章节 = 3/5
- **failed**: 缺少 ≥2 个摘要要素 或 章节 ≤2/5

## 常见误判
- **误判1**: 非英语论文缺少英文摘要被标记为 failed → 部分期刊不要求英文摘要，应确认投稿期刊要求
- **误判2**: 短文/综述缺少标准章节被标记为 warning → 综述文章可能没有独立的「方法」章节
- **误判3**: LaTeX 论文的图表标题格式不同被标记为缺失 → LaTeX 的 `\caption{}` 可能不在 segments 中直接可见
