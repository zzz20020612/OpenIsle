# 维度2: 重复文本分析器

## 检查项
1. 整体文字复制比
2. 单段重复峰值
3. 方法部分重复
4. 核心结果/讨论重复

## 实现方案
聚合免费学术数据库 API：
- Semantic Scholar (100次/5分钟)
- OpenAlex (无硬限制)
- Europe PMC (无硬限制)
- arXiv (3秒间隔)
- CrossRef (无硬限制)

## 执行逻辑
**核心逻辑由 `check_plagiarism.py` 脚本实现**，agent 仅补充以下判断：
1. 脚本输出结果中 `interaction_needed: true` 的条目，agent 需结合上下文判断是否为误报
2. 公式/方程被标记为重复 → 这是标准表述，应排除
3. 参考文献列表被标记为重复 → 引用列表是规范格式，应排除
4. 作者自引被标记为高相似度 → 需要单独统计自引率，不应与外部重复混淆

## 推理链
1. **提取关键段落**：从摘要/方法/结果中各取前 500 字作为查询片段
2. **多 API 并行查重**：同时查询 Semantic Scholar/OpenAlex/Europe PMC/arXiv/CrossRef 5 个数据库
3. **相似度计算**：基于 trigram Jaccard 相似度，阈值 0.85 为 warning，0.95 为 failed
4. **排除标准表述**：公式/方程、参考文献列表、标准方法描述 → 不计入重复率
5. **综合判定**：考虑整体复制比 + 单段峰值 + 方法段重复的组合效应

**空洞高分检测（借鉴 PaperDecision）**：
- 若查重结果来自同一篇论文但仅匹配 "Related Work" 段落 → 降级为 warning（非核心内容重复）
- 若匹配 "Methods" 段落且相似度 > 0.90 → 升级为 critical（核心方法疑似抄袭）

## 判定标准
| 指标 | passed | warning | failed |
|------|--------|---------|--------|
| 整体复制比 | < 15% | 15%~25% | > 25% |
| 单段峰值 | < 0.85 | 0.85~0.95 | > 0.95 |
| 方法段重复 | 无 | 有 | 多处 |

## 常见误判
- **误判1**: 低置信度匹配被误判为高相似度 → API 返回的相似度分数可能因摘要不完整而虚高，需结合上下文判断
- **误判2**: 同一研究的后续发表被标记为重复 → 同一团队的系列研究可能有大量重叠的方法描述，应排除
- **误判3**: 系统综述/Meta分析的高相似度 → 综述类论文的方法段高度标准化，相似度偏高是正常现象

## 输出
```json
{
  "dimension_id": "02",
  "dimension_name": "重复文本",
  "status": "passed|warning|failed",
  "severity": "info|minor|major|critical",
  "findings": [
    {
      "item": "方法段",
      "actual": "与 [DOI: xxx] 相似度 0.87",
      "suggestion": "建议改写以下段落..."
    }
  ],
  "interaction_needed": true
}
```
