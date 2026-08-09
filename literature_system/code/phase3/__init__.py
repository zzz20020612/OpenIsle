"""phase3 论文知识提炼包。

第三阶段实现：基于第二阶段已提取的 paper_sections / paper_figures 表，
通过 LLM 提炼论文知识卡片、方法流程、关键数值，并支持向量化检索。

子模块：
- llm_client: OpenAI 兼容 LLM 客户端
- extractor: 知识卡片/方法/数值提取器（3.1-3.3）
- self_audit: 5 项质量校验
- embedder: 向量化（3.4）
- vector_search: 向量检索与相似推荐（3.4）
"""
