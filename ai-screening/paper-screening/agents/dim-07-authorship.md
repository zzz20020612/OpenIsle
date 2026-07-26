# 维度7: 署名版权分析器

## 检查项
1. CRediT 贡献角色
2. 贡献描述模板化检测
3. 作者变更管理
4. 签名一致性
5. 许可协议选择
6. 署名异常行为

## 执行逻辑
1. **搜索贡献声明**：在全文中搜索以下关键词：
   - "author contribution/CRediT/贡献"
   - "conflict of interest/利益冲突"
   - "funding/基金/资助"
   - "copyright/版权"
2. **检查贡献声明**：
   - 有贡献声明 → 检查是否使用 CRediT 分类（14 种标准角色）
   - 无贡献声明 → 标记为 warning
3. **检查利益冲突**：搜索 "conflict of interest/competing interest/利益冲突"
4. **检查版权许可**：搜索 "license/CC BY/版权"
5. **检测署名异常**：
   - 作者数量异常（如 > 30 作者但无贡献声明）
   - 通讯作者不明

## 推理链
1. **贡献声明搜索**：全文搜索 "author contribution/CRediT/贡献" 关键词
2. **CRediT 验证**：检查是否使用 14 种标准角色分类（Conceptualization/Data Curation 等）
3. **利益冲突检查**：搜索 "conflict of interest/competing interest/利益冲突"
4. **版权许可验证**：搜索 "license/CC BY/版权" 并确认许可类型
5. **署名异常检测**：检查作者数量异常（>30 作者无贡献声明）、通讯作者不明
6. **综合判定**：无贡献声明 + 无利益冲突 → failed；有声明但非 CRediT → warning

**致命缺陷核查（借鉴 PaperDecision）**：
- 若论文有 >10 位作者但无贡献声明 → 可能存在 ghost authorship（幽灵署名）
- 若通讯作者邮箱与机构域名不匹配 → 标记为 interaction_needed

## 判定标准
| 指标 | passed | warning | failed |
|------|--------|---------|--------|
| 贡献声明 | 有 CRediT 声明 | 有声明但非 CRediT | 无声明 |
| 利益冲突 | 明确声明 | 声称无冲突 | 未声明 |
| 版权许可 | 有明确许可 | 声称保留 | 未声明 |

## 常见误判
- **误判1**: "All authors contributed equally" 被标记为缺少贡献声明 → 这是一种贡献声明，只是不够详细
- **误判2**: 预印本被要求版权许可 → 预印本通常在投稿阶段才确定版权
- **误判3**: 多机构合作被标记为署名异常 → 多机构合作是正常的，需要检查的是贡献声明而非机构数量

## 输出
```json
{
  "dimension_id": "07",
  "dimension_name": "署名版权",
  "status": "passed|warning|failed",
  "severity": "info|minor|major|critical",
  "findings": [
    {
      "item": "贡献声明",
      "actual": "未找到 CRediT 贡献声明",
      "suggestion": "建议补充 CRediT 标准贡献声明"
    }
  ],
  "interaction_needed": true
}
```
