// i18n - Internationalization module
// Usage: I18n.t('key') returns the translated string for current language
//        I18n.setLang('en') or I18n.setLang('zh') to switch
//        I18n.toggle() to toggle between zh and en

const I18n = (function() {
    const LANG_KEY = 'lit_sys_lang';
    let currentLang = localStorage.getItem(LANG_KEY) || 'zh';

    const translations = {
        zh: {
            // Navigation
            'nav.dashboard': '仪表盘',
            'nav.search': '检索与知识库',
            'nav.timeline': '时间线',
            'nav.network': '关系网络',
            'nav.compare': '指标对比',
            'nav.vectordb': '向量库',
            'nav.authors': '学者画像',
            'nav.institutions': '机构合作',
            'nav.workflow': '工作流',
            'nav.quality': '质量监控',
            'nav.settings': '设置',

            // Common
            'common.loading': '加载中...',
            'common.loading_stats': '加载统计数据...',
            'common.search': '搜索',
            'common.save': '保存',
            'common.cancel': '取消',
            'common.confirm': '确定',
            'common.close': '关闭',
            'common.delete': '删除',
            'common.edit': '编辑',
            'common.retry': '重试',
            'common.merge': '合并',
            'common.copy': '复制',
            'common.export': '导出',
            'common.import': '导入',
            'common.refresh': '刷新',
            'common.back': '返回',
            'common.no_data': '无数据',
            'common.no_results': '暂无结果',
            'common.page_not_found': '页面不存在',
            'common.load_failed': '加载失败',
            'common.service_ok': '服务正常',
            'common.service_error': '服务异常',
            'common.service_checking': '服务检查中...',
            'common.unknown_year': '未知年份',
            'common.no_title': '无标题',
            'common.placeholder': '输入关键词...',
            'common.settings': '设置',
            'common.rebuild_index': '重建索引',
            'common.confirm_rebuild': '确定要重建索引吗？',

            // Dashboard
            'dashboard.title': '仪表盘',
            'dashboard.total_papers': '总论文数',
            'dashboard.valid_papers': '有效论文（已排除占位）',
            'dashboard.indexed_papers': '已索引论文',
            'dashboard.coverage': '索引覆盖率',
            'dashboard.sections': '章节总数',
            'dashboard.figures': '图表总数',
            'dashboard.data_points': '数据点总数',
            'dashboard.valid_data_points': '有效数据点（已排除占位）',
            'dashboard.parse_jobs': '解析任务状态',
            'dashboard.no_parse_jobs': '暂无解析任务数据',

            // Search
            'search.mode': '检索模式',
            'search.field': '检索字段',
            'search.all_fields': '全部字段',
            'search.title': '标题',
            'search.abstract': '摘要',
            'search.keywords': '关键词',
            'search.author': '作者',
            'search.journal': '期刊名',
            'search.doi': 'DOI',
            'search.year': '年份',
            'search.fulltext': '文章内容',
            'search.click_multi': '点击多选',
            'search.delete_row': '删除该行',
            'search.results': '检索结果',
            'search.no_query': '请输入关键词或选择筛选条件',
            'search.papers_tab': '论文',
            'search.data_points_tab': '数据点',
            'search.knowledge_tab': '知识卡片',
            'search.methods_tab': '方法流程',
            'search.mode_keyword': '关键词',
            'search.mode_phrase': '短语',
            'search.mode_fuzzy': '模糊',
            'search.mode_vector': '向量',
            'search.mode_hybrid': '混合',

            // Facets
            'facet.year': '年份',
            'facet.journal': '期刊',
            'facet.language': '语言',
            'facet.source': '来源',
            'facet.author': '作者',
            'facet.keyword': '关键词',

            // Timeline
            'timeline.no_data': '无时间线数据',
            'timeline.paper_count': '论文数',
            'timeline.parsed_count': '论文解析完成数',
            'timeline.data_point_count': '数据点数',

            // Graph
            'graph.no_nodes': '无节点数据',
            'graph.paper': '论文',
            'graph.author': '作者',
            'graph.keyword': '关键词',
            'graph.data_point': '数据点',
            'graph.institution': '机构',
            'graph.upstream': '上游（被其引用）',
            'graph.downstream': '下游（引用它）',
            'graph.two_hop': '2阶邻居',
            'graph.search_placeholder': '输入节点名称回车定位',

            // Knowledge card
            'knowledge.research_question': '研究问题',
            'knowledge.core_answer': '核心回答',
            'knowledge.key_claims': '关键主张',
            'knowledge.boundaries': '三桶边界',
            'knowledge.reusable': '可复用启发',
            'knowledge.no_card': '该论文暂无知识卡片',

            // Quality
            'quality.title': '质量监控',
            'quality.score': '质量评分',
            'quality.issues': '问题',

            // Workflow
            'workflow.title': '工作流',
            'workflow.config': '工作流配置',
            'workflow.tasks': '任务列表',
            'workflow.trigger': '触发任务',
            'workflow.progress': '任务进度',

            // Settings
            'settings.title': '设置',
            'settings.description': '个性化界面偏好，并集中管理工作流相关配置。修改后点击"保存"即可生效。',
            'settings.workflow_desc': '与"工作流"页面的"工作流配置"区域一致。修改后保存即生效；API Key 仅显示前 4 位以避免泄露。',

            // Toast
            'toast.rebuild_started': '重建任务已启动',
            'toast.rebuild_done': '索引重建完成',
            'toast.rebuild_failed': '重建失败',
            'toast.task_failed': '任务失败',

            // Progress
            'progress.waiting': '等待执行...',
            'progress.running': '进行中',
            'progress.done': '完成',
            'progress.failed': '失败',

            // Authors
            'authors.merge_hint': '检测到 {count} 组同名学者（共 {total} 条重复记录），可点击"合并"按钮进行消歧',
            'authors.search_name': '姓名关键词',
            'authors.search_affiliation': '机构关键词',

            // Filters
            'filter.start_year': '起',
            'filter.end_year': '止',
            'filter.journal': '期刊',
            'filter.source': '来源',
            'filter.error_class': '错误类别过滤',

            // Brand
            'brand.title': '文献系统',
            'brand.subtitle': '学术文献知识共享平台',

            // Language
            'lang.switch': 'English',

            // Knowledge card sections
            'knowledge.evidence_generation': '证据产生',
            'knowledge.key_claims_title': '关键主张',
            'knowledge.boundaries_title': '边界与未解决问题',
            'knowledge.reusable_title': '可复用启发',
            'knowledge.items_count': '{count} 条',
            'knowledge.no_card_text': '该论文暂无知识卡片',
            'knowledge.claim_source.author': '作者原文',
            'knowledge.claim_source.user': '用户标注',
            'knowledge.claim_source.llm': 'LLM 抽取',
            'knowledge.claim_evidence': '证据',
            'knowledge.claim_condition': '限定',
            'knowledge.claim_counter': '反证',
            'knowledge.claim_anchor': '锚点',
            'knowledge.boundary_acknowledged': '作者承认',
            'knowledge.boundary_result_shown': '结果所示',
            'knowledge.boundary_unconfirmed': '未确认',
            'knowledge.boundary_temporal': '时间边界',
            'knowledge.boundary_spatial': '空间边界',
            'knowledge.boundary_methodological': '方法学边界',
            'knowledge.boundary_empty': '暂无',
            'knowledge.inspiration.method': '方法',
            'knowledge.inspiration.dataset': '数据',
            'knowledge.inspiration.framework': '框架',
            'knowledge.inspiration.metric': '指标',
            'knowledge.inspiration.tool': '工具',
            'knowledge.inspiration.general': '启发',

            // Methods
            'methods.no_data': '该论文暂无方法流程',
            'methods.methodology': '研究方法',
            'methods.workflow': '实验/分析流程',
            'methods.data_sources': '数据来源与样本',
            'methods.models_algorithms': '模型/算法',
            'methods.evaluation_metrics': '评估指标',

            // Data points table
            'datapoints.no_data': '该论文暂无数据点',
            'datapoints.metric': '指标',
            'datapoints.value': '数值',
            'datapoints.unit': '单位',
            'datapoints.context': '上下文',
            'datapoints.page': '页码',
            'datapoints.confidence': '置信度',
            'datapoints.unnamed': '未命名指标',

            // Sections
            'sections.no_data': '无章节数据',
            'sections.other': '章节 {num}',

            // Figures
            'figures.no_data': '无图表数据',
            'figures.page_label': '页码',
            'figures.unknown_page': '未知',

            // Citations
            'citations.no_data': '无引用数据',

            // Similar papers
            'similar.no_data': '暂无相似论文',
            'similar.similarity': '相似度',

            // Facet
            'facet.no_data': '无聚合数据',

            // Pagination
            'pagination.prev': '上一页',
            'pagination.next': '下一页',
            'pagination.info': '第 {current} / {total} 页（共 {total_items} 条）',

            // Table
            'table.no_data': '无数据',

            // Tag cloud
            'tagcloud.no_data': '无标签',

            // Graph controls
            'graph.controls.reset': '重置视图',
            'graph.controls.relayout': '重新布局',
            'graph.controls.show_all_labels': '显示全部标签',
            'graph.controls.smart_labels': '智能隐藏标签',
            'graph.controls.focus_depth': '聚焦深度: {depth}阶',
            'graph.controls.toggle': '图谱控制',
            'graph.controls.title': '⚙',

            // Graph sidebar
            'graph.sidebar.node_types': '节点类型',
            'graph.sidebar.year_range': '年份范围',
            'graph.sidebar.citations_nodes': '引用与节点',
            'graph.sidebar.min_citations': '最小引用',
            'graph.sidebar.max_nodes': '最大节点',
            'graph.sidebar.display_options': '显示选项',
            'graph.sidebar.citation_only': '仅论文引用网络',
            'graph.sidebar.show_labels': '显示标签',
            'graph.sidebar.node_locate': '节点定位',
            'graph.sidebar.node_search_placeholder': '输入节点名称回车定位',
            'graph.sidebar.node_search_hint': '支持论文标题、作者、关键词等关键字',
            'graph.sidebar.graph_health': '图谱健康',
            'graph.sidebar.health_loading': '加载中...',
            'graph.sidebar.refresh': '刷新图谱',

            // Graph toolbar
            'graph.toolbar.year': '年份',
            'graph.toolbar.min_citations': '最小引用',
            'graph.toolbar.max_nodes': '最大节点',
            'graph.toolbar.refresh': '刷新图谱',

            // Graph legend
            'graph.legend.upstream': '上游（被其引用）',
            'graph.legend.downstream': '下游（引用它）',
            'graph.legend.two_hop': '2阶邻居',

            // Timeline chart
            'timeline.chart.paper_count': '论文数',
            'timeline.chart.parse_done': '论文解析完成数',
            'timeline.chart.data_points': '数据点数',
            'timeline.chart.y_left_label': '论文数 / 解析完成数',
            'timeline.chart.y_right_label': '数据点数',

            // Search bar
            'search.field_labels.all': '全部字段',
            'search.field_labels.title': '标题',
            'search.field_labels.abstract': '摘要',
            'search.field_labels.keywords': '关键词',
            'search.field_labels.author': '作者',
            'search.field_labels.journal': '期刊名',
            'search.field_labels.doi': 'DOI',
            'search.field_labels.year': '年份',
            'search.field_labels.fulltext': '文章内容',
            'search.placeholder.papers': '输入关键词、短语...',
            'search.placeholder.data_points': '指标名称，如 cattle count',
            'search.placeholder.knowledge': '研究问题 / 核心结论 / 主张内容',
            'search.placeholder.methods': '研究方法 / 数据来源 / 模型算法',
            'search.add_field': '+ 添加字段',
            'search.clear': '清空',
            'search.journal_tier': '期刊分级',
            'search.advanced_search': '▼ 高级检索',
            'search.advanced_search_collapsed': '▶ 高级检索（折叠）',
            'search.advanced_hint': '多字段 + 期刊分级 + 模式',
            'search.advanced_hint_collapsed': '点击展开多字段 / 期刊分级 / 模式',
            'search.default_browse': '默认浏览',
            'search.default_browse_label': '默认浏览',
            'search.sort.year_desc': '年份降序',
            'search.sort.year_asc': '年份升序',
            'search.sort.citations_desc': '被引降序',
            'search.sort.title_asc': '标题升序',
            'search.facet_panel': '聚合面板',
            'search.facet_panel_default': '默认浏览',
            'search.no_query_hint': '💡 未输入检索条件，按默认排序浏览全部论文。\n\n输入关键词或选择筛选条件以激活精确检索。',
            'search.tier_current': '当前分级',
            'search.tier_none': '未选',
            'search.tier_hint_selected': '在顶部「高级检索」区域调整分级选择。',
            'search.tier_hint_none': '在顶部「高级检索」区域点击 T1/T2/T3/其他 进行多选筛选。',
            'search.usage_hint_title': '使用提示',
            'search.usage_hint': '· 顶部「高级检索」可固定显示\n· 多字段行支持添加/删除\n· 模式：关键词 / 短语 / 模糊 / 向量 / 混合',

            // Dashboard table
            'dashboard.table.stage': '阶段',
            'dashboard.table.status': '状态',
            'dashboard.table.count': '数量',

            // Compare
            'compare.title': '指标对比',
            'compare.no_data': '无对比数据',

            // Vector DB
            'vector.title': '向量库',
            'vector.no_data': '无向量数据',

            // Authors
            'authors.title': '学者画像',
            'authors.no_data': '无学者数据',

            // Institutions
            'institutions.title': '机构合作',
            'institutions.no_data': '无机构数据',

            // Workflow
            'workflow.title': '工作流',
            'workflow.no_data': '无工作流数据',

            // Quality
            'quality.title': '质量监控',
            'quality.no_data': '无质量数据',

            // Settings
            'settings.title': '设置',
            'settings.no_data': '无设置数据',

            // Network
            'network.title': '关系网络',
            'network.no_data': '无网络数据',

            // Tooltip
            'tooltip.type': '类型',
            'tooltip.year': '年份',
            'tooltip.citations': '被引',
            'tooltip.connections': '连接数',
            'tooltip.occurrences': '出现次数',
            'tooltip.paper_count': '论文数',
            'tooltip.click_focus': '单击聚焦，双击查看详情',

            // Search field hints
            'search.field_input_placeholder': '输入{field}',
            'search.year_input_placeholder': '如 2020-2024 或 2023',
            'search.delete_row_title': '删除该行',
            'search.max_fields_toast': '最多 6 行字段',

            // Toast messages
            'toast.load_failed': '{context}加载失败: {reason}',
            'toast.additional_data_load_failed': '部分附加数据加载失败，请查看控制台',
            'toast.network_load_failed': '引用网络加载失败',
            'toast.graph_load_failed': '图谱加载失败',

            // Paper detail tabs
            'paper.tab.abstract': '摘要',
            'paper.tab.sections': '章节',
            'paper.tab.figures': '图表',
            'paper.tab.citations': '引用',
            'paper.tab.knowledge': '知识卡片',
            'paper.tab.methods': '方法流程',
            'paper.tab.data': '数据点',

            // Paper meta
            'paper.meta.unknown': '未知',
            'paper.meta.none': '无',
            'paper.meta.unknown_paper': '论文 {id}',
            'paper.meta.doi': 'DOI',
            'paper.meta.year': '年份',
            'paper.meta.journal': '期刊',
            'paper.meta.source': '来源',
            'paper.meta.cited_by': '被引',
            'paper.meta.similar_papers': '相似论文',
            'paper.meta.author': '作者',
            'paper.meta.keywords': '关键词',
        },

        en: {
            // Navigation
            'nav.dashboard': 'Dashboard',
            'nav.search': 'Search & Knowledge',
            'nav.timeline': 'Timeline',
            'nav.network': 'Network',
            'nav.compare': 'Compare',
            'nav.vectordb': 'Vector DB',
            'nav.authors': 'Authors',
            'nav.institutions': 'Institutions',
            'nav.workflow': 'Workflow',
            'nav.quality': 'Quality',
            'nav.settings': 'Settings',

            // Common
            'common.loading': 'Loading...',
            'common.loading_stats': 'Loading stats...',
            'common.search': 'Search',
            'common.save': 'Save',
            'common.cancel': 'Cancel',
            'common.confirm': 'Confirm',
            'common.close': 'Close',
            'common.delete': 'Delete',
            'common.edit': 'Edit',
            'common.retry': 'Retry',
            'common.merge': 'Merge',
            'common.copy': 'Copy',
            'common.export': 'Export',
            'common.import': 'Import',
            'common.refresh': 'Refresh',
            'common.back': 'Back',
            'common.no_data': 'No data',
            'common.no_results': 'No results',
            'common.page_not_found': 'Page not found',
            'common.load_failed': 'Load failed',
            'common.service_ok': 'Service OK',
            'common.service_error': 'Service error',
            'common.service_checking': 'Checking service...',
            'common.unknown_year': 'Unknown year',
            'common.no_title': 'No title',
            'common.placeholder': 'Enter keywords...',
            'common.settings': 'Settings',
            'common.rebuild_index': 'Rebuild Index',
            'common.confirm_rebuild': 'Are you sure you want to rebuild the index?',

            // Dashboard
            'dashboard.title': 'Dashboard',
            'dashboard.total_papers': 'Total Papers',
            'dashboard.valid_papers': 'Valid Papers (excl. placeholders)',
            'dashboard.indexed_papers': 'Indexed Papers',
            'dashboard.coverage': 'Index Coverage',
            'dashboard.sections': 'Total Sections',
            'dashboard.figures': 'Total Figures',
            'dashboard.data_points': 'Total Data Points',
            'dashboard.valid_data_points': 'Valid Data Points (excl. placeholders)',
            'dashboard.parse_jobs': 'Parse Job Status',
            'dashboard.no_parse_jobs': 'No parse job data',

            // Search
            'search.mode': 'Search Mode',
            'search.field': 'Search Field',
            'search.all_fields': 'All Fields',
            'search.title': 'Title',
            'search.abstract': 'Abstract',
            'search.keywords': 'Keywords',
            'search.author': 'Author',
            'search.journal': 'Journal',
            'search.doi': 'DOI',
            'search.year': 'Year',
            'search.fulltext': 'Full Text',
            'search.click_multi': 'Click to multi-select',
            'search.delete_row': 'Delete this row',
            'search.results': 'Search Results',
            'search.no_query': 'Enter keywords or select filters',
            'search.papers_tab': 'Papers',
            'search.data_points_tab': 'Data Points',
            'search.knowledge_tab': 'Knowledge Cards',
            'search.methods_tab': 'Methods',
            'search.mode_keyword': 'Keyword',
            'search.mode_phrase': 'Phrase',
            'search.mode_fuzzy': 'Fuzzy',
            'search.mode_vector': 'Vector',
            'search.mode_hybrid': 'Hybrid',

            // Facets
            'facet.year': 'Year',
            'facet.journal': 'Journal',
            'facet.language': 'Language',
            'facet.source': 'Source',
            'facet.author': 'Author',
            'facet.keyword': 'Keyword',

            // Timeline
            'timeline.no_data': 'No timeline data',
            'timeline.paper_count': 'Papers',
            'timeline.parsed_count': 'Parsed',
            'timeline.data_point_count': 'Data Points',

            // Graph
            'graph.no_nodes': 'No node data',
            'graph.paper': 'Paper',
            'graph.author': 'Author',
            'graph.keyword': 'Keyword',
            'graph.data_point': 'Data Point',
            'graph.institution': 'Institution',
            'graph.upstream': 'Upstream (cited by)',
            'graph.downstream': 'Downstream (cites)',
            'graph.two_hop': '2-hop neighbors',
            'graph.search_placeholder': 'Type node name, press Enter',

            // Knowledge card
            'knowledge.research_question': 'Research Question',
            'knowledge.core_answer': 'Core Answer',
            'knowledge.key_claims': 'Key Claims',
            'knowledge.boundaries': 'Boundaries',
            'knowledge.reusable': 'Reusable Insights',
            'knowledge.no_card': 'No knowledge card available',

            // Quality
            'quality.title': 'Quality Monitor',
            'quality.score': 'Quality Score',
            'quality.issues': 'Issues',

            // Workflow
            'workflow.title': 'Workflow',
            'workflow.config': 'Workflow Config',
            'workflow.tasks': 'Task List',
            'workflow.trigger': 'Trigger Task',
            'workflow.progress': 'Task Progress',

            // Settings
            'settings.title': 'Settings',
            'settings.description': 'Customize UI preferences and manage workflow configuration. Click "Save" to apply changes.',
            'settings.workflow_desc': 'Same as the "Workflow Config" section on the Workflow page. Changes take effect after saving; API keys show only the first 4 characters.',

            // Toast
            'toast.rebuild_started': 'Rebuild task started',
            'toast.rebuild_done': 'Index rebuild complete',
            'toast.rebuild_failed': 'Rebuild failed',
            'toast.task_failed': 'Task failed',

            // Progress
            'progress.waiting': 'Waiting...',
            'progress.running': 'Running',
            'progress.done': 'Done',
            'progress.failed': 'Failed',

            // Authors
            'authors.merge_hint': 'Found {count} duplicate author groups ({total} records). Click "Merge" to disambiguate.',
            'authors.search_name': 'Name keyword',
            'authors.search_affiliation': 'Affiliation keyword',

            // Filters
            'filter.start_year': 'From',
            'filter.end_year': 'To',
            'filter.journal': 'Journal',
            'filter.source': 'Source',
            'filter.error_class': 'Error class filter',

            // Brand
            'brand.title': 'Literature System',
            'brand.subtitle': 'Academic Literature Knowledge Platform',

            // Language
            'lang.switch': '中文',

            // Knowledge card sections
            'knowledge.evidence_generation': 'Evidence Generation',
            'knowledge.key_claims_title': 'Key Claims',
            'knowledge.boundaries_title': 'Boundaries & Open Issues',
            'knowledge.reusable_title': 'Reusable Insights',
            'knowledge.items_count': '{count} items',
            'knowledge.no_card_text': 'No knowledge card available',
            'knowledge.claim_source.author': 'Author',
            'knowledge.claim_source.user': 'User Annotation',
            'knowledge.claim_source.llm': 'LLM Extraction',
            'knowledge.claim_evidence': 'Evidence',
            'knowledge.claim_condition': 'Condition',
            'knowledge.claim_counter': 'Counter',
            'knowledge.claim_anchor': 'Anchor',
            'knowledge.boundary_acknowledged': 'Acknowledged',
            'knowledge.boundary_result_shown': 'Result Shown',
            'knowledge.boundary_unconfirmed': 'Unconfirmed',
            'knowledge.boundary_temporal': 'Temporal',
            'knowledge.boundary_spatial': 'Spatial',
            'knowledge.boundary_methodological': 'Methodological',
            'knowledge.boundary_empty': 'None',
            'knowledge.inspiration.method': 'Method',
            'knowledge.inspiration.dataset': 'Dataset',
            'knowledge.inspiration.framework': 'Framework',
            'knowledge.inspiration.metric': 'Metric',
            'knowledge.inspiration.tool': 'Tool',
            'knowledge.inspiration.general': 'Insight',

            // Methods
            'methods.no_data': 'No method workflow available',
            'methods.methodology': 'Methodology',
            'methods.workflow': 'Experiment/Analysis Pipeline',
            'methods.data_sources': 'Data Sources & Samples',
            'methods.models_algorithms': 'Models/Algorithms',
            'methods.evaluation_metrics': 'Evaluation Metrics',

            // Data points table
            'datapoints.no_data': 'No data points available',
            'datapoints.metric': 'Metric',
            'datapoints.value': 'Value',
            'datapoints.unit': 'Unit',
            'datapoints.context': 'Context',
            'datapoints.page': 'Page',
            'datapoints.confidence': 'Confidence',
            'datapoints.unnamed': 'Unnamed',

            // Sections
            'sections.no_data': 'No sections',
            'sections.other': 'Section {num}',

            // Figures
            'figures.no_data': 'No figures',
            'figures.page_label': 'Page',
            'figures.unknown_page': 'Unknown',

            // Citations
            'citations.no_data': 'No citations',

            // Similar papers
            'similar.no_data': 'No similar papers',
            'similar.similarity': 'Similarity',

            // Facet
            'facet.no_data': 'No aggregation data',

            // Pagination
            'pagination.prev': 'Previous',
            'pagination.next': 'Next',
            'pagination.info': 'Page {current}/{total} ({total_items} total)',

            // Table
            'table.no_data': 'No data',

            // Tag cloud
            'tagcloud.no_data': 'No tags',

            // Graph controls
            'graph.controls.reset': 'Reset View',
            'graph.controls.relayout': 'Re-layout',
            'graph.controls.show_all_labels': 'Show All Labels',
            'graph.controls.smart_labels': 'Smart Labels',
            'graph.controls.focus_depth': 'Focus Depth: {depth}-hop',
            'graph.controls.toggle': 'Graph Controls',
            'graph.controls.title': '\u2699',

            // Graph sidebar
            'graph.sidebar.node_types': 'Node Types',
            'graph.sidebar.year_range': 'Year Range',
            'graph.sidebar.citations_nodes': 'Citations & Nodes',
            'graph.sidebar.min_citations': 'Min Citations',
            'graph.sidebar.max_nodes': 'Max Nodes',
            'graph.sidebar.display_options': 'Display Options',
            'graph.sidebar.citation_only': 'Citation Network Only',
            'graph.sidebar.show_labels': 'Show Labels',
            'graph.sidebar.node_locate': 'Node Search',
            'graph.sidebar.node_search_placeholder': 'Type node name, press Enter',
            'graph.sidebar.node_search_hint': 'Supports paper title, author, keyword',
            'graph.sidebar.graph_health': 'Graph Health',
            'graph.sidebar.health_loading': 'Loading...',
            'graph.sidebar.refresh': 'Refresh Graph',

            // Graph toolbar
            'graph.toolbar.year': 'Year',
            'graph.toolbar.min_citations': 'Min Citations',
            'graph.toolbar.max_nodes': 'Max Nodes',
            'graph.toolbar.refresh': 'Refresh Graph',

            // Graph legend
            'graph.legend.upstream': 'Upstream (cited by)',
            'graph.legend.downstream': 'Downstream (cites)',
            'graph.legend.two_hop': '2-hop neighbors',

            // Timeline chart
            'timeline.chart.paper_count': 'Papers',
            'timeline.chart.parse_done': 'Parsed',
            'timeline.chart.data_points': 'Data Points',
            'timeline.chart.y_left_label': 'Papers / Parsed',
            'timeline.chart.y_right_label': 'Data Points',

            // Search bar
            'search.field_labels.all': 'All Fields',
            'search.field_labels.title': 'Title',
            'search.field_labels.abstract': 'Abstract',
            'search.field_labels.keywords': 'Keywords',
            'search.field_labels.author': 'Author',
            'search.field_labels.journal': 'Journal',
            'search.field_labels.doi': 'DOI',
            'search.field_labels.year': 'Year',
            'search.field_labels.fulltext': 'Full Text',
            'search.placeholder.papers': 'Enter keywords, phrases...',
            'search.placeholder.data_points': 'Metric name, e.g. cattle count',
            'search.placeholder.knowledge': 'Research question / conclusion / claim',
            'search.placeholder.methods': 'Method / data source / algorithm',
            'search.add_field': '+ Add Field',
            'search.clear': 'Clear',
            'search.journal_tier': 'Journal Tier',
            'search.advanced_search': '\u25bc Advanced Search',
            'search.advanced_search_collapsed': '\u25b6 Advanced Search (collapsed)',
            'search.advanced_hint': 'Multi-field + Journal Tier + Mode',
            'search.advanced_hint_collapsed': 'Click to expand multi-field / tier / mode',
            'search.default_browse': 'Default Browse',
            'search.default_browse_label': 'Default Browse',
            'search.sort.year_desc': 'Year Desc',
            'search.sort.year_asc': 'Year Asc',
            'search.sort.citations_desc': 'Citations Desc',
            'search.sort.title_asc': 'Title Asc',
            'search.facet_panel': 'Facets',
            'search.facet_panel_default': 'Default Browse',
            'search.no_query_hint': 'No query entered. Browsing all papers sorted by default.\n\nEnter keywords or select filters to activate precise search.',
            'search.tier_current': 'Current Tier',
            'search.tier_none': 'None',
            'search.tier_hint_selected': 'Adjust tier selection in the Advanced Search area above.',
            'search.tier_hint_none': 'Click T1/T2/T3/Other in the Advanced Search area to filter.',
            'search.usage_hint_title': 'Tips',
            'search.usage_hint': 'Advanced Search bar can be pinned\nMulti-field rows support add/delete\nModes: Keyword / Phrase / Fuzzy / Vector / Hybrid',

            // Dashboard table
            'dashboard.table.stage': 'Stage',
            'dashboard.table.status': 'Status',
            'dashboard.table.count': 'Count',

            // Compare
            'compare.title': 'Compare',
            'compare.no_data': 'No comparison data',

            // Vector DB
            'vector.title': 'Vector DB',
            'vector.no_data': 'No vector data',

            // Authors
            'authors.title': 'Authors',
            'authors.no_data': 'No author data',

            // Institutions
            'institutions.title': 'Institutions',
            'institutions.no_data': 'No institution data',

            // Workflow
            'workflow.title': 'Workflow',
            'workflow.no_data': 'No workflow data',

            // Quality
            'quality.title': 'Quality Monitor',
            'quality.no_data': 'No quality data',

            // Settings
            'settings.title': 'Settings',
            'settings.no_data': 'No settings data',

            // Network
            'network.title': 'Network',
            'network.no_data': 'No network data',

            // Tooltip
            'tooltip.type': 'Type',
            'tooltip.year': 'Year',
            'tooltip.citations': 'Citations',
            'tooltip.connections': 'Connections',
            'tooltip.occurrences': 'Occurrences',
            'tooltip.paper_count': 'Papers',
            'tooltip.click_focus': 'Click to focus, double-click for details',

            // Search field hints
            'search.field_input_placeholder': 'Enter {field}',
            'search.year_input_placeholder': 'e.g. 2020-2024 or 2023',
            'search.delete_row_title': 'Delete this row',
            'search.max_fields_toast': 'Maximum 6 field rows',

            // Toast messages
            'toast.load_failed': '{context} load failed: {reason}',
            'toast.additional_data_load_failed': 'Some additional data failed to load, check console',
            'toast.network_load_failed': 'Citation network load failed',
            'toast.graph_load_failed': 'Graph load failed',

            // Paper detail tabs
            'paper.tab.abstract': 'Abstract',
            'paper.tab.sections': 'Sections',
            'paper.tab.figures': 'Figures',
            'paper.tab.citations': 'Citations',
            'paper.tab.knowledge': 'Knowledge Card',
            'paper.tab.methods': 'Methods',
            'paper.tab.data': 'Data Points',

            // Paper meta
            'paper.meta.unknown': 'Unknown',
            'paper.meta.none': 'None',
            'paper.meta.unknown_paper': 'Paper {id}',
            'paper.meta.doi': 'DOI',
            'paper.meta.year': 'Year',
            'paper.meta.journal': 'Journal',
            'paper.meta.source': 'Source',
            'paper.meta.cited_by': 'Cited by',
            'paper.meta.similar_papers': 'Similar Papers',
            'paper.meta.author': 'Author',
            'paper.meta.keywords': 'Keywords',
        }
    };

    function t(key, params) {
        let text = translations[currentLang]?.[key] || translations.zh?.[key] || key;
        if (params) {
            Object.keys(params).forEach(k => {
                text = text.replace(`{${k}}`, params[k]);
            });
        }
        return text;
    }

    function setLang(lang) {
        if (translations[lang]) {
            currentLang = lang;
            localStorage.setItem(LANG_KEY, lang);
            updatePageTexts();
            updateLangButton();
        }
    }

    function toggle() {
        setLang(currentLang === 'zh' ? 'en' : 'zh');
    }

    function getLang() {
        return currentLang;
    }

    function updateLangButton() {
        const btn = document.getElementById('lang-switch');
        if (btn) {
            btn.textContent = t('lang.switch');
        }
    }

    function updatePageTexts() {
        // Update all elements with data-i18n attribute
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.dataset.i18n;
            if (el.tagName === 'INPUT' && el.type === 'text') {
                el.placeholder = t(key);
            } else {
                el.textContent = t(key);
            }
        });

        // Update title
        document.title = t('brand.title');

        // Update brand
        const brandH1 = document.querySelector('.brand h1');
        const brandSub = document.querySelector('.brand .subtitle');
        if (brandH1) brandH1.textContent = t('brand.title');
        if (brandSub) brandSub.textContent = t('brand.subtitle');

        // Update global search input placeholder
        const globalInput = document.getElementById('global-search-input');
        if (globalInput) globalInput.placeholder = t('common.placeholder');

        // Update global search button
        const globalBtn = document.getElementById('global-search-btn');
        if (globalBtn) globalBtn.textContent = t('common.search');

        // Update settings button
        const settingsBtn = document.getElementById('btn-settings');
        if (settingsBtn) settingsBtn.textContent = t('common.settings');

        // Update rebuild button
        const rebuildBtn = document.getElementById('btn-rebuild');
        if (rebuildBtn) rebuildBtn.textContent = t('common.rebuild_index');

        // Update service status
        const statusDot = document.getElementById('service-status');
        const statusText = document.getElementById('service-text');
        if (statusDot && statusText) {
            if (statusDot.classList.contains('ok')) {
                statusText.textContent = t('common.service_ok');
            } else if (statusDot.classList.contains('error')) {
                statusText.textContent = t('common.service_error');
            }
        }
    }

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', () => {
        updateLangButton();
        updatePageTexts();
    });

    return { t, setLang, toggle, getLang, updatePageTexts, updateLangButton };
})();