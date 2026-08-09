"""Phase3 Prompt 模板目录。

v1 模板（稳定版，已生产环境使用）：
- knowledge_card_v1.txt: 知识卡片提取
- methods_v1.txt: 方法流程提取
- data_points_v1.txt: 数据数值提取
- knowledge_card_review_v1.txt / knowledge_card_method_v1.txt: 分类版知识卡片
- methods_review_v1.txt / methods_methodology_v1.txt / methods_experimental_v1.txt: 分类版方法
- paper_all_in_one_v1.txt: 一次性合并提取

v2 模板（A/B 实验用，差异化要点）：
- knowledge_card_v2.txt: 强制字符偏移 + counter_evidence + key_claims 必须含具体数值
- methods_v2.txt: 强制 sample size 具体数字 + evaluation_metrics.scope + models 字符偏移
- data_points_v2.txt: 强制 confidence 0-1 浮点 + metric_name ontology 对齐 + 字符偏移
"""
