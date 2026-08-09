// 主应用：路由、页面视图、全局事件
(function () {
    const content = document.getElementById('content');
    const statusDot = document.getElementById('service-status');
    const statusText = document.getElementById('service-text');

    // 搜索状态
    let searchState = {
        q: '',
        mode: 'keyword',
        filters: {},
        offset: 0,
        limit: 20,
        result: null,
        activeTab: 'results',
        tab: 'papers',               // 内容标签页：papers/data_points/knowledge/methods
        fts_weight: 0.4,
        vector_weight: 0.6,
        default_sort: 'year_desc',   // 默认浏览模式下的排序
        journal_tiers: [],           // 期刊分级多选筛选：tier1/tier2/tier3/other
        // 字段化检索：每行 {field, value}
        field_rows: [
            { field: 'all', value: '' },
            { field: 'author', value: '' },
            { field: 'year', value: '' }
        ],
        // 高级检索条是否折叠（默认折叠，节省页面占用）
        gsb_collapsed: localStorage.getItem('gsb_collapsed') !== 'false'
    };

    // 初始化
    document.addEventListener('DOMContentLoaded', () => {
        initNavigation();
        initGlobalSearch();
        initRebuildButton();
        initSettingsButton();
        initModal();
        checkHealth();
        setInterval(checkHealth, 10000);
        route();
    });

    window.addEventListener('hashchange', route);

    // ------------------ 路由 ------------------
    function route() {
        const hash = window.location.hash || '#/dashboard';
        const [path, query] = hash.slice(1).split('?');
        updateNav(path);
        // 仅 /search 路由显示顶部 sticky 高级检索条；其他页面隐藏
        const bar = document.getElementById('global-search-bar');
        if (bar) {
            bar.style.display = path === '/search' ? 'block' : 'none';
            if (path !== '/search') bar.innerHTML = '';
        }
        content.innerHTML = '<div class="loading-text">' + I18n.t('common.loading') + '</div>';

        if (path === '/dashboard' || path === '') {
            renderDashboard();
        } else if (path === '/search') {
            renderSearch(query);
        } else if (path.startsWith('/paper/')) {
            const id = path.split('/')[2];
            renderPaperDetail(id);
        } else if (path === '/knowledgebase') {
            // 重定向到检索页面的知识库标签页
            window.location.hash = '#/search?tab=' + (query ? parseQuery(query).tab || 'papers' : 'papers');
            return;
        } else if (path === '/timeline') {
            renderTimeline(query);
        } else if (path === '/compare') {
            renderCompare();
        } else if (path === '/network') {
            renderNetwork(query);
        } else if (path === '/vectordb') {
            renderVectorDB();
        } else if (path === '/authors') {
            renderAuthors(query);
        } else if (path.startsWith('/author/')) {
            const id = path.split('/')[2];
            renderAuthorDetail(id);
        } else if (path === '/institutions') {
            renderInstitutions(query);
        } else if (path === '/workflow') {
            renderWorkflow();
        } else if (path === '/quality') {
            renderQuality();
        } else if (path === '/settings') {
            renderSettings();
        } else {
            content.innerHTML = '<div class="empty-state">' + I18n.t('common.page_not_found') + '</div>';
        }
    }

    function updateNav(path) {
        document.querySelectorAll('.nav-item').forEach(el => {
            el.classList.toggle('active', path.startsWith('/' + el.dataset.route));
        });
    }

    function initNavigation() {
        document.querySelectorAll('.nav-item').forEach(el => {
            el.addEventListener('click', () => {
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                el.classList.add('active');
            });
        });
    }

    // ------------------ 健康检查 ------------------
    async function checkHealth() {
        try {
            await API.health();
            statusDot.className = 'status-dot ok';
            statusText.textContent = I18n.t('common.service_ok');
        } catch (err) {
            statusDot.className = 'status-dot error';
            statusText.textContent = I18n.t('common.service_error');
        }
    }

    // ------------------ 全局搜索 ------------------
    function initGlobalSearch() {
        const input = document.getElementById('global-search-input');
        const btn = document.getElementById('global-search-btn');
        const doSearch = () => {
            const q = input.value.trim();
            if (!q) return;
            window.location.hash = `#/search?q=${encodeURIComponent(q)}&mode=keyword`;
        };
        btn.addEventListener('click', doSearch);
        input.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });
    }

    // ------------------ 重建索引 ------------------
    function initRebuildButton() {
        const btn = document.getElementById('btn-rebuild');
        btn.addEventListener('click', async () => {
            if (!confirm(I18n.t('common.confirm_rebuild'))) return;
            btn.disabled = true;
            try {
                const { task_id } = await API.rebuild();
                showToast(I18n.t('toast.rebuild_started') + `: ${task_id}`, 'success');
                showProgress(task_id, () => {
                    btn.disabled = false;
                    showToast(I18n.t('toast.rebuild_done'), 'success');
                    if (window.location.hash.startsWith('#/dashboard')) renderDashboard();
                });
            } catch (err) {
                btn.disabled = false;
                showToast(I18n.t('toast.rebuild_failed') + ': ' + err.message, 'error');
            }
        });
    }

    // ------------------ 顶部栏设置按钮 ------------------
    function initSettingsButton() {
        const btn = document.getElementById('btn-settings');
        if (!btn) return;
        btn.addEventListener('click', () => {
            window.location.hash = '#/settings';
        });
    }

    function showProgress(taskId, onDone) {
        openModal(I18n.t('workflow.progress'), `<div id="progress-area"><div class="progress-wrap">
            <div class="progress-bar"><div class="progress-fill" id="progress-fill"></div></div>
            <div class="progress-text" id="progress-text">${I18n.t('progress.waiting')}</div>
        </div></div>`);
        Utils.pollProgress(taskId, (task) => {
            const fill = document.getElementById('progress-fill');
            const text = document.getElementById('progress-text');
            if (fill) fill.style.width = task.progress + '%';
            const statusText = task.status === 'done' ? I18n.t('progress.done') : task.status === 'failed' ? I18n.t('progress.failed') : I18n.t('progress.running');
            if (text) text.textContent = `${statusText} | ${task.message || ''} (${task.progress.toFixed(0)}%)`;
        }, (task) => {
            // 完成状态让用户短暂看到 100%，失败立即关闭
            const closeDelay = task.status === 'done' ? 600 : 0;
            setTimeout(() => {
                closeModal();
                if (task.status === 'failed') {
                    showToast(I18n.t('toast.task_failed') + ': ' + (task.error || task.message), 'error');
                }
                if (onDone) onDone(task);
            }, closeDelay);
        });
    }

    // ------------------ Dashboard ------------------
    async function renderDashboard() {
        content.innerHTML = '<div class="loading-text">' + I18n.t('common.loading_stats') + '</div>';
        try {
            const stats = await API.stats();
            let html = '<h2 style="margin-top:0;">' + I18n.t('dashboard.title') + '</h2><div class="card-grid">';
            html += Components.statCard(I18n.t('dashboard.total_papers'), stats.total_papers || 0);
            // 2026-08-01：区分总论文 vs 有效论文（排除占位）
            html += Components.statCard(I18n.t('dashboard.valid_papers'), stats.valid_papers || 0);
            html += Components.statCard(I18n.t('dashboard.indexed_papers'), stats.indexed_papers || 0);
            html += Components.statCard(I18n.t('dashboard.coverage'), (stats.coverage || 0) + '%');
            html += Components.statCard(I18n.t('dashboard.sections'), stats.sections || 0);
            html += Components.statCard(I18n.t('dashboard.figures'), stats.figures || 0);
            html += Components.statCard(I18n.t('dashboard.data_points'), stats.data_points || 0);
            if (stats.data_points_valid !== undefined) {
                html += Components.statCard(I18n.t('dashboard.valid_data_points'), stats.data_points_valid || 0);
            }
            html += '</div>';

            html += '<div class="card"><h3 class="card-title">' + I18n.t('dashboard.parse_jobs') + '</h3>';
            if (stats.parse_jobs && stats.parse_jobs.length) {
                html += '<table class="data-table"><thead><tr><th>' + I18n.t('dashboard.table.stage') + '</th><th>' + I18n.t('dashboard.table.status') + '</th><th>' + I18n.t('dashboard.table.count') + '</th></tr></thead><tbody>';
                stats.parse_jobs.forEach(j => {
                    html += `<tr><td>${j.stage || ''}</td><td>${j.status || ''}</td><td>${j.c}</td></tr>`;
                });
                html += '</tbody></table>';
            } else {
                html += '<div class="empty-state">' + I18n.t('dashboard.no_parse_jobs') + '</div>';
            }
            html += '</div>';

            content.innerHTML = html;
        } catch (err) {
            console.error('[dashboard] 加载失败:', err);
            content.innerHTML = `<div class="empty-state">${I18n.t('common.load_failed')}: ${err.message}</div>`;
            showToast(I18n.t('common.load_failed') + ': ' + err.message, 'error');
        }
    }

    // ------------------ Search ------------------
    async function renderSearch(queryString) {
        const params = parseQuery(queryString);
        searchState.q = params.q || '';
        searchState.mode = params.mode || 'keyword';
        searchState.offset = parseInt(params.offset || '0', 10);
        searchState.tab = params.tab || 'papers';
        searchState.fts_weight = parseFloat(params.fts_weight) || 0.4;
        searchState.vector_weight = parseFloat(params.vector_weight) || 0.6;
        searchState.default_sort = params.sort || 'year_desc';
        searchState.journal_tiers = params.journal_tiers ? params.journal_tiers.split(',').filter(Boolean) : [];
        searchState.filters = {};
        ['year_from', 'year_to', 'year', 'journal', 'author', 'language', 'source', 'doi'].forEach(k => {
            if (params[k]) searchState.filters[k] = params[k];
        });
        // 字段化检索行：从 URL 恢复（field1=..&q1=..&field2=..&q2=..）
        const fieldOptions = ['all', 'title', 'abstract', 'keywords', 'author', 'journal', 'doi', 'year', 'fulltext'];
        const restored = [];
        for (let i = 1; i <= 5; i++) {
            const f = params[`field${i}`];
            const v = params[`q${i}`];
            if (f && fieldOptions.includes(f)) {
                restored.push({ field: f, value: v || '' });
            } else if (v && !f) {
                restored.push({ field: 'all', value: v });
            }
        }
        if (restored.length) {
            searchState.field_rows = restored;
        }
        if (params.q && !restored.length) {
            // 兼容旧 URL：单 q 参数映射到 all 字段
            searchState.field_rows = [{ field: 'all', value: params.q }];
        }

        // 渲染顶部 sticky 高级搜索条（与全局关键词并排）
        renderGlobalSearchBar();
        content.innerHTML = buildSearchLayout();
        bindSearchControls();

        const hasQuery = searchState.q || Object.keys(searchState.filters).length
            || searchState.journal_tiers.length
            || searchState.field_rows.some(r => r.value.trim());
        if (hasQuery || searchState.tab !== 'papers') {
            await doSearch();
        } else {
            await loadSearchDefault();
        }
    }

    // 渲染顶部 sticky 高级搜索条（含全局关键词、字段行、模式、按钮）
    function renderGlobalSearchBar() {
        const bar = document.getElementById('global-search-bar');
        if (!bar) return;
        const isPaperTab = searchState.tab === 'papers';
        const fieldLabels = {
            all: I18n.t('search.field_labels.all'), title: I18n.t('search.field_labels.title'), abstract: I18n.t('search.field_labels.abstract'), keywords: I18n.t('search.field_labels.keywords'),
            author: I18n.t('search.field_labels.author'), journal: I18n.t('search.field_labels.journal'), doi: I18n.t('search.field_labels.doi'), year: I18n.t('search.field_labels.year'), fulltext: I18n.t('search.field_labels.fulltext')
        };
        const placeholders = {
            papers: I18n.t('search.placeholder.papers'),
            data_points: I18n.t('search.placeholder.data_points'),
            knowledge: I18n.t('search.placeholder.knowledge'),
            methods: I18n.t('search.placeholder.methods')
        };
        // 字段行（仅 papers tab 显示完整版，其他 tab 用单一输入框）
        let fieldRowsHtml = '';
        if (isPaperTab) {
            const rows = searchState.field_rows.map((row, idx) => {
                const isYear = row.field === 'year';
                const inputHtml = isYear
                    ? `<input type="text" class="field-row-input" data-idx="${idx}" value="${Utils.escapeHtml(row.value)}" placeholder="如 2020-2024 或 2023" autocomplete="off">`
                    : `<input type="text" class="field-row-input" data-idx="${idx}" value="${Utils.escapeHtml(row.value)}" placeholder="输入${fieldLabels[row.field] || ''}" autocomplete="off">`;
                return `<div class="field-row" data-idx="${idx}">
                    <select class="field-row-select" data-idx="${idx}" aria-label="检索字段">
                        ${Object.entries(fieldLabels).map(([k, v]) => `<option value="${k}" ${row.field === k ? 'selected' : ''}>${v}</option>`).join('')}
                    </select>
                    ${inputHtml}
                    <button type="button" class="field-row-remove" data-idx="${idx}" title="删除该行" aria-label="删除">×</button>
                </div>`;
            }).join('');
            const modes = [
                { v: 'keyword', l: I18n.t('search.mode_keyword') },
                { v: 'phrase', l: I18n.t('search.mode_phrase') },
                { v: 'fuzzy', l: I18n.t('search.mode_fuzzy') },
                { v: 'vector', l: I18n.t('search.mode_vector') },
                { v: 'hybrid', l: I18n.t('search.mode_hybrid') }
            ];
            fieldRowsHtml = `
                <div class="gsb-fields" id="gsb-fields">
                    ${rows}
                </div>
                <div class="gsb-controls">
                    <select id="search-mode" aria-label="检索模式">
                        ${modes.map(m => `<option value="${m.v}" ${searchState.mode === m.v ? 'selected' : ''}>${m.l}</option>`).join('')}
                    </select>
                    <button type="button" id="field-row-add" class="btn-ghost">${I18n.t('search.add_field')}</button>
                    <button type="button" class="btn btn-primary" id="search-btn">${I18n.t('common.search')}</button>
                    <button type="button" id="field-row-clear" class="btn-ghost">${I18n.t('search.clear')}</button>
                </div>
            `;
        } else {
            // 非 papers tab：单一关键词输入框
            fieldRowsHtml = `
                <div class="gsb-simple">
                    <input type="text" id="search-q-kb" value="${Utils.escapeHtml(searchState.q)}" placeholder="${placeholders[searchState.tab] || placeholders.papers}" autocomplete="off">
                    <select id="search-mode" aria-label="检索模式">
                        <option value="keyword" ${searchState.mode === 'keyword' ? 'selected' : ''}>${I18n.t('search.mode_keyword')}</option>
                        <option value="phrase" ${searchState.mode === 'phrase' ? 'selected' : ''}>${I18n.t('search.mode_phrase')}</option>
                        <option value="fuzzy" ${searchState.mode === 'fuzzy' ? 'selected' : ''}>${I18n.t('search.mode_fuzzy')}</option>
                        <option value="vector" ${searchState.mode === 'vector' ? 'selected' : ''}>${I18n.t('search.mode_vector')}</option>
                        <option value="hybrid" ${searchState.mode === 'hybrid' ? 'selected' : ''}>${I18n.t('search.mode_hybrid')}</option>
                    </select>
                    <button type="button" class="btn btn-primary" id="search-btn-kb">${I18n.t('common.search')}</button>
                </div>
            `;
        }
        // 期刊分级 chips（紧凑）
        const tiers = [
            { key: 'tier1', label: 'T1', color: '#1e40af' },
            { key: 'tier2', label: 'T2', color: '#166534' },
            { key: 'tier3', label: 'T3', color: '#92400e' },
            { key: 'other', label: I18n.t('search.tier_none'), color: '#6b7280' }
        ];
        const tierHtml = `
            <div class="gsb-tiers">
                <span class="gsb-tiers-label">${I18n.t('search.journal_tier')}</span>
                <div class="tier-chips" id="tier-chips">
                    ${tiers.map(t => `
                        <button type="button" class="tier-chip ${searchState.journal_tiers.includes(t.key) ? 'active' : ''}" data-tier="${t.key}" title="点击多选"
                            style="padding:3px 10px;border:1.5px solid ${searchState.journal_tiers.includes(t.key) ? t.color : '#e5e7eb'};border-radius:12px;background:${searchState.journal_tiers.includes(t.key) ? t.color : 'white'};color:${searchState.journal_tiers.includes(t.key) ? 'white' : t.color};font-size:11px;font-weight:600;cursor:pointer;transition:all 0.15s;">
                            ${t.label}
                        </button>
                    `).join('')}
                </div>
            </div>
        `;
        bar.innerHTML = `
            <div class="gsb-inner ${searchState.gsb_collapsed ? 'collapsed' : ''}">
                <div class="gsb-title" id="gsb-title" role="button" tabindex="0" title="点击展开/折叠高级检索">
                    <span class="gsb-title-main">${searchState.gsb_collapsed ? I18n.t('search.advanced_search_collapsed') : I18n.t('search.advanced_search')}</span>
                    <span class="gsb-title-sub">${isPaperTab ? (searchState.gsb_collapsed ? I18n.t('search.advanced_hint_collapsed') : I18n.t('search.advanced_hint')) : I18n.t('search.advanced_hint')}</span>
                </div>
                ${tierHtml}
                <div class="gsb-divider"></div>
                <div class="gsb-fields-wrap" id="gsb-fields-wrap" style="${searchState.gsb_collapsed ? 'display:none;' : ''}">
                    ${fieldRowsHtml}
                </div>
            </div>
        `;
        bar.style.display = 'block';
    }

    function buildSearchLayout() {
        const isDefault = searchState.tab === 'papers'
            && !(searchState.q || Object.keys(searchState.filters).length
                 || searchState.journal_tiers.length
                 || searchState.field_rows.some(r => r.value.trim()));
        const isPaperTab = searchState.tab === 'papers';
        const tiers = [
            { key: 'tier1', label: 'T1', desc: 'Nature/Science/Cell/Lancet', color: '#1e40af' },
            { key: 'tier2', label: 'T2', desc: '子刊/PNAS/SA等', color: '#166534' },
            { key: 'tier3', label: 'T3', desc: 'ES&T/WR等', color: '#92400e' },
            { key: 'other', label: '其他', desc: '其他期刊', color: '#6b7280' }
        ];
        return `<div class="search-layout">
            <aside class="search-filters card" id="facets-panel">
                <h3 class="card-title">${isDefault ? I18n.t('search.facet_panel_default') : I18n.t('search.facet_panel')}</h3>
                <div class="empty-state" id="facets-default" style="${isDefault ? '' : 'display:none;'}">
                    <div style="font-size:13px;color:var(--text-secondary);line-height:1.7;">
                        ${I18n.t('search.no_query_hint').replace(/\n/g, '<br>')}
                    </div>
                </div>
                <div class="journal-tier-facets" style="margin-top:14px;">
                    <label style="font-size:13px;font-weight:600;color:var(--text-primary);display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                        <span>${I18n.t('search.tier_current')}</span>
                        <span style="font-size:11px;font-weight:400;color:var(--text-secondary);">${searchState.journal_tiers.length ? searchState.journal_tiers.map(t => 'T' + t.replace('tier','').replace('other','其他')).join('+') : I18n.t('search.tier_none')}</span>
                    </label>
                    <div style="font-size:12px;color:var(--text-secondary);line-height:1.6;">
                        ${searchState.journal_tiers.length
                            ? I18n.t('search.tier_hint_selected')
                            : I18n.t('search.tier_hint_none')}
                    </div>
                </div>
                <div class="search-hint" style="margin-top:18px;padding-top:14px;border-top:1px dashed var(--border);">
                    <div style="font-size:12px;color:var(--text-secondary);line-height:1.7;">
                        <strong style="color:var(--text-primary);">${I18n.t('search.usage_hint_title')}</strong><br>
                        ${I18n.t('search.usage_hint').replace(/\n/g, '<br>')}
                    </div>
                </div>
            </aside>
            <div class="search-results">
                <div id="hybrid-weights" class="hybrid-weights" style="display:${searchState.mode === 'hybrid' && isPaperTab ? 'flex' : 'none'};">
                    <div class="weight-control">
                        <label for="fts-weight">FTS5 权重</label>
                        <input type="range" id="fts-weight" min="0" max="1" step="0.05" value="${searchState.fts_weight}">
                        <span id="fts-weight-val">${searchState.fts_weight.toFixed(2)}</span>
                    </div>
                    <div class="weight-control">
                        <label for="vector-weight">向量权重</label>
                        <input type="range" id="vector-weight" min="0" max="1" step="0.05" value="${searchState.vector_weight}">
                        <span id="vector-weight-val">${searchState.vector_weight.toFixed(2)}</span>
                    </div>
                </div>
                <div class="search-tabs">
                    <button class="search-tab ${searchState.tab === 'papers' ? 'active' : ''}" data-tab="papers">${I18n.t('search.papers_tab')}</button>
                    <button class="search-tab ${searchState.tab === 'data_points' ? 'active' : ''}" data-tab="data_points">${I18n.t('search.data_points_tab')}</button>
                    <button class="search-tab ${searchState.tab === 'knowledge' ? 'active' : ''}" data-tab="knowledge">${I18n.t('search.knowledge_tab')}</button>
                    <button class="search-tab ${searchState.tab === 'methods' ? 'active' : ''}" data-tab="methods">${I18n.t('search.methods_tab')}</button>
                </div>
                <div class="search-toolbar" style="display:${isDefault ? 'flex' : 'none'};align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap;">
                    <span style="font-size:13px;color:var(--text-secondary);">${I18n.t('search.default_browse_label')}</span>
                    <select id="search-default-sort" class="form-select" style="width:auto;min-width:140px;">
                        <option value="year_desc" ${searchState.default_sort === 'year_desc' ? 'selected' : ''}>${I18n.t('search.sort.year_desc')}</option>
                        <option value="year_asc" ${searchState.default_sort === 'year_asc' ? 'selected' : ''}>${I18n.t('search.sort.year_asc')}</option>
                        <option value="citations_desc" ${searchState.default_sort === 'citations_desc' ? 'selected' : ''}>${I18n.t('search.sort.citations_desc')}</option>
                        <option value="title_asc" ${searchState.default_sort === 'title_asc' ? 'selected' : ''}>${I18n.t('search.sort.title_asc')}</option>
                    </select>
                </div>
                <div id="active-filters" style="margin-bottom:12px;"></div>
                <div id="search-result-area">
                    <div class="loading-text">${I18n.t('common.loading')}</div>
                </div>
            </div>
        </div>`;
    }

    function buildFieldSearchBox(fieldLabels) {
        const rows = searchState.field_rows.map((row, idx) => {
            const isYear = row.field === 'year';
            const inputHtml = isYear
                ? `<input type="text" class="field-row-input" data-idx="${idx}" value="${Utils.escapeHtml(row.value)}" placeholder="${I18n.t('search.year_input_placeholder')}">`
                : `<input type="text" class="field-row-input" data-idx="${idx}" value="${Utils.escapeHtml(row.value)}" placeholder="${I18n.t('search.field_input_placeholder', {field: fieldLabels[row.field] || ''})}">`;
            return `<div class="field-row" data-idx="${idx}" style="display:flex;gap:8px;align-items:center;margin-bottom:8px;">
                <select class="field-row-select" data-idx="${idx}" style="width:120px;padding:11px 10px;border:1px solid var(--border);border-radius:var(--radius-sm);background:#fff;font-size:14px;outline:none;cursor:pointer;flex-shrink:0;">
                    ${Object.entries(fieldLabels).map(([k, v]) => `<option value="${k}" ${row.field === k ? 'selected' : ''}>${v}</option>`).join('')}
                </select>
                ${inputHtml}
                <button type="button" class="field-row-remove" data-idx="${idx}" title="${I18n.t('search.delete_row_title')}" style="width:36px;height:36px;border:1px solid var(--border);border-radius:var(--radius-sm);background:#fff;cursor:pointer;color:#9ca3af;font-size:16px;flex-shrink:0;display:flex;align-items:center;justify-content:center;">×</button>
            </div>`;
        }).join('');
        const modeHtml = `<div class="field-row-mode" style="display:flex;gap:8px;align-items:center;margin-top:4px;flex-wrap:wrap;">
            <select id="search-mode" style="padding:11px 14px;border:1px solid var(--border);border-radius:var(--radius-sm);background:#fff;font-size:14px;outline:none;cursor:pointer;min-width:120px;">
                <option value="keyword" ${searchState.mode === 'keyword' ? 'selected' : ''}>${I18n.t('search.mode_keyword')}</option>
                <option value="phrase" ${searchState.mode === 'phrase' ? 'selected' : ''}>${I18n.t('search.mode_phrase')}</option>
                <option value="fuzzy" ${searchState.mode === 'fuzzy' ? 'selected' : ''}>${I18n.t('search.mode_fuzzy')}</option>
                <option value="vector" ${searchState.mode === 'vector' ? 'selected' : ''}>${I18n.t('search.mode_vector')}</option>
                <option value="hybrid" ${searchState.mode === 'hybrid' ? 'selected' : ''}>${I18n.t('search.mode_hybrid')}</option>
            </select>
            <button type="button" id="field-row-add" style="padding:11px 16px;border:1px solid var(--border);border-radius:var(--radius-sm);background:#fff;font-size:13px;cursor:pointer;color:var(--text-primary);">${I18n.t('search.add_field')}</button>
            <button type="button" class="btn btn-primary" id="search-btn" style="padding:11px 24px;font-size:14px;">${I18n.t('common.search')}</button>
            <button type="button" id="field-row-clear" style="padding:11px 16px;border:none;background:none;font-size:13px;cursor:pointer;color:var(--text-secondary);">${I18n.t('search.clear')}</button>
        </div>`;
        return `<div class="field-search-box" id="field-search-box" style="background:white;padding:14px;border:1px solid var(--border);border-radius:var(--radius-sm);margin-bottom:14px;box-shadow:var(--shadow-sm);">
            ${rows}
            ${modeHtml}
        </div>`;
    }

    function buildSimpleSearchBox(placeholder) {
        return `<div class="search-box">
            <input type="text" id="search-q-kb" value="${Utils.escapeHtml(searchState.q)}" placeholder="${placeholder}">
            <button class="btn btn-primary" id="search-btn-kb">${I18n.t('common.search')}</button>
        </div>`;
    }

    function bindSearchControls() {
        const input = document.getElementById('search-q');
        const inputKb = document.getElementById('search-q-kb');
        const mode = document.getElementById('search-mode');
        const btn = document.getElementById('search-btn');
        const btnKb = document.getElementById('search-btn-kb');
        const weightPanel = document.getElementById('hybrid-weights');
        const ftsInput = document.getElementById('fts-weight');
        const vecInput = document.getElementById('vector-weight');
        const ftsVal = document.getElementById('fts-weight-val');
        const vecVal = document.getElementById('vector-weight-val');
        const defaultSort = document.getElementById('search-default-sort');

        // 高级检索条：点击标题折叠/展开
        const gsbTitle = document.getElementById('gsb-title');
        if (gsbTitle) {
            const toggleGsb = () => {
                searchState.gsb_collapsed = !searchState.gsb_collapsed;
                localStorage.setItem('gsb_collapsed', String(searchState.gsb_collapsed));
                const wrap = document.getElementById('gsb-fields-wrap');
                const inner = document.querySelector('.gsb-inner');
                const main = gsbTitle.querySelector('.gsb-title-main');
                const sub = gsbTitle.querySelector('.gsb-title-sub');
                if (wrap) wrap.style.display = searchState.gsb_collapsed ? 'none' : '';
                if (inner) inner.classList.toggle('collapsed', searchState.gsb_collapsed);
                if (main) main.textContent = searchState.gsb_collapsed ? I18n.t('search.advanced_search_collapsed') : I18n.t('search.advanced_search');
                if (sub && searchState.tab === 'papers') {
                    sub.textContent = searchState.gsb_collapsed
                        ? I18n.t('search.advanced_hint_collapsed')
                        : I18n.t('search.advanced_hint');
                }
            };
            gsbTitle.addEventListener('click', toggleGsb);
            gsbTitle.addEventListener('keydown', e => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    toggleGsb();
                }
            });
        }

        const updateWeights = () => {
            if (ftsInput) searchState.fts_weight = parseFloat(ftsInput.value) || 0;
            if (vecInput) searchState.vector_weight = parseFloat(vecInput.value) || 0;
            if (ftsVal) ftsVal.textContent = searchState.fts_weight.toFixed(2);
            if (vecVal) vecVal.textContent = searchState.vector_weight.toFixed(2);
        };
        const toggleWeights = () => {
            if (weightPanel) weightPanel.style.display = mode && mode.value === 'hybrid' ? 'flex' : 'none';
        };

        // 字段行模式下，触发搜索前先收集所有行的值
        const collectFieldRows = () => {
            const rows = [];
            document.querySelectorAll('.field-row').forEach(row => {
                const idx = parseInt(row.dataset.idx, 10);
                const field = row.querySelector('.field-row-select').value;
                const value = row.querySelector('.field-row-input').value.trim();
                rows.push({ field, value });
            });
            searchState.field_rows = rows;
        };

        const trigger = () => {
            if (input) {
                searchState.q = input.value.trim();
            } else if (inputKb) {
                searchState.q = inputKb.value.trim();
            } else {
                collectFieldRows();
                const allRow = searchState.field_rows.find(r => r.field === 'all' && r.value);
                searchState.q = allRow ? allRow.value : '';
            }
            if (mode) searchState.mode = mode.value;
            searchState.offset = 0;
            updateWeights();
            updateSearchUrl();
        };
        if (btn) { btn.addEventListener('click', trigger); }
        if (input) { input.addEventListener('keydown', e => { if (e.key === 'Enter') trigger(); }); }
        if (btnKb) { btnKb.addEventListener('click', trigger); }
        if (inputKb) { inputKb.addEventListener('keydown', e => { if (e.key === 'Enter') trigger(); }); }
        if (mode) { mode.addEventListener('change', () => { toggleWeights(); if ((input || inputKb || document.querySelector('.field-row-input')) && (input || inputKb || document.querySelector('.field-row-input')).value.trim()) trigger(); }); }
        if (ftsInput) ftsInput.addEventListener('input', updateWeights);
        if (vecInput) vecInput.addEventListener('input', updateWeights);
        if (ftsInput) ftsInput.addEventListener('change', () => { trigger(); });
        if (vecInput) vecInput.addEventListener('change', () => { trigger(); });

        // 字段行：添加/删除/字段切换
        const addBtn = document.getElementById('field-row-add');
        if (addBtn) {
            addBtn.addEventListener('click', () => {
                collectFieldRows();
                if (searchState.field_rows.length >= 6) {
                    showToast(I18n.t('search.max_fields_toast'), 'warning');
                    return;
                }
                searchState.field_rows.push({ field: 'all', value: '' });
                updateSearchUrl();
                renderSearch(window.location.hash.slice(1).split('?')[1] || '');
            });
        }
        const clearBtn = document.getElementById('field-row-clear');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                searchState.field_rows = [{ field: 'all', value: '' }];
                searchState.journal_tiers = [];
                searchState.filters = {};
                searchState.q = '';
                searchState.offset = 0;
                updateSearchUrl();
                renderSearch('');
            });
        }
        document.querySelectorAll('.field-row-remove').forEach(rm => {
            rm.addEventListener('click', () => {
                const idx = parseInt(rm.dataset.idx, 10);
                collectFieldRows();
                if (searchState.field_rows.length <= 1) {
                    showToast('至少保留一行', 'warning');
                    return;
                }
                searchState.field_rows.splice(idx, 1);
                updateSearchUrl();
                renderSearch(window.location.hash.slice(1).split('?')[1] || '');
            });
        });
        document.querySelectorAll('.field-row-input').forEach(inp => {
            inp.addEventListener('keydown', e => { if (e.key === 'Enter') trigger(); });
        });
        document.querySelectorAll('.field-row-select').forEach(sel => {
            sel.addEventListener('change', () => {
                collectFieldRows();
                updateSearchUrl();
            });
        });

        // 标签页切换
        document.querySelectorAll('.search-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                searchState.tab = tab.dataset.tab;
                searchState.offset = 0;
                updateSearchUrl();
                renderSearch(window.location.hash.slice(1).split('?')[1] || '');
            });
        });

        // 期刊分级多选 chip（固定显示在左侧栏，与 isDefault 解耦）
        const tierChipData = {
            tier1: '#1e40af',
            tier2: '#166534',
            tier3: '#92400e',
            other: '#6b7280'
        };
        document.querySelectorAll('.tier-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const tier = chip.dataset.tier;
                const idx = searchState.journal_tiers.indexOf(tier);
                if (idx >= 0) {
                    searchState.journal_tiers.splice(idx, 1);
                } else {
                    searchState.journal_tiers.push(tier);
                }
                searchState.offset = 0;
                // 立即更新 chip 样式（不重渲染整个页面，避免固定显示的位置失效）
                document.querySelectorAll('.tier-chip').forEach(c => {
                    const k = c.dataset.tier;
                    const active = searchState.journal_tiers.includes(k);
                    const color = tierChipData[k] || '#6b7280';
                    c.classList.toggle('active', active);
                    c.style.background = active ? color : 'white';
                    c.style.color = active ? 'white' : color;
                    c.style.borderColor = active ? color : '#e5e7eb';
                });
                // 只更新 URL，由 hashchange → route() → renderSearch() → doSearch() 统一驱动
                // 避免在 chip 点击里直接调 doSearch() 与 hashchange 触发的 renderSearch 并发请求，
                // 导致两次 API.search 互相竞争，第二个被中断时报 "Failed to fetch"。
                updateSearchUrl();
            });
        });

        // 默认浏览模式下的排序切换
        if (defaultSort) {
            defaultSort.addEventListener('change', () => {
                searchState.default_sort = defaultSort.value;
                searchState.offset = 0;
                updateDefaultSearchUrl();
                loadSearchDefault();
            });
        }

        toggleWeights();
    }

    function updateSearchUrl() {
        const isPaper = searchState.tab === 'papers';
        const p = { mode: searchState.mode, offset: searchState.offset, tab: searchState.tab };
        if (searchState.mode === 'hybrid') {
            p.fts_weight = searchState.fts_weight;
            p.vector_weight = searchState.vector_weight;
        }
        if (searchState.journal_tiers.length) {
            p.journal_tiers = searchState.journal_tiers.join(',');
        }
        // 字段行参数化（field1=..&q1=..）
        if (isPaper && searchState.field_rows && searchState.field_rows.length) {
            searchState.field_rows.forEach((row, i) => {
                const idx = i + 1;
                if (row.field) p[`field${idx}`] = row.field;
                if (row.value) p[`q${idx}`] = row.value;
            });
        } else if (searchState.q) {
            p.q = searchState.q;
        }
        const hasAnyQuery = isPaper
            ? (searchState.field_rows.some(r => r.value.trim())
                || searchState.journal_tiers.length
                || Object.keys(searchState.filters).length)
            : (searchState.q || Object.keys(searchState.filters).length);
        if (!hasAnyQuery) {
            p.sort = searchState.default_sort;
        }
        Object.assign(p, searchState.filters);
        window.location.hash = '#/search' + Utils.buildQueryString(p);
    }

    function updateDefaultSearchUrl() {
        const p = { sort: searchState.default_sort, offset: searchState.offset };
        if (searchState.journal_tiers.length) p.journal_tiers = searchState.journal_tiers.join(',');
        window.location.hash = '#/search' + Utils.buildQueryString(p);
    }

    // 默认浏览：拉取全部论文（与知识库 papers tab 一致）
    async function loadSearchDefault() {
        const resultArea = document.getElementById('search-result-area');
        const facetsPanel = document.getElementById('facets-panel');
        if (!resultArea) return;
        resultArea.innerHTML = '<div class="loading-text">加载论文列表...</div>';
        try {
            const params = {
                sort: searchState.default_sort,
                limit: searchState.limit,
                offset: searchState.offset
            };
            // 后端单值 journal_tier 暂不支持数组，所以多选时分别拉取再合并
            if (searchState.journal_tiers.length === 1) {
                params.journal_tier = searchState.journal_tiers[0];
            }
            const data = await API.getPapersList(params);
            let papers = data.papers || [];
            if (searchState.journal_tiers.length > 1) {
                papers = papers.filter(p => p.journal_tier && searchState.journal_tiers.includes(p.journal_tier));
            }
            if (!papers.length) {
                resultArea.innerHTML = '<div class="empty-state">暂无论文数据</div>';
                return;
            }
            const columns = [
                { key: 'title', label: '标题' },
                { key: 'year', label: '年份' },
                { key: 'journal', label: '期刊' },
                { key: 'journal_tier', label: '分级', render: (v) => {
                    const labels = { tier1: 'T1', tier2: 'T2', tier3: 'T3' };
                    const colors = { tier1: '#dbeafe', tier2: '#dcfce7', tier3: '#fef3c7' };
                    const textColors = { tier1: '#1e40af', tier2: '#166534', tier3: '#92400e' };
                    if (v && labels[v]) {
                        return `<span style="background:${colors[v]};color:${textColors[v]};padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;">${labels[v]}</span>`;
                    }
                    return '';
                }},
                { key: 'source', label: '来源' },
                { key: 'citation_count', label: '被引' },
                { key: 'keywords', label: '关键词', render: (v) => {
                    const arr = Array.isArray(v) ? v : (v ? [v] : []);
                    return arr.slice(0, 5).map(k => `<span class="tag">${Utils.escapeHtml(k)}</span>`).join('');
                }}
            ];
            const tierLabel = searchState.journal_tiers.length ? ' · 分级: ' + searchState.journal_tiers.join('+') : '';
            let html = `<div style="font-size:13px;color:var(--text-secondary);margin-bottom:12px;">默认浏览 · 共 ${papers.length} 篇${tierLabel}</div>`;
            html += Components.renderTable(papers, columns, {
                onRowClick: (row) => { window.location.hash = `#/paper/${row.id}`; }
            });
            html += `<div data-pagination>${Components.renderPagination(papers.length, searchState.limit, searchState.offset, (page) => {
                searchState.offset = (page - 1) * searchState.limit;
                updateDefaultSearchUrl();
                loadSearchDefault();
            })}</div>`;
            resultArea.innerHTML = html;
        } catch (err) {
            console.error('[search default] 加载失败:', err);
            resultArea.innerHTML = `<div class="empty-state">${I18n.t('common.load_failed')}: ${err.message}</div>`;
            showToast(I18n.t('toast.load_failed', {context: '默认列表', reason: err.message}), 'error');
        }
    }

    async function doSearch() {
        const resultArea = document.getElementById('search-result-area');
        const facetsPanel = document.getElementById('facets-panel');
        resultArea.innerHTML = '<div class="loading-text">搜索中...</div>';

        try {
            if (searchState.tab === 'papers') {
                await doSearchPapers(resultArea, facetsPanel);
            } else if (searchState.tab === 'data_points') {
                await doSearchDataPoints(resultArea);
            } else if (searchState.tab === 'knowledge') {
                await doSearchKnowledge(resultArea);
            } else if (searchState.tab === 'methods') {
                await doSearchMethods(resultArea);
            }
        } catch (err) {
            console.error('[search] 搜索失败:', err);
            resultArea.innerHTML = `<div class="empty-state">搜索失败: ${err.message}</div>`;
            showToast('搜索失败: ' + err.message, 'error');
        }
    }

    async function doSearchPapers(resultArea, facetsPanel) {
        let result;
        if (searchState.mode === 'vector') {
            result = await API.vectorSearch({ q: searchState.q, top_k: searchState.limit, offset: searchState.offset });
        } else if (searchState.mode === 'hybrid') {
            result = await API.hybridSearch({
                q: searchState.q,
                top_k: searchState.limit,
                offset: searchState.offset,
                fts_weight: searchState.fts_weight,
                vector_weight: searchState.vector_weight
            });
        } else {
            result = await API.search({
                q: searchState.q,
                mode: searchState.mode,
                limit: searchState.limit,
                offset: searchState.offset,
                ...searchState.filters,
                // 期刊分级多选筛选（后端会按多值过滤）
                journal_tiers: searchState.journal_tiers.length ? searchState.journal_tiers : undefined,
            });
        }
        searchState.result = result;
        renderSearchResults(resultArea, result);
        renderFacets(facetsPanel, result.aggregations || {});
        renderActiveFilters();
    }

    async function doSearchDataPoints(resultArea) {
        const params = {
            metric_name: searchState.q,
            limit: searchState.limit,
            offset: searchState.offset
        };
        const data = await API.getDataPointsList(params);
        const columns = [
            { key: 'metric_name', label: '指标' },
            { key: 'metric_value', label: '数值' },
            { key: 'unit', label: '单位' },
            { key: 'year', label: '年份' },
            { key: 'paper_title', label: '论文' },
            { key: 'context', label: '上下文' }
        ];
        let html = Components.renderTable(data.data_points, columns, {
            onRowClick: (row) => { window.location.hash = `#/paper/${row.paper_id}`; }
        });
        html += `<div data-pagination>${Components.renderPagination(data.total, searchState.limit, searchState.offset, (page) => {
            searchState.offset = (page - 1) * searchState.limit;
            updateSearchUrl();
            doSearch();
        })}</div>`;
        resultArea.innerHTML = html;
    }

    async function doSearchKnowledge(resultArea) {
        const params = {
            q: searchState.q,
            limit: searchState.limit,
            offset: searchState.offset
        };
        const data = await API.getKnowledgeList(params);
        const columns = [
            { key: 'paper_title', label: '论文' },
            { key: 'year', label: '年份' },
            { key: 'research_question', label: '研究问题', render: (v) => Utils.truncate(v, 120) },
            { key: 'core_answer', label: '核心回答', render: (v) => Utils.truncate(v, 120) },
            { key: 'key_claims_count', label: '主张数' },
            { key: 'has_reusable_inspiration', label: '可复用启发', render: (v) => v ? '有' : '' }
        ];
        let html = Components.renderTable(data.knowledge, columns, {
            onRowClick: (row) => { window.location.hash = `#/paper/${row.paper_id}`; }
        });
        html += `<div data-pagination>${Components.renderPagination(data.total, searchState.limit, searchState.offset, (page) => {
            searchState.offset = (page - 1) * searchState.limit;
            updateSearchUrl();
            doSearch();
        })}</div>`;
        resultArea.innerHTML = html;
    }

    async function doSearchMethods(resultArea) {
        const params = {
            q: searchState.q,
            limit: searchState.limit,
            offset: searchState.offset
        };
        const data = await API.getMethodsList(params);
        const columns = [
            { key: 'paper_title', label: '论文' },
            { key: 'year', label: '年份' },
            { key: 'methodology', label: '研究方法', render: (v) => Utils.truncate(v, 120) },
            { key: 'data_sources', label: '数据来源', render: (v) => Utils.truncate(typeof v === 'string' ? v : JSON.stringify(v), 80) },
            { key: 'models_algorithms', label: '模型/算法', render: (v) => Utils.truncate(typeof v === 'string' ? v : JSON.stringify(v), 80) }
        ];
        let html = Components.renderTable(data.methods, columns, {
            onRowClick: (row) => { window.location.hash = `#/paper/${row.paper_id}`; }
        });
        html += `<div data-pagination>${Components.renderPagination(data.total, searchState.limit, searchState.offset, (page) => {
            searchState.offset = (page - 1) * searchState.limit;
            updateSearchUrl();
            doSearch();
        })}</div>`;
        resultArea.innerHTML = html;
    }

    function renderScoredSearchResult(hit) {
        const title = hit.title || '无标题';
        const snippet = hit.abstract_snippet || hit.text || '';
        const authors = Utils.joinAuthors(hit.authors);
        const pid = hit.paper_id || hit.id;
        const attrs = pid ? `data-paper-id="${pid}"` : '';
        const score = hit.hybrid_score !== undefined ? hit.hybrid_score : (hit.similarity !== undefined ? hit.similarity : null);
        const scoreLabel = hit.hybrid_score !== undefined ? '混合得分' : '相似度';
        const scoreHtml = score !== null ? `<span class="result-score">${scoreLabel}: ${score.toFixed(3)}</span>` : '';
        return `<div class="result-card" ${attrs}>
            <div class="result-title">${title}</div>
            <div class="result-meta">
                <span>${hit.published_year || '未知年份'}</span>
                <span>${hit.journal || ''}</span>
                <span>${authors ? Utils.truncate(authors, 80) : ''}</span>
                ${scoreHtml}
            </div>
            <div class="result-snippet">${snippet}</div>
        </div>`;
    }

    function renderSearchResults(container, result) {
        if (result.error) {
            container.innerHTML = `<div class="empty-state">${result.error}</div>`;
            return;
        }
        const hits = result.hits || result.results || [];
        if (!hits.length) {
            container.innerHTML = '<div class="empty-state">未找到匹配结果</div>';
            return;
        }
        let html = `<div style="font-size:13px;color:var(--text-secondary);margin-bottom:12px;">共 ${result.total !== undefined ? result.total : hits.length} 条结果</div>`;
        const showScore = searchState.mode === 'vector' || searchState.mode === 'hybrid';
        hits.forEach((hit, i) => {
            if (showScore) {
                html += renderScoredSearchResult(hit);
            } else {
                html += Components.renderSearchResult(hit, i);
            }
        });
        html += `<div data-pagination>${Components.renderPagination(
            result.total || hits.length,
            searchState.limit,
            searchState.offset,
            (page) => {
                searchState.offset = (page - 1) * searchState.limit;
                updateSearchUrl();
                doSearch();
            }
        )}</div>`;
        container.innerHTML = html;

        // 绑定点击（dataset 将 data-paper-id 映射为 paperId）
        container.querySelectorAll('.result-card[data-paper-id]').forEach(card => {
            const pid = card.dataset.paperId;
            if (!pid || pid === 'undefined') return;
            card.style.cursor = 'pointer';
            card.addEventListener('click', () => {
                window.location.hash = `#/paper/${pid}`;
            });
        });
    }

    function renderFacets(container, aggregations) {
        container.innerHTML = '<h3 class="card-title">聚合面板</h3>' +
            Components.renderFacets(aggregations, searchState.filters, (facet, key) => {
                if (searchState.filters[facet] === key) {
                    delete searchState.filters[facet];
                } else {
                    searchState.filters[facet] = key;
                }
                searchState.offset = 0;
                updateSearchUrl();
                doSearch();
            });
    }

    function renderActiveFilters() {
        const el = document.getElementById('active-filters');
        const names = { year_from: '起始年份', year_to: '截止年份', year: '年份', journal: '期刊', author: '作者', language: '语言', source: '来源', doi: 'DOI' };
        const items = Object.entries(searchState.filters).map(([k, v]) => `<span style="display:inline-flex;align-items:center;gap:4px;background:#e0e7ff;color:#3730a3;padding:4px 10px;border-radius:12px;font-size:12px;margin-right:6px;">
            ${names[k] || k}: ${Utils.escapeHtml(v)} <button style="background:none;border:none;cursor:pointer;padding:0;font-weight:bold;" data-filter="${k}">&times;</button>
        </span>`).join('');
        el.innerHTML = items ? '<div>当前筛选: ' + items + '</div>' : '';
        el.querySelectorAll('button[data-filter]').forEach(btn => {
            btn.addEventListener('click', () => {
                delete searchState.filters[btn.dataset.filter];
                searchState.offset = 0;
                updateSearchUrl();
                doSearch();
            });
        });
    }

    // ------------------ Paper Detail ------------------
    async function renderPaperDetail(id) {
        content.innerHTML = '<div class="loading-text">加载论文详情...</div>';
        try {
            const loadErrors = [];
            const [paper, similar, knowledge, methods, dataPoints, citations, paperAuthors] = await Promise.all([
                API.getPaper(id),
                API.getPaperSimilar(id, 5).catch(err => { loadErrors.push('相似论文: ' + err.message); return { results: [] }; }),
                API.getPaperKnowledge(id).catch(err => { loadErrors.push('知识卡片: ' + err.message); return { knowledge: null }; }),
                API.getPaperMethods(id).catch(err => { loadErrors.push('方法流程: ' + err.message); return { methods: null }; }),
                API.getPaperDataPoints(id).catch(err => { loadErrors.push('数据点: ' + err.message); return { data_points: [] }; }),
                API.getPaperCitations(id).catch(err => { loadErrors.push('引用网络: ' + err.message); return { citations: [] }; }),
                API.getPaperAuthors(id).catch(err => { loadErrors.push('作者信息: ' + err.message); return { authors: [] }; })
            ]);
            if (loadErrors.length) {
                console.error('[paper detail] 部分附加数据加载失败:', loadErrors);
                showToast(I18n.t('toast.additional_data_load_failed'), 'warning');
            }

            const tabs = [
                { id: 'abstract', label: I18n.t('paper.tab.abstract') },
                { id: 'sections', label: I18n.t('paper.tab.sections') },
                { id: 'figures', label: I18n.t('paper.tab.figures') },
                { id: 'citations', label: I18n.t('paper.tab.citations') },
                { id: 'knowledge', label: I18n.t('paper.tab.knowledge') },
                { id: 'methods', label: I18n.t('paper.tab.methods') },
                { id: 'data', label: I18n.t('paper.tab.data') }
            ];

            let html = '<div class="paper-detail">';
            html += '<div class="paper-main">';
            html += `<div class="paper-header">
                <h2>${Utils.escapeHtml(paper.title || I18n.t('paper.meta.unknown_paper', {id: id}))}</h2>
                <div class="meta">
                    <span>${I18n.t('paper.meta.doi')}: ${paper.doi ? `<a href="https://doi.org/${paper.doi}" target="_blank">${paper.doi}</a>` : I18n.t('paper.meta.none')}</span>
                    <span>${I18n.t('paper.meta.year')}: ${paper.published_date || paper.published_year || I18n.t('paper.meta.unknown')}</span>
                    <span>${I18n.t('paper.meta.journal')}: ${Utils.escapeHtml(paper.journal || I18n.t('paper.meta.unknown'))}</span>
                    <span>${I18n.t('paper.meta.source')}: ${paper.source || ''}</span>
                    <span>${I18n.t('paper.meta.cited_by')}: ${paper.citation_count !== undefined ? paper.citation_count : I18n.t('paper.meta.unknown')}</span>
                </div>
                <div class="meta" style="margin-top:6px;">
                    <span>${I18n.t('paper.meta.author')}: ${Utils.escapeHtml(Utils.joinAuthors(paper.author) || I18n.t('paper.meta.unknown'))}</span>
                </div>
                <div class="meta" style="margin-top:6px;">
                    <span>${I18n.t('paper.meta.keywords')}: ${Utils.escapeHtml(Utils.joinKeywords(paper.keywords) || I18n.t('paper.meta.none'))}</span>
                </div>
            </div>`;

            html += Components.renderTabs(tabs, 'abstract', (tabId) => switchPaperTab(tabId, paper, knowledge, methods, dataPoints, citations));
            html += '<div id="paper-tab-content"></div>';
            html += '</div>'; // paper-main

            html += '<div class="paper-sidebar">';
            html += '<div class="card"><h3 class="card-title">' + I18n.t('paper.meta.similar_papers') + '</h3>' + Components.renderSimilarPapers(similar) + '</div>';

            // 学者 / 机构 / 引用网络联动
            const authors = paperAuthors.authors || [];
            const institutions = new Set();
            authors.forEach(a => (a.institutions || []).forEach(i => { if (i) institutions.add(i); }));
            const firstAuthor = authors[0];
            html += '<div class="card"><h3 class="card-title">知识网络联动</h3>';
            html += `<div style="margin-bottom:10px;"><a class="btn btn-secondary" href="#/network?focus_paper=${id}">在引用网络中查看</a></div>`;
            if (firstAuthor) {
                html += `<div style="margin-bottom:10px;"><a class="btn btn-secondary" href="#/author/${firstAuthor.id}">查看第一作者画像</a></div>`;
            }
            if (institutions.size) {
                html += '<div style="margin-bottom:6px;font-size:13px;color:var(--text-secondary);">相关机构</div>';
                html += '<div style="display:flex;flex-wrap:wrap;gap:6px;">';
                Array.from(institutions).slice(0, 8).forEach(inst => {
                    html += `<a class="tag" href="#/institutions?affiliation=${encodeURIComponent(inst)}">${Utils.escapeHtml(inst)}</a>`;
                });
                html += '</div>';
            }
            if (authors.length) {
                html += '<div style="margin:10px 0 6px;font-size:13px;color:var(--text-secondary);">核心作者</div>';
                html += '<div style="display:flex;flex-wrap:wrap;gap:6px;">';
                authors.slice(0, 10).forEach(a => {
                    html += `<a class="tag" href="#/author/${a.id}">${Utils.escapeHtml(a.full_name)}</a>`;
                });
                html += '</div>';
            }
            html += '</div>'; // card

            html += '</div>'; // paper-sidebar
            html += '</div>'; // paper-detail

            content.innerHTML = html;
            switchPaperTab('abstract', paper, knowledge, methods, dataPoints, citations);
            Components.drawSimilarChart(similar);

            // 绑定相似论文点击
            content.querySelectorAll('[data-paper-id]').forEach(el => {
                const pid = el.dataset.paperId;
                if (!pid || pid === 'undefined') return;
                el.addEventListener('click', () => {
                    window.location.hash = `#/paper/${pid}`;
                });
            });
        } catch (err) {
            console.error('[paper detail] 加载失败:', err);
            content.innerHTML = `<div class="empty-state">${I18n.t('common.load_failed')}: ${err.message}</div>`;
            showToast(I18n.t('toast.load_failed', {context: '论文详情', reason: err.message}), 'error');
        }
    }

    function switchPaperTab(tabId, paper, knowledge, methods, dataPoints, citations) {
        const container = document.getElementById('paper-tab-content');
        document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tabId));
        switch (tabId) {
            case 'abstract':
                container.innerHTML = `<div class="card"><p style="line-height:1.7;">${Utils.escapeHtml(paper.abstract || '无摘要')}</p></div>`;
                break;
            case 'sections':
                container.innerHTML = Components.renderSections(paper.sections);
                Components.bindSectionToggles();
                break;
            case 'figures':
                container.innerHTML = Components.renderFigures(paper.figures);
                break;
            case 'citations':
                container.innerHTML = Components.renderCitations(citations.citations);
                break;
            case 'knowledge':
                container.innerHTML = Components.renderKnowledge(knowledge.knowledge);
                Components.bindAnchorPills();
                break;
            case 'methods':
                container.innerHTML = Components.renderMethods(methods.methods);
                break;
            case 'data':
                container.innerHTML = Components.renderDataPoints(dataPoints);
                break;
        }
    }

    // ------------------ Compare ------------------
    async function renderCompare() {
        const hash = window.location.hash || '';
        const qs = hash.split('?')[1] || '';
        const params = parseQuery(qs);
        const presetMetric = params.metric || '';

        content.innerHTML = `<h2 style="margin-top:0;">跨论文指标对比</h2>
            <div class="card">
                <div class="compare-input">
                    <input type="text" id="compare-metric" placeholder="输入指标名，如 yield / efficiency / reduction" value="${Utils.escapeHtml(presetMetric)}">
                    <button class="btn btn-primary" id="compare-btn">对比</button>
                </div>
                <div id="compare-result"><div class="loading-text">${I18n.t('common.loading')}</div></div>
            </div>`;

        const input = document.getElementById('compare-metric');
        const btn = document.getElementById('compare-btn');
        const result = document.getElementById('compare-result');

        const doCompare = async (metric) => {
            const m = (metric !== undefined ? metric : input.value).trim();
            if (!m) {
                await loadCompareDefault();
                return;
            }
            if (input.value.trim() !== m) input.value = m;
            result.innerHTML = '<div class="loading-text">' + I18n.t('common.loading') + '</div>';
            try {
                const data = await API.compareMetric(m, 30);
                renderCompareResult(result, data);
            } catch (err) {
                console.error('[compare] 对比失败:', err);
                result.innerHTML = `<div class="empty-state">对比失败: ${err.message}</div>`;
                showToast('数据对比失败: ' + err.message, 'error');
            }
        };
        btn.addEventListener('click', () => doCompare());
        input.addEventListener('keydown', e => { if (e.key === 'Enter') doCompare(); });

        if (presetMetric) {
            await doCompare(presetMetric);
        } else {
            await loadCompareDefault();
        }
    }

    // 默认浏览：展示可用指标列表
    async function loadCompareDefault() {
        const result = document.getElementById('compare-result');
        if (!result) return;
        result.innerHTML = '<div class="loading-text">加载指标列表...</div>';
        try {
            // 用较大的 limit 拉取一批数据点，前端按 metric_name 聚合
            const data = await API.getDataPointsList({ limit: 500, offset: 0 });
            const points = data.data_points || [];
            if (!points.length) {
                result.innerHTML = '<div class="empty-state">暂无数据点，请先采集并提炼论文</div>';
                return;
            }
            // 聚合：每个指标名 → { count, sample, units: Set, year_min, year_max, papers: Set }
            const map = new Map();
            points.forEach(p => {
                if (!p.metric_name) return;
                const key = p.metric_name;
                if (!map.has(key)) {
                    map.set(key, {
                        metric_name: key,
                        count: 0,
                        sample: p.metric_value !== null && p.metric_value !== undefined ? p.metric_value : null,
                        unit: p.unit || '',
                        year_min: p.year || null,
                        year_max: p.year || null,
                        paper_count: 0,
                        papers: new Set()
                    });
                }
                const it = map.get(key);
                it.count += 1;
                if (p.paper_id !== undefined && p.paper_id !== null) it.papers.add(p.paper_id);
                if (p.year) {
                    if (it.year_min === null || p.year < it.year_min) it.year_min = p.year;
                    if (it.year_max === null || p.year > it.year_max) it.year_max = p.year;
                }
            });
            const items = Array.from(map.values()).map(it => ({
                metric_name: it.metric_name,
                count: it.count,
                sample: it.sample,
                unit: it.unit,
                year_min: it.year_min,
                year_max: it.year_max,
                paper_count: it.papers.size
            })).sort((a, b) => b.count - a.count);

            const renderCard = (it) => {
                const yearRange = it.year_min && it.year_max
                    ? (it.year_min === it.year_max ? `${it.year_min}` : `${it.year_min}-${it.year_max}`)
                    : '';
                const sample = it.sample !== null && it.sample !== undefined
                    ? `${Utils.escapeHtml(String(it.sample))}${it.unit ? ' ' + Utils.escapeHtml(it.unit) : ''}`
                    : '';
                return `<div class="metric-card" data-metric="${Utils.escapeHtml(it.metric_name)}" style="
                    border: 1px solid var(--border);
                    border-radius: var(--radius);
                    padding: 12px 14px;
                    background: var(--surface);
                    cursor: pointer;
                    transition: transform var(--transition), box-shadow var(--transition), border-color var(--transition);
                " onmouseover="this.style.borderColor='var(--primary)';this.style.transform='translateY(-1px)';this.style.boxShadow='var(--shadow)';"
                   onmouseout="this.style.borderColor='var(--border)';this.style.transform='';this.style.boxShadow='';">
                    <div style="font-weight:600;color:var(--text);margin-bottom:4px;">${Utils.escapeHtml(it.metric_name)}</div>
                    <div style="font-size:12px;color:var(--text-secondary);display:flex;flex-wrap:wrap;gap:8px;">
                        <span>📊 ${it.count} 个数据点</span>
                        <span>📄 ${it.paper_count} 篇论文</span>
                        ${yearRange ? `<span>📅 ${yearRange}</span>` : ''}
                        ${sample ? `<span style="color:var(--primary);">样本: ${sample}</span>` : ''}
                    </div>
                </div>`;
            };

            let html = `<div style="font-size:13px;color:var(--text-secondary);margin-bottom:12px;">默认浏览 · 共 ${items.length} 个不同指标（基于最近 500 条数据点）</div>`;
            html += `<div class="metric-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;">`;
            html += items.map(renderCard).join('');
            html += `</div>`;
            result.innerHTML = html;

            // 点击指标卡片：填入输入框并触发对比
            result.querySelectorAll('.metric-card').forEach(card => {
                card.addEventListener('click', () => {
                    const m = card.dataset.metric;
                    const inputEl = document.getElementById('compare-metric');
                    if (inputEl) inputEl.value = m;
                    // 跳转 URL 以便刷新保持
                    window.location.hash = '#/compare?metric=' + encodeURIComponent(m);
                });
            });
        } catch (err) {
            console.error('[compare default] 加载失败:', err);
            result.innerHTML = `<div class="empty-state">${I18n.t('common.load_failed')}: ${err.message}</div>`;
            showToast(I18n.t('toast.load_failed', {context: '指标列表', reason: err.message}), 'error');
        }
    }

    function renderCompareResult(container, data) {
        if (!data.results || !data.results.length) {
            container.innerHTML = '<div class="empty-state">未找到该指标的数据</div>';
            return;
        }
        const chartData = data.results
            .filter(r => r.metric_value !== null && !isNaN(r.metric_value))
            .map(r => ({
                label: Utils.truncate(r.title || `论文 ${r.paper_id}`, 20),
                value: parseFloat(r.metric_value)
            }));

        let html = '<div id="compare-chart" class="chart-container" style="margin-bottom:16px;"></div>';
        html += '<table class="data-table"><thead><tr><th>论文</th><th>指标</th><th>数值</th><th>单位</th><th>上下文</th></tr></thead><tbody>';
        data.results.forEach(r => {
            html += `<tr data-paper-id="${r.paper_id}" style="cursor:pointer;">
                <td>${Utils.escapeHtml(Utils.truncate(r.title || `论文 ${r.paper_id}`, 40))}</td>
                <td>${Utils.escapeHtml(r.metric_name || '')}</td>
                <td>${r.metric_value !== null ? r.metric_value : ''}</td>
                <td>${Utils.escapeHtml(r.unit || '')}</td>
                <td>${Utils.escapeHtml(Utils.truncate(r.context || '', 60))}</td>
            </tr>`;
        });
        html += '</tbody></table>';
        container.innerHTML = html;

        setTimeout(() => {
            const el = document.getElementById('compare-chart');
            if (el && chartData.length) Charts.barChart(el, chartData, { height: 320 });
        }, 0);

        container.querySelectorAll('tr[data-paper-id]').forEach(tr => {
            const pid = tr.dataset.paperId;
            if (!pid || pid === 'undefined') return;
            tr.addEventListener('click', () => {
                window.location.hash = `#/paper/${pid}`;
            });
        });
    }

    // ------------------ Network / Graph ------------------
    async function renderNetwork(queryString) {
        const params = parseQuery(queryString);
        const focusPaperId = params.focus_paper ? parseInt(params.focus_paper, 10) : null;
        const focusAuthor = params.focus_author ? decodeURIComponent(params.focus_author) : null;

        content.innerHTML = `<h2 style="margin-top:0;">引用网络 / 关系图谱</h2>
            <div class="graph-layout">
                <div id="graph-sidebar"></div>
                <div id="graph-chart" class="graph-container"></div>
            </div>`;

        const sidebarEl = document.getElementById('graph-sidebar');
        const chartEl = document.getElementById('graph-chart');
        chartEl.innerHTML = '<div class="loading-text">构建图谱...</div>';

        let state = {
            year_from: '', year_to: '', min_citations: 0, max_nodes: (focusPaperId || focusAuthor) ? 120 : 80, show_labels: true,
            entity_types: { paper: true, author: true, keyword: true, data_point: true },
            citation_only: false,
            node_search: ''
        };

        // 缓存上一次图谱数据，用于前端节点定位
        let lastGraphData = { nodes: [], edges: [] };
        let lastDiagnostics = { issue_count: 0, issues: [] };

        const buildGraphData = async () => {
            const types = Object.entries(state.entity_types)
                .filter(([_, v]) => v).map(([k]) => k).join(',');
            const params = { entity_types: types, min_citations: state.min_citations, max_nodes: state.max_nodes };
            if (state.year_from) params.year_from = state.year_from;
            if (state.year_to) params.year_to = state.year_to;
            const data = await API.getGraph(params);

            let nodes = data.nodes || [];
            let edges = data.edges || [];

            // 按类型过滤：后端始终返回论文节点作为连接基础，前端按用户选择严格隐藏未勾选类型
            const activeTypes = new Set(Object.entries(state.entity_types)
                .filter(([_, v]) => v).map(([k]) => k));
            if (activeTypes.size > 0) {
                nodes = nodes.filter(n => activeTypes.has(n.type));
                const nodeIdSet = new Set(nodes.map(n => n.id));
                edges = edges.filter(e => nodeIdSet.has(e.source) && nodeIdSet.has(e.target));
            }

            // 仅论文引用模式：只保留论文节点与引用边
            if (state.citation_only) {
                nodes = nodes.filter(n => n.type === 'paper');
                const nodeIdSet = new Set(nodes.map(n => n.id));
                edges = edges.filter(e => e.type === 'cites' && nodeIdSet.has(e.source) && nodeIdSet.has(e.target));
            }

            // focus_paper / focus_author 模式：聚焦目标论文或其作者论文的 1-hop 子图
            if (focusPaperId || focusAuthor) {
                let targetIds = new Set();
                if (focusPaperId) targetIds.add(`p${focusPaperId}`);
                if (focusAuthor) {
                    try {
                        const searchRes = await API.search({ q: '', author: focusAuthor, mode: 'keyword', limit: 50 });
                        (searchRes.results || []).forEach(r => {
                            if (r.id) targetIds.add(`p${r.id}`);
                        });
                    } catch (e) {
                        console.error('[network] 按作者搜索失败:', e);
                    }
                }
                const neighborIds = new Set(targetIds);
                edges.forEach(e => {
                    if (targetIds.has(e.source)) neighborIds.add(e.target);
                    if (targetIds.has(e.target)) neighborIds.add(e.source);
                });
                nodes = nodes.filter(n => neighborIds.has(n.id));
                const nodeIdSet = new Set(nodes.map(n => n.id));
                edges = edges.filter(e => nodeIdSet.has(e.source) && nodeIdSet.has(e.target));
            }

            return { nodes, edges };
        };

        const loadGraph = async (opts = {}) => {
            chartEl.innerHTML = '<div class="loading-text">构建图谱...</div>';
            try {
                const { nodes, edges } = await buildGraphData();
                lastGraphData = { nodes, edges };

                // 并行获取图谱健康诊断
                const diagParams = {
                    entity_types: Object.entries(state.entity_types)
                        .filter(([_, v]) => v).map(([k]) => k).join(','),
                    min_citations: state.min_citations,
                    max_nodes: state.max_nodes,
                    ...(state.year_from ? { year_from: state.year_from } : {}),
                    ...(state.year_to ? { year_to: state.year_to } : {})
                };
                const diagnostics = await API.getGraphDiagnostics(diagParams);
                lastDiagnostics = diagnostics;

                // 收集问题节点 ID（孤立节点、时间异常等）
                const problemNodeIds = new Set();
                (diagnostics.issues || []).forEach(issue => {
                    if (issue.node_id) problemNodeIds.add(issue.node_id);
                    if (issue.node_ids) issue.node_ids.forEach(id => problemNodeIds.add(id));
                });

                Charts.forceGraph(chartEl, nodes, edges, {
                    show_labels: state.show_labels,
                    relayout: opts.relayout,
                    citation_only: state.citation_only,
                    focusHopDepth: opts.focusHopDepth || 1,
                    problemNodeIds,
                    onNodeClick: (n) => {
                        if (n.type === 'paper' && n.paper_id) {
                            window.location.hash = `#/paper/${n.paper_id}`;
                        } else if (n.type === 'author' && n.author_id) {
                            window.location.hash = `#/author/${n.author_id}`;
                        }
                    }
                });

                // 更新侧边栏诊断徽章
                renderDiagnosticsBadge();
            } catch (err) {
                console.error('[network] 图谱加载失败:', err);
                chartEl.innerHTML = `<div class="empty-state">${I18n.t('toast.graph_load_failed')}: ${err.message}</div>`;
                showToast(I18n.t('toast.network_load_failed') + ': ' + err.message, 'error');
            }
        };

        const renderDiagnosticsBadge = () => {
            const el = document.getElementById('graph-diag-badge');
            if (!el) return;
            const count = lastDiagnostics.issue_count || 0;
            if (count === 0) {
                el.innerHTML = '<span style="color:#16a34a;">✓ 图谱健康</span>';
                return;
            }
            const stats = lastDiagnostics.issue_stats || {};
            const tips = Object.entries(stats).map(([k, v]) => {
                const names = {
                    isolated_node: '孤立节点', dangling_edge: '悬挂边',
                    time_anomaly: '时间异常', duplicate_institution: '重复机构'
                };
                return `${names[k] || k}: ${v}`;
            }).join('、');
            el.innerHTML = `<span style="color:#dc2626;cursor:pointer;font-weight:600;">⚠ ${count} 个问题</span>
                <div class="hint" style="margin-top:4px;">${tips}；点击定位第一个问题节点</div>`;
            el.onclick = () => {
                const first = (lastDiagnostics.issues || []).find(i => i.node_id || (i.node_ids || []).length);
                if (first) {
                    const nid = first.node_id || (first.node_ids || [])[0];
                    chartEl.dispatchEvent(new CustomEvent('graph:focus', { detail: { nodeId: nid, hopDepth: 1 } }));
                }
            };
        };

        const locateNode = (keyword) => {
            if (!keyword || !lastGraphData.nodes.length) return;
            const lower = keyword.toLowerCase();
            const target = lastGraphData.nodes.find(n =>
                (n.label || '').toLowerCase().includes(lower) ||
                (n.doi || '').toLowerCase().includes(lower)
            );
            if (!target) {
                showToast('未找到匹配节点', 'warning');
                return;
            }
            // 触发图表内部聚焦：通过自定义事件让 forceGraph 暴露的 focus API 处理
            chartEl.dispatchEvent(new CustomEvent('graph:focus', { detail: { nodeId: target.id, hopDepth: 2 } }));
            showToast(`已定位: ${Utils.truncate(target.label, 30)}`, 'success');
        };

        sidebarEl.innerHTML = Components.renderGraphSidebar(state, (newState) => {
            const { action, ...rest } = newState;
            state = { ...state, ...rest };
            if (action === 'locate') {
                locateNode(state.node_search);
            } else {
                loadGraph({ relayout: true });
            }
        });

        await loadGraph();
    }

    // ------------------ Vector DB ------------------
    async function renderVectorDB() {
        content.innerHTML = `<h2 style="margin-top:0;">向量数据库</h2>
            <div class="card-grid" id="vec-stats"></div>
            <div class="card">
                <h3 class="card-title">向量语义检索</h3>
                <div class="vector-search-box">
                    <input type="text" id="vec-q" placeholder="输入查询文本，如 livestock grazing" style="flex:1;padding:10px 14px;border:1px solid var(--border);border-radius:var(--radius);font-size:15px;">
                    <select id="vec-mode" style="padding:10px 12px;border:1px solid var(--border);border-radius:var(--radius);font-size:14px;">
                        <option value="vector">纯向量</option>
                        <option value="hybrid">混合检索</option>
                    </select>
                    <select id="vec-chunk-type" style="padding:10px 12px;border:1px solid var(--border);border-radius:var(--radius);font-size:14px;">
                        <option value="">全部类型</option>
                        <option value="section">章节</option>
                        <option value="claim">主张</option>
                        <option value="method">方法</option>
                        <option value="data_point">数据点</option>
                        <option value="abstract">摘要</option>
                    </select>
                    <input type="number" id="vec-topk" value="5" min="1" max="50" style="width:80px;padding:10px 12px;border:1px solid var(--border);border-radius:var(--radius);font-size:14px;">
                    <button class="btn btn-primary" id="vec-search">检索</button>
                </div>
                <div id="vec-results" style="margin-top:16px;"></div>
            </div>
            <div class="card">
                <h3 class="card-title">向量 Chunk 抽样</h3>
                <div id="vec-samples"></div>
            </div>`;

        const statsEl = document.getElementById('vec-stats');
        const resultsEl = document.getElementById('vec-results');
        const samplesEl = document.getElementById('vec-samples');

        try {
            const stats = await API.vectorStats({ top_k: 5 });
            statsEl.innerHTML =
                Components.statCard('向量总数', stats.total_embeddings || 0) +
                Components.statCard('已向量化论文', stats.papers_with_embeddings || 0) +
                Components.statCard('向量维度', stats.dimension || 0) +
                Components.statCard('sqlite-vec', stats.sqlite_vec_available ? '可用' : 'NumPy回退');

            if (stats.by_chunk_type && stats.by_chunk_type.length) {
                statsEl.innerHTML += `<div class="card"><h3 class="card-title">Chunk 类型分布</h3><div id="vec-type-chart"></div></div>`;
                setTimeout(() => {
                    const chartEl = document.getElementById('vec-type-chart');
                    if (chartEl && Charts.pieChart) {
                        Charts.pieChart(chartEl, stats.by_chunk_type.map(t => ({ label: t.chunk_type, value: t.c })), { height: 220 });
                    } else if (chartEl) {
                        chartEl.innerHTML = stats.by_chunk_type.map(t => `<span class="tag">${t.chunk_type}: ${t.c}</span>`).join('');
                    }
                }, 0);
            }

            if (stats.samples && stats.samples.length) {
                samplesEl.innerHTML = Components.renderTable(stats.samples, [
                    { key: 'paper_id', label: '论文ID' },
                    { key: 'chunk_type', label: '类型' },
                    { key: 'chunk_id', label: 'ChunkID' },
                    { key: 'text', label: '文本', render: (v) => Utils.truncate(v, 160) }
                ], { onRowClick: (row) => { window.location.hash = `#/paper/${row.paper_id}`; } });
            } else {
                samplesEl.innerHTML = `<div class="empty-state">${I18n.t('common.no_results')}</div>`;
            }
        } catch (err) {
            console.error('[vectordb] 加载失败:', err);
            statsEl.innerHTML = `<div class="empty-state">${I18n.t('toast.load_failed', {context: '向量统计', reason: err.message})}</div>`;
            samplesEl.innerHTML = `<div class="empty-state">${I18n.t('common.no_data')}</div>`;
            showToast(I18n.t('toast.load_failed', {context: '向量库', reason: err.message}), 'error');
        }

        const doSearch = async () => {
            const q = document.getElementById('vec-q').value.trim();
            if (!q) return;
            const mode = document.getElementById('vec-mode').value;
            const top_k = parseInt(document.getElementById('vec-topk').value, 10) || 5;
            const chunk_type = document.getElementById('vec-chunk-type').value || undefined;
            resultsEl.innerHTML = '<div class="loading-text">检索中...</div>';
            try {
                const params = { q, top_k, chunk_type };
                const data = mode === 'hybrid' ? await API.hybridSearch(params) : await API.vectorSearch(params);
                const results = data.results || [];
                if (!results.length) {
                    resultsEl.innerHTML = '<div class="empty-state">未找到相似向量</div>';
                    return;
                }
                let html = `<div style="font-size:13px;color:var(--text-secondary);margin-bottom:12px;">返回 ${results.length} 条结果</div>`;
                if (mode === 'hybrid') {
                    // hybrid 返回论文级结果
                    html += Components.renderTable(results.map((r, i) => ({ ...r, rank: i + 1 })), [
                        { key: 'rank', label: '排名' },
                        { key: 'id', label: '论文ID' },
                        { key: 'title', label: '标题', render: (v) => Utils.truncate(v, 50) },
                        { key: 'hybrid_score', label: '混合得分', render: (v) => v !== undefined ? v.toFixed(3) : '' },
                        { key: 'abstract', label: '摘要', render: (v) => Utils.truncate(v, 120) }
                    ], { onRowClick: (row) => { window.location.hash = `#/paper/${row.id || row.paper_id}`; } });
                } else {
                    // vector 返回 chunk 级结果
                    html += Components.renderTable(results.map((r, i) => ({ ...r, rank: i + 1 })), [
                        { key: 'rank', label: '排名' },
                        { key: 'paper_id', label: '论文ID' },
                        { key: 'chunk_type', label: '类型' },
                        { key: 'similarity', label: '相似度', render: (v) => v !== undefined ? v.toFixed(3) : '' },
                        { key: 'text', label: '文本', render: (v) => Utils.truncate(v, 140) }
                    ], { onRowClick: (row) => { window.location.hash = `#/paper/${row.paper_id}`; } });
                }
                resultsEl.innerHTML = html;
            } catch (err) {
                console.error('[vectordb] 检索失败:', err);
                resultsEl.innerHTML = `<div class="empty-state">检索失败: ${err.message}</div>`;
                showToast('向量检索失败: ' + err.message, 'error');
            }
        };
        document.getElementById('vec-search').addEventListener('click', doSearch);
        document.getElementById('vec-q').addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });
    }

    // ------------------ Authors / Institutions ------------------
    let authorsState = { q: '', affiliation: '', offset: 0, limit: 25 };

    async function renderAuthors(queryString) {
        const params = parseQuery(queryString);
        authorsState.q = params.q || '';
        authorsState.affiliation = params.affiliation || '';
        authorsState.offset = parseInt(params.offset || '0', 10);

        content.innerHTML = `<h2 style="margin-top:0;">学者画像</h2>
            <div class="card">
                <div class="author-search">
                    <input type="text" id="author-q" placeholder="姓名关键词" value="${Utils.escapeHtml(authorsState.q)}">
                    <input type="text" id="author-affiliation" placeholder="机构关键词" value="${Utils.escapeHtml(authorsState.affiliation)}">
                    <button class="btn btn-primary" id="author-search-btn">搜索</button>
                </div>
                <div id="authors-result"></div>
            </div>`;

        const doSearch = async () => {
            authorsState.q = document.getElementById('author-q').value.trim();
            authorsState.affiliation = document.getElementById('author-affiliation').value.trim();
            authorsState.offset = 0;
            updateAuthorsUrl();
            await loadAuthors();
        };
        document.getElementById('author-search-btn').addEventListener('click', doSearch);
        document.getElementById('author-q').addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });
        document.getElementById('author-affiliation').addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });

        await loadAuthors();
    }

    function updateAuthorsUrl() {
        const p = { q: authorsState.q, affiliation: authorsState.affiliation, offset: authorsState.offset, limit: authorsState.limit };
        window.location.hash = '#/authors' + Utils.buildQueryString(p);
    }

    async function loadAuthors() {
        const container = document.getElementById('authors-result');
        container.innerHTML = '<div class="loading-text">加载学者列表...</div>';
        try {
            const data = await API.listAuthors({
                q: authorsState.q,
                affiliation: authorsState.affiliation,
                limit: authorsState.limit,
                offset: authorsState.offset
            });
            const authors = data.authors || [];
            if (!authors.length) {
                container.innerHTML = '<div class="empty-state">未找到学者</div>';
                return;
            }

            // 按 full_name 分组，识别同名重复
            const nameMap = new Map();
            authors.forEach(a => {
                const key = (a.full_name || '').trim().toLowerCase();
                if (!nameMap.has(key)) nameMap.set(key, []);
                nameMap.get(key).push(a);
            });
            const groups = Array.from(nameMap.values());

            let html = '';
            // 顶部统计
            const dupGroups = groups.filter(g => g.length > 1);
            const dupTotal = dupGroups.reduce((s, g) => s + g.length, 0);
            if (dupGroups.length > 0) {
                html += `<div class="card" style="background:#fef3c7;border-color:#f59e0b;margin-bottom:16px;">
                    <div style="display:flex;align-items:center;gap:8px;">
                        <span style="font-size:18px;">&#9888;</span>
                        <span>检测到 <strong>${dupGroups.length}</strong> 组同名学者（共 <strong>${dupTotal}</strong> 条重复记录），可点击"合并"按钮进行消歧</span>
                    </div>
                </div>`;
            }

            // 渲染分组表格
            html += '<table class="data-table"><thead><tr>';
            html += '<th style="width:20%">姓名</th><th style="width:25%">机构</th><th style="width:10%">论文数</th><th style="width:10%">h-index</th><th style="width:15%">ORCID</th><th style="width:20%">操作</th>';
            html += '</tr></thead><tbody>';

            groups.forEach(group => {
                const primary = group[0]; // 取第一条作为主记录
                const isDuplicate = group.length > 1;

                // 合并所有机构
                const allInstitutions = new Set();
                group.forEach(a => (a.institutions || []).forEach(inst => allInstitutions.add(inst)));
                const instStr = Array.from(allInstitutions).slice(0, 3).join('; ');

                // 论文数取最大值
                const maxPapers = Math.max(...group.map(a => a.paper_count || a.total_publications || 0));
                const totalPapers = group.reduce((s, a) => s + (a.paper_count || a.total_publications || 0), 0);

                html += '<tr' + (isDuplicate ? ' style="background:#fffbeb;"' : '') + '>';
                html += `<td>`;
                html += `<a href="#/author/${primary.id}" style="color:#3b82f6;text-decoration:none;font-weight:600;">${Utils.escapeHtml(primary.full_name)}</a>`;
                if (isDuplicate) {
                    html += ` <span class="tag" style="background:#fef3c7;color:#b45309;font-size:11px;" title="数据库中有 ${group.length} 条同名记录">${group.length} 条重复</span>`;
                }
                html += `</td>`;
                html += `<td>${Utils.escapeHtml(instStr) || '-'}</td>`;
                html += `<td>${isDuplicate ? `${totalPapers} (分${group.length}条)` : maxPapers}</td>`;
                html += `<td>${primary.h_index || '—'}</td>`;
                html += `<td>${primary.orcid ? `<a href="https://orcid.org/${primary.orcid}" target="_blank" style="font-size:12px;">${primary.orcid}</a>` : '-'}</td>`;
                html += `<td>`;
                if (isDuplicate) {
                    const allIds = group.map(a => a.id);
                    html += `<button class="btn btn-primary btn-sm" onclick="mergeDuplicateAuthors(${primary.id}, [${allIds.join(',')}])">合并</button> `;
                    html += `<button class="btn btn-secondary btn-sm" onclick="showDuplicateDetails([${allIds.join(',')}])">详情</button>`;
                } else {
                    html += `<a href="#/author/${primary.id}" class="btn btn-secondary btn-sm" style="text-decoration:none;">查看</a>`;
                }
                html += `</td>`;
                html += '</tr>';
            });

            html += '</tbody></table>';

            // 分页
            html += `<div data-pagination>${Components.renderPagination(data.total, authorsState.limit, authorsState.offset, (page) => {
                authorsState.offset = (page - 1) * authorsState.limit;
                updateAuthorsUrl();
                loadAuthors();
            })}</div>`;

            container.innerHTML = html;
        } catch (err) {
            console.error('[authors] 加载失败:', err);
            container.innerHTML = `<div class="empty-state">${I18n.t('common.load_failed')}: ${err.message}</div>`;
            showToast(I18n.t('toast.load_failed', {context: '学者列表', reason: err.message}), 'error');
        }
    }

    // 全局函数：合并重复作者
    window.mergeDuplicateAuthors = async function(primary_id, all_ids) {
        const duplicate_ids = all_ids.filter(id => id !== primary_id);
        if (!duplicate_ids.length) {
            showToast('没有可合并的重复记录', 'warning');
            return;
        }
        
        if (!confirm(`确认将 ${duplicate_ids.length} 条重复记录合并到学者 ID ${primary_id}？\n\n此操作将：\n1. 保留主记录的所有元数据\n2. 转移所有论文关联\n3. 删除重复记录\n\n操作不可撤销，是否继续？`)) {
            return;
        }
        
        try {
            const result = await API.mergeAuthors(primary_id, duplicate_ids);
            if (result.error) {
                showToast(`合并失败: ${result.error}`, 'error');
                return;
            }
            showToast(`合并成功！已合并 ${result.merged_count} 条记录，转移 ${result.merged_papers} 篇论文`, 'success');
            // 刷新列表
            loadAuthors();
        } catch (err) {
            showToast(`合并失败: ${err.message}`, 'error');
        }
    };
    
    // 全局函数：查看重复详情
    window.showDuplicateDetails = async function(all_ids) {
        try {
            const details = await Promise.all(all_ids.map(id => API.getAuthor(id)));
            let html = '<div style="max-height:400px;overflow-y:auto;">';
            details.forEach((data, idx) => {
                const author = data.author || {};
                const stats = data.stats || {};
                html += `<div style="border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:12px;">`;
                html += `<div style="font-weight:600;margin-bottom:8px;">记录 ${idx + 1} (ID: ${author.id})</div>`;
                html += `<div style="font-size:13px;color:var(--text-secondary);">`;
                html += `<div>论文数: ${stats.total_papers || 0}</div>`;
                html += `<div>机构: ${author.current_affiliation || '-'}</div>`;
                html += `<div>ORCID: ${author.orcid || '-'}</div>`;
                html += `<div>创建时间: ${author.created_at || '-'}</div>`;
                html += `</div></div>`;
            });
            html += '</div>';
            openModal('重复记录详情', html);
        } catch (err) {
            showToast(`加载详情失败: ${err.message}`, 'error');
        }
    };

    async function renderAuthorDetail(id) {
        content.innerHTML = '<div class="loading-text">加载学者画像...</div>';
        try {
            const [profile, papers, network] = await Promise.all([
                API.getAuthor(id),
                API.getAuthorPapers(id, { limit: 10, offset: 0 }),
                API.getAuthorNetwork(id, 40)
            ]);
            const author = profile.author || {};
            const stats = profile.stats || {};
            const coauthors = profile.coauthors || [];

            let html = '<h2 style="margin-top:0;">学者画像</h2>';
            html += '<div class="author-card">';
            html += '<div class="author-main">';
            html += `<div class="card">
                <div class="author-name">${Utils.escapeHtml(author.full_name || `学者 ${id}`)}</div>
                <div class="author-meta">
                    ${author.orcid ? `<span>ORCID: <a href="https://orcid.org/${author.orcid}" target="_blank">${author.orcid}</a></span>` : ''}
                    ${author.current_affiliation ? `<span>${Utils.escapeHtml(author.current_affiliation)}</span>` : ''}
                </div>
                <div style="margin-bottom:12px;">
                    ${(author.institutions || []).map(inst => `<span class="tag">${Utils.escapeHtml(inst)}</span>`).join('')}
                </div>
                <div class="card-grid" style="grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));">
                    ${Components.statCard('论文数', stats.total_papers || 0)}
                    ${Components.statCard('总被引', stats.total_citations || 0)}
                    ${Components.statCard('h-index', author.h_index || '—')}
                </div>
            </div>`;

            html += '<div class="card"><h3 class="card-title">关键词分布</h3>';
            if (stats.top_keywords && stats.top_keywords.length) {
                html += Components.renderTagCloud(stats.top_keywords.map(k => ({ key: k.keyword, count: k.count })), (tag) => {
                    window.location.hash = `#/search?q=${encodeURIComponent(tag)}`;
                });
            } else {
                html += '<div class="empty-state">暂无关键词数据</div>';
            }
            html += '</div>';

            html += '<div class="card"><h3 class="card-title">主要合作者</h3>';
            if (coauthors.length) {
                html += '<div class="coauthor-list">' + coauthors.slice(0, 20).map(c =>
                    `<span class="coauthor-item" data-author-id="${c.id}">${Utils.escapeHtml(c.full_name)} (${c.c})</span>`
                ).join('') + '</div>';
            } else {
                html += '<div class="empty-state">暂无合作者数据</div>';
            }
            html += '</div>';

            html += '<div class="card"><h3 class="card-title">合作网络</h3><div id="author-network" class="graph-container" style="height:500px;"></div></div>';

            html += '<div class="card"><h3 class="card-title">代表论文</h3>';
            if (papers.papers && papers.papers.length) {
                const columns = [
                    { key: 'title', label: '标题', render: (v) => Utils.truncate(Utils.escapeHtml(v || ''), 60) },
                    { key: 'year', label: '年份' },
                    { key: 'journal', label: '期刊', render: (v) => Utils.truncate(Utils.escapeHtml(v || ''), 30) },
                    { key: 'citation_count', label: '被引' }
                ];
                html += Components.renderTable(papers.papers, columns, {
                    onRowClick: (row) => { window.location.hash = `#/paper/${row.id}`; }
                });
                if (papers.total > papers.papers.length) {
                    const authorName = encodeURIComponent(author.full_name || '');
                    html += `<div style="margin-top:10px;"><a class="btn btn-secondary" href="#/search?author=${authorName}&mode=keyword">查看全部 ${papers.total} 篇论文</a></div>`;
                }
                html += `<div style="margin-top:10px;"><a class="btn btn-secondary" href="#/network?focus_author=${encodeURIComponent(author.full_name || '')}">在引用网络中定位其论文</a></div>`;
            } else {
                html += '<div class="empty-state">暂无论文数据</div>';
            }
            html += '</div>';
            html += '</div>'; // author-main

            html += '<div class="author-sidebar">';
            html += '<div class="card"><h3 class="card-title">年份分布</h3><div id="author-year-chart"></div></div>';
            html += '<div class="card"><h3 class="card-title">期刊分布</h3><div id="author-journal-chart"></div></div>';
            html += '</div>'; // author-sidebar
            html += '</div>'; // author-card

            content.innerHTML = html;

            setTimeout(() => {
                const yearEl = document.getElementById('author-year-chart');
                if (yearEl && stats.year_distribution && stats.year_distribution.length) {
                    Charts.barChart(yearEl, stats.year_distribution.map(y => ({ label: y.year, value: y.c })), { height: 220 });
                }
                const journalEl = document.getElementById('author-journal-chart');
                if (journalEl && stats.top_journals && stats.top_journals.length) {
                    Charts.horizontalBar(journalEl, stats.top_journals.map(j => ({ label: j.journal, value: j.c })), { height: stats.top_journals.length * 34 + 30 });
                }
                const netEl = document.getElementById('author-network');
                if (netEl && network.nodes && network.nodes.length) {
                    Charts.forceGraph(netEl, network.nodes, network.edges, {
                        show_labels: true,
                        onNodeClick: (n) => {
                            if (n.type === 'author' && n.author_id) {
                                window.location.hash = `#/author/${n.author_id}`;
                            } else if (n.type === 'institution') {
                                window.location.hash = `#/institutions?affiliation=${encodeURIComponent(n.label)}`;
                            }
                        }
                    });
                }
                content.querySelectorAll('.coauthor-item').forEach(el => {
                    el.addEventListener('click', () => {
                        window.location.hash = `#/author/${el.dataset.authorId}`;
                    });
                });
            }, 0);
        } catch (err) {
            console.error('[author detail] 加载失败:', err);
            content.innerHTML = `<div class="empty-state">${I18n.t('toast.load_failed', {context: '学者画像', reason: err.message})}</div>`;
            showToast(I18n.t('toast.load_failed', {context: '学者画像', reason: err.message}), 'error');
        }
    }

    async function renderInstitutions(queryString) {
        const params = parseQuery(queryString);
        const affiliation = params.affiliation || '';

        content.innerHTML = `<h2 style="margin-top:0;">机构合作网络</h2>
            <div class="card">
                <div class="author-search">
                    <input type="text" id="institution-q" placeholder="机构名关键词（留空显示全局 Top 机构）" value="${Utils.escapeHtml(affiliation)}">
                    <button class="btn btn-primary" id="institution-search-btn">搜索</button>
                    <button class="btn btn-secondary" id="institution-papers-btn" ${affiliation ? '' : 'disabled'}>查看该机构学者</button>
                </div>
                <div id="institution-network" class="graph-container" style="height:560px;margin-top:10px;"></div>
                <div id="institution-list" style="margin-top:16px;"></div>
            </div>`;

        const loadNetwork = async (q) => {
            const netEl = document.getElementById('institution-network');
            const listEl = document.getElementById('institution-list');
            netEl.innerHTML = '<div class="loading-text">构建机构网络...</div>';
            listEl.innerHTML = '';
            try {
                const data = await API.getInstitutionNetwork({ affiliation: q, max_nodes: 60, min_papers: 1 });
                const nodes = data.nodes || [];
                const edges = data.edges || [];
                if (!nodes.length) {
                    netEl.innerHTML = '<div class="empty-state">未找到机构数据</div>';
                    return;
                }
                Charts.forceGraph(netEl, nodes, edges, {
                    show_labels: true,
                    onNodeClick: (n) => {
                        if (n.type === 'institution') {
                            document.getElementById('institution-q').value = n.label;
                            loadNetwork(n.label);
                        }
                    }
                });
                const columns = [
                    { key: 'label', label: '机构' },
                    { key: 'paper_count', label: '论文数' },
                    { key: 'is_center', label: '中心', render: (v) => v ? '是' : '' }
                ];
                listEl.innerHTML = '<h3 class="card-title">机构列表</h3>' + Components.renderTable(nodes.filter(n => n.type === 'institution'), columns, {
                    onRowClick: (row) => {
                        document.getElementById('institution-q').value = row.label;
                        loadNetwork(row.label);
                    }
                });
            } catch (err) {
                console.error('[institutions] 加载失败:', err);
                netEl.innerHTML = `<div class="empty-state">${I18n.t('toast.load_failed', {context: '机构网络', reason: err.message})}</div>`;
                showToast(I18n.t('toast.load_failed', {context: '机构网络', reason: err.message}), 'error');
            }
        };

        const doSearch = () => {
            const q = document.getElementById('institution-q').value.trim();
            window.location.hash = '#/institutions' + Utils.buildQueryString({ affiliation: q });
            loadNetwork(q);
        };
        const doViewPapers = () => {
            const q = document.getElementById('institution-q').value.trim();
            if (!q) return;
            window.location.hash = '#/authors?affiliation=' + encodeURIComponent(q);
        };
        document.getElementById('institution-search-btn').addEventListener('click', doSearch);
        document.getElementById('institution-papers-btn').addEventListener('click', doViewPapers);
        document.getElementById('institution-q').addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });

        await loadNetwork(affiliation);
    }

    // ------------------ Workflow / Pipeline ------------------
    async function renderWorkflow() {
        content.innerHTML = `<h2 style="margin-top:0;">文献工作流</h2>
            <div class="card" id="wf-settings-card">
                <h3 class="card-title" style="display:flex;align-items:center;justify-content:space-between;cursor:pointer;" id="wf-settings-toggle">
                    工作流配置
                    <span class="icon" style="font-size:16px;">▼</span>
                </h3>
                <div class="workflow-settings-container" id="wf-settings-container" style="display:none;">
                    <p style="font-size:13px;color:var(--text-secondary);">在此配置 API Key、数据源与解析/提炼参数，保存后立即生效。</p>
                    <div class="workflow-settings" id="wf-settings-form">
                        <div class="settings-section accordion-section">
                            <h4 class="accordion-header" data-section="sources"><span>采集源</span><span class="accordion-icon">▼</span></h4>
                            <div class="accordion-content" id="wf-section-sources" style="display:block;">
                                <div class="checkbox-group">
                                    <label><input type="checkbox" id="wf-cfg-source-crossref" value="crossref" checked> Crossref</label>
                                    <label><input type="checkbox" id="wf-cfg-source-semantic_scholar" value="semantic_scholar"> Semantic Scholar</label>
                                </div>
                            </div>
                        </div>
                        <div class="settings-section accordion-section">
                            <h4 class="accordion-header" data-section="keys"><span>API Keys</span><span class="accordion-icon">▼</span></h4>
                            <div class="accordion-content" id="wf-section-keys" style="display:block;">
                                <div class="settings-grid">
                                    <div class="form-field"><label for="wf-cfg-semantic_scholar_api_key">Semantic Scholar API Key <span style="font-weight:400;color:var(--text-secondary);">(可选)</span></label><input type="password" id="wf-cfg-semantic_scholar_api_key" placeholder="留空使用默认限流配置"></div>
                                    <div class="form-field"><label for="wf-cfg-mineru_api_key">MinerU API Key <span style="font-weight:400;color:var(--danger);">(必填)</span></label><input type="password" id="wf-cfg-mineru_api_key" placeholder="MinerU PDF 解析服务授权"><button class="btn btn-sm btn-secondary" data-test-service="mineru" style="margin-top:4px;">测试连接</button></div>
                                    <div class="form-field"><label for="wf-cfg-llm_api_key">LLM API Key <span style="font-weight:400;color:var(--danger);">(必填)</span></label><input type="password" id="wf-cfg-llm_api_key" placeholder="LLM 提炼服务授权"><button class="btn btn-sm btn-secondary" data-test-service="llm" style="margin-top:4px;">测试连接</button></div>
                                    <div class="form-field"><label for="wf-cfg-embedding_api_key">Embedding API Key <span style="font-weight:400;color:var(--danger);">(必填)</span></label><input type="password" id="wf-cfg-embedding_api_key" placeholder="Embedding 向量化服务授权"><button class="btn btn-sm btn-secondary" data-test-service="embedding" style="margin-top:4px;">测试连接</button></div>
                                    <div class="form-field"><label for="wf-cfg-wos_api_key">Web of Science API Key <span style="font-weight:400;color:var(--text-secondary);">(可选)</span></label><input type="password" id="wf-cfg-wos_api_key" placeholder="启用 Web of Science 采集时填写"><button class="btn btn-sm btn-secondary" data-test-service="wos" style="margin-top:4px;">测试连接</button></div>
                                    <div class="form-field"><label for="wf-cfg-scopus_api_keys">Scopus API Keys <span style="font-weight:400;color:var(--text-secondary);">(可选)</span></label><input type="password" id="wf-cfg-scopus_api_keys" placeholder="多个 key 用英文逗号分隔"><button class="btn btn-sm btn-secondary" data-test-service="scopus" style="margin-top:4px;">测试连接</button></div>
                                </div>
                            </div>
                        </div>
                        <div class="settings-section accordion-section">
                            <h4 class="accordion-header" data-section="pdf-download"><span>PDF 下载策略优先级</span><span class="accordion-icon">▼</span></h4>
                            <div class="accordion-content" id="wf-section-pdf-download" style="display:block;">
                                <p class="accordion-hint">数字越小越优先，0=禁用</p>
                                <div class="settings-grid">
                                    <div class="form-field"><label for="wf-cfg-pdf_strategy_crossref_text_mining">Crossref Text Mining</label><input type="number" id="wf-cfg-pdf_strategy_crossref_text_mining" min="0" max="9"></div>
                                    <div class="form-field"><label for="wf-cfg-pdf_strategy_crossref_pdf">Crossref PDF</label><input type="number" id="wf-cfg-pdf_strategy_crossref_pdf" min="0" max="9"></div>
                                    <div class="form-field"><label for="wf-cfg-pdf_strategy_oa_url">OA URL 直接下载</label><input type="number" id="wf-cfg-pdf_strategy_oa_url" min="0" max="9"></div>
                                    <div class="form-field"><label for="wf-cfg-pdf_strategy_doi_redirect">DOI 重定向</label><input type="number" id="wf-cfg-pdf_strategy_doi_redirect" min="0" max="9"></div>
                                    <div class="form-field"><label for="wf-cfg-pdf_strategy_unpaywall">Unpaywall</label><input type="number" id="wf-cfg-pdf_strategy_unpaywall" min="0" max="9"></div>
                                </div>
                            </div>
                        </div>
                        <div class="settings-section accordion-section">
                            <h4 class="accordion-header" data-section="pdf-parser"><span>PDF 解析策略优先级</span><span class="accordion-icon">▼</span></h4>
                            <div class="accordion-content" id="wf-section-pdf-parser" style="display:block;">
                                <p class="accordion-hint">数字越小越优先，0=禁用</p>
                                <div class="settings-grid">
                                    <div class="form-field"><label for="wf-cfg-pdf_parser_mineru_api">MinerU API</label><input type="number" id="wf-cfg-pdf_parser_mineru_api" min="0" max="9"></div>
                                    <div class="form-field"><label for="wf-cfg-pdf_parser_pymupdf">PyMuPDF</label><input type="number" id="wf-cfg-pdf_parser_pymupdf" min="0" max="9"></div>
                                    <div class="form-field"><label for="wf-cfg-pdf_parser_marker_gpu">Marker GPU</label><input type="number" id="wf-cfg-pdf_parser_marker_gpu" min="0" max="9"></div>
                                    <div class="form-field"><label for="wf-cfg-pdf_parser_marker_cpu">Marker CPU</label><input type="number" id="wf-cfg-pdf_parser_marker_cpu" min="0" max="9"></div>
                                </div>
                            </div>
                        </div>
                        <div class="settings-section accordion-section">
                            <h4 class="accordion-header" data-section="llm"><span>LLM 提炼参数</span><span class="accordion-icon">▼</span></h4>
                            <div class="accordion-content" id="wf-section-llm" style="display:block;">
                                <div class="settings-grid">
                                    <div class="form-field wide"><label for="wf-cfg-llm_base_url">LLM Base URL</label><input type="text" id="wf-cfg-llm_base_url"></div>
                                    <div class="form-field"><label for="wf-cfg-llm_model">模型</label><input type="text" id="wf-cfg-llm_model"></div>
                                    <div class="form-field"><label for="wf-cfg-llm_max_tokens">Max Tokens</label><input type="number" id="wf-cfg-llm_max_tokens" min="1"></div>
                                    <div class="form-field"><label for="wf-cfg-llm_temperature">Temperature</label><input type="number" id="wf-cfg-llm_temperature" step="0.1" min="0" max="2"></div>
                                    <div class="form-field"><label for="wf-cfg-llm_request_timeout">Timeout (秒)</label><input type="number" id="wf-cfg-llm_request_timeout" min="1"></div>
                                    <div class="form-field"><label for="wf-cfg-llm_max_retries">最大重试</label><input type="number" id="wf-cfg-llm_max_retries" min="0"></div>
                                </div>
                            </div>
                        </div>
                        <div class="settings-section accordion-section">
                            <h4 class="accordion-header" data-section="embedding"><span>Embedding 参数</span><span class="accordion-icon">▼</span></h4>
                            <div class="accordion-content" id="wf-section-embedding" style="display:block;">
                                <div class="settings-grid">
                                    <div class="form-field wide"><label for="wf-cfg-embedding_base_url">Embedding Base URL</label><input type="text" id="wf-cfg-embedding_base_url"></div>
                                    <div class="form-field"><label for="wf-cfg-embedding_model">模型</label><input type="text" id="wf-cfg-embedding_model"></div>
                                    <div class="form-field"><label for="wf-cfg-embedding_dim">维度</label><input type="number" id="wf-cfg-embedding_dim" min="1"></div>
                                    <div class="form-field"><label for="wf-cfg-embedding_batch_size">Batch Size</label><input type="number" id="wf-cfg-embedding_batch_size" min="1"></div>
                                </div>
                            </div>
                        </div>
                    <div style="margin-top:12px;">
                        <button class="btn btn-primary" id="wf-save-settings">保存配置</button>
                        <span id="wf-settings-status" style="margin-left:12px;font-size:13px;color:var(--text-secondary);"></span>
                    </div>
                </div>
                </div>
            </div>
            <div class="card-grid">
                <div class="card">
                    <h3 class="card-title">1. 文献采集</h3>
                    <p style="font-size:13px;color:var(--text-secondary);">输入关键词与筛选条件，从已配置的采集源获取元数据入库。</p>
                    <div class="workflow-form">
                        <div class="form-field">
                            <label for="wf-keyword">采集关键词 <span style="color:var(--danger);">*</span></label>
                            <input type="text" id="wf-keyword" placeholder="如 livestock grazing">
                        </div>
                        <div class="wf-row-3">
                            <div class="form-field">
                                <label for="wf-year-from">起始年份</label>
                                <input type="number" id="wf-year-from" placeholder="如 2020" min="1900" max="2026">
                            </div>
                            <div class="form-field">
                                <label for="wf-year-to">截止年份</label>
                                <input type="number" id="wf-year-to" placeholder="如 2024" min="1900" max="2026">
                            </div>
                            <div class="form-field">
                                <label for="wf-journal">期刊名称</label>
                                <input type="text" id="wf-journal" placeholder="如 Nature, Science">
                            </div>
                        </div>
                        <div class="wf-row-2">
                            <div class="form-field">
                                <label for="wf-rows">每页条数</label>
                                <input type="number" id="wf-rows" value="20" min="1" max="100">
                            </div>
                            <div class="form-field">
                                <label for="wf-pages">最大页数</label>
                                <input type="number" id="wf-pages" value="2" min="1" max="20">
                            </div>
                        </div>
                        <button class="btn btn-primary" id="wf-collect">开始采集</button>
                    </div>
                </div>
                <div class="card">
                    <h3 class="card-title">2. PDF 解析</h3>
                    <p style="font-size:13px;color:var(--text-secondary);">下载并解析开放获取论文的全文。</p>
                    <div class="workflow-form">
                        <div class="form-field">
                            <label for="wf-parse-source">解析数据源</label>
                            <select id="wf-parse-source">
                                <option value="all" selected>全部来源</option>
                                <option value="arxiv">arxiv</option>
                                <option value="crossref">crossref</option>
                                <option value="semantic_scholar">semantic_scholar</option>
                            </select>
                        </div>
                        <div class="form-field">
                            <label for="wf-parse-limit">最多解析篇数</label>
                            <input type="number" id="wf-parse-limit" value="5" min="1" max="50">
                        </div>
                        <div class="form-field checkbox">
                            <label><input type="checkbox" id="wf-parse-force"> 强制重解析（忽略已解析记录）</label>
                        </div>
                        <button class="btn btn-primary" id="wf-parse">开始解析</button>
                    </div>
                </div>
                <div class="card">
                    <h3 class="card-title">3. LLM 提炼</h3>
                    <p style="font-size:13px;color:var(--text-secondary);">对未提炼的已解析论文运行知识卡片、方法流程、数据点提取与向量化。</p>
                    <button class="btn btn-primary" id="wf-extract">开始提炼</button>
                </div>
                <div class="card card-pipeline">
                    <h3 class="card-title">4. 一键全流程</h3>
                    <p style="font-size:13px;color:var(--text-secondary);margin-bottom:8px;">自动串联采集→解析→提炼，参数从上方三个卡片中读取。</p>
                    <div class="pipeline-params-summary" id="pipeline-params-summary">
                        <span class="pipeline-param-item"><span class="pipeline-param-label">关键词</span><span class="pipeline-param-value" id="pipeline-summary-keyword">—</span></span>
                        <span class="pipeline-param-item"><span class="pipeline-param-label">年份</span><span class="pipeline-param-value" id="pipeline-summary-year">—</span></span>
                        <span class="pipeline-param-item"><span class="pipeline-param-label">解析源</span><span class="pipeline-param-value" id="pipeline-summary-source">—</span></span>
                        <span class="pipeline-param-item"><span class="pipeline-param-label">解析上限</span><span class="pipeline-param-value" id="pipeline-summary-limit">—</span></span>
                    </div>
                    <button class="btn btn-primary btn-lg" id="wf-pipeline-run" style="width:100%;">开始全流程</button>
                </div>
            </div>
            <div class="card">
                <h3 class="card-title">失败原因统计</h3>
                <div style="margin-bottom:12px;">
                    <button class="btn btn-secondary" id="wf-refresh-stats">刷新统计</button>
                    <button class="btn btn-secondary" id="wf-archive-jobs" style="margin-left:8px;">归档旧任务</button>
                    <span id="wf-archive-status" style="margin-left:12px;font-size:13px;color:var(--text-secondary);"></span>
                </div>
                <div id="wf-jobs-stats"></div>
            </div>
            <div class="card">
                <h3 class="card-title">任务与解析作业状态</h3>
                <div style="margin-bottom:12px;display:flex;gap:10px;flex-wrap:wrap;align-items:center;">
                    <button class="btn btn-secondary" id="wf-refresh-jobs">刷新</button>
                    <select id="wf-jobs-status" class="form-select" style="width:auto;min-width:100px;">
                        <option value="">全部状态</option>
                        <option value="pending">pending</option>
                        <option value="running">running</option>
                        <option value="done">done</option>
                        <option value="failed">failed</option>
                        <option value="permanent_failed">permanent_failed</option>
                    </select>
                    <select id="wf-jobs-stage" class="form-select" style="width:auto;min-width:100px;">
                        <option value="">全部阶段</option>
                        <option value="download">download</option>
                        <option value="parse">parse</option>
                        <option value="extract">extract</option>
                    </select>
                    <input type="text" id="wf-jobs-error-class" placeholder="错误类别过滤" style="width:auto;min-width:120px;">
                    <span id="wf-jobs-pagination-info" style="font-size:13px;color:var(--text-secondary);"></span>
                </div>
                <div id="wf-jobs-summary"></div>
                <div id="wf-jobs-list"></div>
                <div id="wf-jobs-pagination" style="margin-top:12px;display:flex;gap:8px;justify-content:center;"></div>
            </div>`;

        // 工作流配置加载与保存
        const cfgFields = [
            'collect_sources',
            'semantic_scholar_api_key', 'mineru_api_key', 'llm_api_key', 'embedding_api_key', 'wos_api_key', 'scopus_api_keys',
            'pdf_strategy_crossref_text_mining', 'pdf_strategy_crossref_pdf', 'pdf_strategy_oa_url', 'pdf_strategy_doi_redirect', 'pdf_strategy_unpaywall',
            'pdf_parser_mineru_api', 'pdf_parser_pymupdf', 'pdf_parser_marker_gpu', 'pdf_parser_marker_cpu',
            'llm_base_url', 'llm_model', 'llm_max_tokens', 'llm_temperature', 'llm_request_timeout', 'llm_max_retries',
            'embedding_base_url', 'embedding_model', 'embedding_dim', 'embedding_batch_size'
        ];

        let loadedSettings = {};

        const loadSettings = async () => {
            try {
                const settings = await API.getWorkflowSettings();
                loadedSettings = { ...settings };
                // 采集源
                const sources = settings.collect_sources || ['crossref'];
                document.getElementById('wf-cfg-source-crossref').checked = sources.includes('crossref');
                document.getElementById('wf-cfg-source-semantic_scholar').checked = sources.includes('semantic_scholar');
                // 文本与数字字段
                cfgFields.slice(1).forEach(key => {
                    const el = document.getElementById('wf-cfg-' + key);
                    if (el && settings[key] !== undefined) el.value = settings[key];
                });
            } catch (err) {
                showToast('加载配置失败: ' + err.message, 'error');
            }
        };

        const saveSettings = async () => {
            const btn = document.getElementById('wf-save-settings');
            const status = document.getElementById('wf-settings-status');
            btn.disabled = true;
            status.textContent = '保存中...';
            try {
                const sources = [];
                if (document.getElementById('wf-cfg-source-crossref').checked) sources.push('crossref');
                if (document.getElementById('wf-cfg-source-semantic_scholar').checked) sources.push('semantic_scholar');
                const updates = { collect_sources: sources };
                const sensitiveKeys = ['semantic_scholar_api_key', 'mineru_api_key', 'llm_api_key', 'embedding_api_key', 'wos_api_key', 'scopus_api_keys'];
                cfgFields.slice(1).forEach(key => {
                    const el = document.getElementById('wf-cfg-' + key);
                    if (!el) return;
                    const value = el.value;
                    // 敏感 key 未修改（仍是脱敏占位符）时不提交
                    if (sensitiveKeys.includes(key) && value === loadedSettings[key]) return;
                    updates[key] = value;
                });
                await API.setWorkflowSettings(updates);
                status.textContent = '已保存';
                showToast('配置已保存', 'success');
                await loadSettings();
            } catch (err) {
                status.textContent = '保存失败';
                showToast('保存配置失败: ' + err.message, 'error');
            } finally {
                btn.disabled = false;
            }
        };

        document.getElementById('wf-save-settings').addEventListener('click', saveSettings);
        loadSettings();

        // 测试连接按钮事件
        document.querySelectorAll('[data-test-service]').forEach(btn => {
            btn.addEventListener('click', async () => {
                const service = btn.dataset.testService;
                const originalText = btn.textContent;
                btn.disabled = true;
                btn.textContent = '测试中...';
                
                try {
                    const data = { service };
                    
                    // 根据服务类型收集参数
                    if (service === 'llm') {
                        data.api_key = document.getElementById('wf-cfg-llm_api_key').value;
                        data.base_url = document.getElementById('wf-cfg-llm_base_url').value;
                        data.model = document.getElementById('wf-cfg-llm_model').value;
                    } else if (service === 'embedding') {
                        data.api_key = document.getElementById('wf-cfg-embedding_api_key').value;
                        data.base_url = document.getElementById('wf-cfg-embedding_base_url').value;
                        data.model = document.getElementById('wf-cfg-embedding_model').value;
                    } else if (service === 'mineru') {
                        data.api_key = document.getElementById('wf-cfg-mineru_api_key').value;
                    } else if (service === 'wos') {
                        data.api_key = document.getElementById('wf-cfg-wos_api_key').value;
                    } else if (service === 'scopus') {
                        data.api_key = document.getElementById('wf-cfg-scopus_api_keys').value;
                    }
                    
                    const result = await API.testConnection(data);
                    
                    if (result.success) {
                        btn.textContent = '✓ 连接成功';
                        btn.style.background = 'var(--success)';
                        btn.style.color = 'white';
                        showToast(`${service} 连接测试成功`, 'success');
                    } else {
                        btn.textContent = '✗ 连接失败';
                        btn.style.background = 'var(--danger)';
                        btn.style.color = 'white';
                        showToast(`${service} 连接测试失败: ${result.message}`, 'error');
                    }
                    
                    // 3秒后恢复按钮状态
                    setTimeout(() => {
                        btn.textContent = originalText;
                        btn.style.background = '';
                        btn.style.color = '';
                        btn.disabled = false;
                    }, 3000);
                    
                } catch (err) {
                    btn.textContent = '✗ 测试失败';
                    btn.style.background = 'var(--danger)';
                    btn.style.color = 'white';
                    showToast(`测试失败: ${err.message}`, 'error');
                    
                    setTimeout(() => {
                        btn.textContent = originalText;
                        btn.style.background = '';
                        btn.style.color = '';
                        btn.disabled = false;
                    }, 3000);
                }
            });
        });

        // 工作流配置折叠/展开
        const toggle = document.getElementById('wf-settings-toggle');
        const container = document.getElementById('wf-settings-container');
        const icon = toggle.querySelector('.icon');
        toggle.addEventListener('click', () => {
            const isExpanded = container.style.display !== 'none';
            container.style.display = isExpanded ? 'none' : 'block';
            icon.textContent = isExpanded ? '▼' : '▲';
        });

        // 配置内 Accordion
        document.querySelectorAll('.accordion-header').forEach(header => {
            header.addEventListener('click', () => {
                const section = header.dataset.section;
                const content = document.getElementById(`wf-section-${section}`);
                const icon = header.querySelector('.accordion-icon');
                if (!content) return;
                const isExpanded = content.style.display !== 'none';
                content.style.display = isExpanded ? 'none' : 'block';
                icon.textContent = isExpanded ? '▶' : '▼';
            });
        });

        const bindTask = (btnId, fn, getData) => {
            const btn = document.getElementById(btnId);
            btn.addEventListener('click', async () => {
                btn.disabled = true;
                try {
                    const data = getData ? getData() : {};
                    const res = await fn(data);
                    showToast(`任务已启动: ${res.task_id}`, 'success');
                    showProgress(res.task_id, () => {
                        btn.disabled = false;
                        showToast('任务完成', 'success');
                        loadJobs();
                    });
                } catch (err) {
                    btn.disabled = false;
                    showToast('启动失败: ' + err.message, 'error');
                }
            });
        };

        bindTask('wf-collect', API.collect, () => ({
            keyword: document.getElementById('wf-keyword').value.trim(),
            rows: parseInt(document.getElementById('wf-rows').value, 10) || 20,
            max_pages: parseInt(document.getElementById('wf-pages').value, 10) || 2,
            year_from: document.getElementById('wf-year-from').value.trim(),
            year_to: document.getElementById('wf-year-to').value.trim(),
            journal: document.getElementById('wf-journal').value.trim()
        }));
        bindTask('wf-parse', API.parse, () => ({
            source: document.getElementById('wf-parse-source').value,
            limit: parseInt(document.getElementById('wf-parse-limit').value, 10) || 5,
            force: document.getElementById('wf-parse-force').checked
        }));
        bindTask('wf-extract', API.extract, null);
        bindTask('wf-pipeline-run', API.pipelineRun, () => ({
            keyword: document.getElementById('wf-keyword').value.trim(),
            rows: parseInt(document.getElementById('wf-rows').value, 10) || 20,
            max_pages: parseInt(document.getElementById('wf-pages').value, 10) || 2,
            year_from: document.getElementById('wf-year-from').value.trim(),
            year_to: document.getElementById('wf-year-to').value.trim(),
            journal: document.getElementById('wf-journal').value.trim(),
            parse_source: document.getElementById('wf-parse-source').value,
            parse_limit: parseInt(document.getElementById('wf-parse-limit').value, 10) || 5
        }));

        // 一键全流程：参数实时同步预览
        const syncPipelineSummary = () => {
            const kw = document.getElementById('wf-keyword').value.trim() || '—';
            const yf = document.getElementById('wf-year-from').value.trim();
            const yt = document.getElementById('wf-year-to').value.trim();
            const year = (yf || yt) ? `${yf || '...'} ~ ${yt || '...'}` : '不限';
            const src = document.getElementById('wf-parse-source').value;
            const srcLabel = { all: '全部', arxiv: 'arxiv', crossref: 'crossref', semantic_scholar: 'Semantic Scholar' }[src] || src;
            const lim = document.getElementById('wf-parse-limit').value || '5';
            document.getElementById('pipeline-summary-keyword').textContent = kw;
            document.getElementById('pipeline-summary-year').textContent = year;
            document.getElementById('pipeline-summary-source').textContent = srcLabel;
            document.getElementById('pipeline-summary-limit').textContent = lim;
        };
        ['wf-keyword', 'wf-year-from', 'wf-year-to', 'wf-journal', 'wf-rows', 'wf-pages',
         'wf-parse-source', 'wf-parse-limit', 'wf-parse-force'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('input', syncPipelineSummary);
        });
        syncPipelineSummary();

        const summaryEl = document.getElementById('wf-jobs-summary');
        const listEl = document.getElementById('wf-jobs-list');
        const paginationEl = document.getElementById('wf-jobs-pagination');
        const paginationInfoEl = document.getElementById('wf-jobs-pagination-info');
        const statsEl = document.getElementById('wf-jobs-stats');

        const jobsState = {
            limit: 20,
            offset: 0,
            status: '',
            stage: '',
            errorClass: ''
        };

        const renderPagination = (total, limit, offset) => {
            if (!total) {
                paginationEl.innerHTML = '';
                paginationInfoEl.textContent = '';
                return;
            }
            const totalPages = Math.ceil(total / limit);
            const currentPage = Math.floor(offset / limit) + 1;
            paginationInfoEl.textContent = `共 ${total} 条，第 ${currentPage}/${totalPages} 页`;
            if (totalPages <= 1) {
                paginationEl.innerHTML = '';
                return;
            }
            let html = '';
            for (let i = 1; i <= totalPages; i++) {
                const active = i === currentPage ? 'btn-primary' : 'btn-secondary';
                html += `<button class="btn btn-sm ${active}" data-page="${i}">${i}</button>`;
            }
            paginationEl.innerHTML = html;
            paginationEl.querySelectorAll('button').forEach(btn => {
                btn.addEventListener('click', () => {
                    jobsState.offset = (parseInt(btn.dataset.page, 10) - 1) * jobsState.limit;
                    loadJobs();
                });
            });
        };

        const loadJobs = async () => {
            try {
                const params = { limit: jobsState.limit, offset: jobsState.offset };
                if (jobsState.status) params.status = jobsState.status;
                if (jobsState.stage) params.stage = jobsState.stage;
                if (jobsState.errorClass) params.error_class = jobsState.errorClass;

                const data = await API.getJobs(params);
                if (data.summary && data.summary.length) {
                    summaryEl.innerHTML = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;">' +
                        data.summary.map(s => `<span class="tag">${s.stage || ''}/${s.status || ''}: ${s.c}</span>`).join('') +
                        '</div>';
                } else {
                    summaryEl.innerHTML = '<div class="empty-state">暂无解析作业</div>';
                }
                const columns = [
                    { key: 'id', label: 'Job ID' },
                    { key: 'paper_id', label: '论文ID' },
                    { key: 'stage', label: '阶段' },
                    { key: 'status', label: '状态' },
                    { key: 'error_class', label: '错误类别', render: (v) => v || '-' },
                    { key: 'progress', label: '进度', render: (v) => `${v || 0}%` },
                    { key: 'message', label: '消息', render: (v) => Utils.truncate(v, 60) },
                    { key: 'created_at', label: '创建时间', render: (v) => v ? new Date(v).toLocaleString() : '' },
                    { key: 'actions', label: '操作', render: (_v, row) => {
                        const canRetry = ['failed', 'permanent_failed'].includes(row.status) && row.paper_id && row.stage;
                        return canRetry ? `<button class="btn btn-sm btn-retry" data-retry-id="${row.id}" data-retry-pid="${row.paper_id}" data-retry-stage="${row.stage}">重试</button>` : '';
                    }}
                ];
                const tableId = 'wf-jobs-table-' + Date.now();
                listEl.innerHTML = `<div id="${tableId}">` + Components.renderTable(data.jobs || [], columns, {
                    onRowClick: (row) => { if (row.paper_id) window.location.hash = `#/paper/${row.paper_id}`; }
                }) + '</div>';
                renderPagination(data.total || 0, jobsState.limit, jobsState.offset);
                setTimeout(() => {
                    document.querySelectorAll(`#${tableId} .btn-retry`).forEach(btn => {
                        btn.addEventListener('click', async (e) => {
                            e.stopPropagation();
                            const pid = parseInt(btn.dataset.retryPid, 10);
                            const stage = btn.dataset.retryStage;
                            const jobId = parseInt(btn.dataset.retryId, 10);
                            if (!pid || !stage) return;
                            btn.disabled = true;
                            btn.textContent = '重试中...';
                            try {
                                const res = await API.retryJob({ paper_id: pid, stage, job_id: jobId });
                                showToast(`重试任务已启动: ${res.task_id}`, 'success');
                                showProgress(res.task_id, () => {
                                    showToast('重试完成', 'success');
                                    loadJobs();
                                });
                            } catch (err) {
                                btn.disabled = false;
                                btn.textContent = '重试';
                                showToast('重试失败: ' + err.message, 'error');
                            }
                        });
                    });
                }, 0);
            } catch (err) {
                console.error('[workflow] 任务列表加载失败:', err);
                summaryEl.innerHTML = `<div class="empty-state">${I18n.t('common.load_failed')}: ${err.message}</div>`;
                listEl.innerHTML = '';
                paginationEl.innerHTML = '';
                paginationInfoEl.textContent = '';
                showToast(I18n.t('toast.load_failed', {context: '任务列表', reason: err.message}), 'error');
            }
        };

        const loadStats = async () => {
            try {
                const stats = await API.getJobStats();
                let html = `<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px;">
                    <span class="tag">失败总数: ${stats.total_failed || 0}</span>
                    <span class="tag">已归档: ${stats.archived_count || 0}</span>
                </div>`;
                if (stats.by_error_class && stats.by_error_class.length) {
                    html += '<table class="data-table"><thead><tr><th>错误类别</th><th>数量</th></tr></thead><tbody>';
                    html += stats.by_error_class.map(s => `<tr><td>${Utils.escapeHtml(s.error_class || I18n.t('paper.meta.unknown'))}</td><td>${s.c}</td></tr>`).join('');
                    html += '</tbody></table>';
                } else {
                    html += '<div class="empty-state">暂无失败统计</div>';
                }
                statsEl.innerHTML = html;
            } catch (err) {
                console.error('[workflow] 统计加载失败:', err);
                statsEl.innerHTML = `<div class="empty-state">${I18n.t('common.load_failed')}: ${err.message}</div>`;
            }
        };

        const bindFilter = (id, key) => {
            const el = document.getElementById(id);
            if (!el) return;
            el.addEventListener('change', () => {
                jobsState[key] = el.value;
                jobsState.offset = 0;
                loadJobs();
            });
        };
        bindFilter('wf-jobs-status', 'status');
        bindFilter('wf-jobs-stage', 'stage');
        const errorClassInput = document.getElementById('wf-jobs-error-class');
        if (errorClassInput) {
            errorClassInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    jobsState.errorClass = errorClassInput.value.trim();
                    jobsState.offset = 0;
                    loadJobs();
                }
            });
            errorClassInput.addEventListener('blur', () => {
                jobsState.errorClass = errorClassInput.value.trim();
                jobsState.offset = 0;
                loadJobs();
            });
        }

        document.getElementById('wf-refresh-jobs').addEventListener('click', loadJobs);
        document.getElementById('wf-refresh-stats').addEventListener('click', loadStats);
        document.getElementById('wf-archive-jobs').addEventListener('click', async () => {
            const btn = document.getElementById('wf-archive-jobs');
            const status = document.getElementById('wf-archive-status');
            if (!confirm('确定要归档 7 天前的已完成/失败任务吗？')) return;
            btn.disabled = true;
            status.textContent = '归档中...';
            try {
                const res = await API.archiveJobs({ days: 7, batch: 1000 });
                showToast(`归档任务已启动: ${res.task_id}`, 'success');
                showProgress(res.task_id, () => {
                    showToast('归档完成', 'success');
                    loadJobs();
                    loadStats();
                });
            } catch (err) {
                btn.disabled = false;
                status.textContent = '归档失败';
                showToast('归档失败: ' + err.message, 'error');
            }
        });

        loadJobs();
        loadStats();
    }

    // ------------------ Knowledge Base ------------------
    let kbState = {
        tab: 'papers', q: '', year_from: '', year_to: '',
        journal: '', source: '', sort: 'year_desc', offset: 0, limit: 25
    };

    async function renderKnowledgeBase(queryString) {
        const params = parseQuery(queryString);
        kbState.tab = params.tab || 'papers';
        kbState.q = params.q || '';
        kbState.year_from = params.year_from || '';
        kbState.year_to = params.year_to || '';
        kbState.journal = params.journal || '';
        kbState.source = params.source || '';
        kbState.sort = params.sort || 'year_desc';
        kbState.offset = parseInt(params.offset || '0', 10);

        const placeholders = {
            papers: '标题 / 摘要 / 期刊关键词',
            data_points: '指标名称，如 cattle count',
            knowledge: '研究问题 / 核心结论 / 主张内容',
            methods: '研究方法 / 数据来源 / 模型算法'
        };
        const showJournalSource = kbState.tab === 'papers';
        content.innerHTML = `<h2 style="margin-top:0;">知识库</h2>
            <div class="knowledgebase-toolbar">
                <input type="text" id="kb-q" placeholder="${placeholders[kbState.tab] || placeholders.papers}" value="${Utils.escapeHtml(kbState.q)}">
                <input type="number" id="kb-year-from" placeholder="起年" value="${Utils.escapeHtml(kbState.year_from)}">
                <input type="number" id="kb-year-to" placeholder="止年" value="${Utils.escapeHtml(kbState.year_to)}">
                ${showJournalSource ? `<input type="text" id="kb-journal" placeholder="期刊" value="${Utils.escapeHtml(kbState.journal)}">` : ''}
                ${showJournalSource ? `<input type="text" id="kb-source" placeholder="来源" value="${Utils.escapeHtml(kbState.source)}">` : ''}
                <select id="kb-sort">
                    <option value="year_desc" ${kbState.sort === 'year_desc' ? 'selected' : ''}>年份降序</option>
                    <option value="year_asc" ${kbState.sort === 'year_asc' ? 'selected' : ''}>年份升序</option>
                    <option value="citations_desc" ${kbState.sort === 'citations_desc' ? 'selected' : ''}>被引降序</option>
                    <option value="title_asc" ${kbState.sort === 'title_asc' ? 'selected' : ''}>标题升序</option>
                </select>
                <button class="btn btn-primary" id="kb-search">搜索</button>
            </div>
            <div class="knowledgebase-tabs">
                <button class="knowledgebase-tab ${kbState.tab === 'papers' ? 'active' : ''}" data-tab="papers">论文</button>
                <button class="knowledgebase-tab ${kbState.tab === 'data_points' ? 'active' : ''}" data-tab="data_points">数据点</button>
                <button class="knowledgebase-tab ${kbState.tab === 'knowledge' ? 'active' : ''}" data-tab="knowledge">知识卡片</button>
                <button class="knowledgebase-tab ${kbState.tab === 'methods' ? 'active' : ''}" data-tab="methods">方法流程</button>
            </div>
            <div id="kb-result"></div>`;

        const searchBtn = document.getElementById('kb-search');
        const refresh = () => {
            kbState.q = document.getElementById('kb-q').value.trim();
            kbState.year_from = document.getElementById('kb-year-from').value.trim();
            kbState.year_to = document.getElementById('kb-year-to').value.trim();
            const journalEl = document.getElementById('kb-journal');
            const sourceEl = document.getElementById('kb-source');
            kbState.journal = journalEl ? journalEl.value.trim() : '';
            kbState.source = sourceEl ? sourceEl.value.trim() : '';
            kbState.sort = document.getElementById('kb-sort').value;
            kbState.offset = 0;
            updateKbUrl();
            loadKnowledgeBase();
        };
        searchBtn.addEventListener('click', refresh);
        document.getElementById('kb-q').addEventListener('keydown', e => { if (e.key === 'Enter') refresh(); });
        document.getElementById('kb-sort').addEventListener('change', refresh);

        document.querySelectorAll('.knowledgebase-tab').forEach(btn => {
            btn.addEventListener('click', () => {
                kbState.tab = btn.dataset.tab;
                kbState.offset = 0;
                updateKbUrl();
                renderKnowledgeBase(window.location.hash.slice(1).split('?')[1] || '');
            });
        });

        await loadKnowledgeBase();
    }

    function updateKbUrl() {
        const p = {
            tab: kbState.tab, q: kbState.q,
            year_from: kbState.year_from, year_to: kbState.year_to,
            journal: kbState.journal, source: kbState.source,
            sort: kbState.sort, offset: kbState.offset
        };
        window.location.hash = '#/knowledgebase' + Utils.buildQueryString(p);
    }

    async function loadKnowledgeBase() {
        const resultEl = document.getElementById('kb-result');
        resultEl.innerHTML = '<div class="loading-text">' + I18n.t('common.loading') + '</div>';
        try {
            if (kbState.tab === 'papers') {
                const params = {
                    q: kbState.q,
                    year_from: kbState.year_from || undefined,
                    year_to: kbState.year_to || undefined,
                    journal: kbState.journal || undefined,
                    source: kbState.source || undefined,
                    sort: kbState.sort,
                    limit: kbState.limit,
                    offset: kbState.offset
                };
                const data = await API.getPapersList(params);
                const columns = [
                    { key: 'title', label: '标题' },
                    { key: 'year', label: '年份' },
                    { key: 'journal', label: '期刊' },
                    { key: 'source', label: '来源' },
                    { key: 'citation_count', label: '被引' },
                    { key: 'keywords', label: '关键词', render: (v) => {
                        const arr = Array.isArray(v) ? v : (v ? [v] : []);
                        return arr.slice(0, 5).map(k => `<span class="tag">${Utils.escapeHtml(k)}</span>`).join('');
                    }}
                ];
                let html = Components.renderTable(data.papers, columns, {
                    onRowClick: (row) => { window.location.hash = `#/paper/${row.id}`; }
                });
                html += `<div data-pagination>${Components.renderPagination(data.total, kbState.limit, kbState.offset, (page) => {
                    kbState.offset = (page - 1) * kbState.limit;
                    updateKbUrl();
                    loadKnowledgeBase();
                })}</div>`;
                resultEl.innerHTML = html;
            } else if (kbState.tab === 'data_points') {
                const params = {
                    metric_name: kbState.q,
                    year_from: kbState.year_from || undefined,
                    year_to: kbState.year_to || undefined,
                    limit: kbState.limit,
                    offset: kbState.offset
                };
                const data = await API.getDataPointsList(params);
                const columns = [
                    { key: 'metric_name', label: '指标' },
                    { key: 'metric_value', label: '数值' },
                    { key: 'unit', label: '单位' },
                    { key: 'year', label: '年份' },
                    { key: 'paper_title', label: '论文' },
                    { key: 'context', label: '上下文' }
                ];
                let html = Components.renderTable(data.data_points, columns, {
                    onRowClick: (row) => { window.location.hash = `#/paper/${row.paper_id}`; }
                });
                html += `<div data-pagination>${Components.renderPagination(data.total, kbState.limit, kbState.offset, (page) => {
                    kbState.offset = (page - 1) * kbState.limit;
                    updateKbUrl();
                    loadKnowledgeBase();
                })}</div>`;
                resultEl.innerHTML = html;
            } else if (kbState.tab === 'knowledge') {
                const params = {
                    q: kbState.q,
                    year_from: kbState.year_from || undefined,
                    year_to: kbState.year_to || undefined,
                    limit: kbState.limit,
                    offset: kbState.offset
                };
                const data = await API.getKnowledgeList(params);
                const columns = [
                    { key: 'paper_title', label: '论文' },
                    { key: 'year', label: '年份' },
                    { key: 'research_question', label: '研究问题', render: (v) => Utils.truncate(v, 120) },
                    { key: 'core_answer', label: '核心回答', render: (v) => Utils.truncate(v, 120) },
                    { key: 'key_claims_count', label: '主张数' },
                    { key: 'has_reusable_inspiration', label: '可复用启发', render: (v) => v ? '有' : '' }
                ];
                let html = Components.renderTable(data.knowledge, columns, {
                    onRowClick: (row) => { window.location.hash = `#/paper/${row.paper_id}`; }
                });
                html += `<div data-pagination>${Components.renderPagination(data.total, kbState.limit, kbState.offset, (page) => {
                    kbState.offset = (page - 1) * kbState.limit;
                    updateKbUrl();
                    loadKnowledgeBase();
                })}</div>`;
                resultEl.innerHTML = html;
            } else if (kbState.tab === 'methods') {
                const params = {
                    q: kbState.q,
                    year_from: kbState.year_from || undefined,
                    year_to: kbState.year_to || undefined,
                    limit: kbState.limit,
                    offset: kbState.offset
                };
                const data = await API.getMethodsList(params);
                const columns = [
                    { key: 'paper_title', label: '论文' },
                    { key: 'year', label: '年份' },
                    { key: 'methodology', label: '研究方法', render: (v) => Utils.truncate(v, 120) },
                    { key: 'data_sources', label: '数据来源', render: (v) => Utils.truncate(typeof v === 'string' ? v : JSON.stringify(v), 80) },
                    { key: 'models_algorithms', label: '模型/算法', render: (v) => Utils.truncate(typeof v === 'string' ? v : JSON.stringify(v), 80) }
                ];
                let html = Components.renderTable(data.methods, columns, {
                    onRowClick: (row) => { window.location.hash = `#/paper/${row.paper_id}`; }
                });
                html += `<div data-pagination>${Components.renderPagination(data.total, kbState.limit, kbState.offset, (page) => {
                    kbState.offset = (page - 1) * kbState.limit;
                    updateKbUrl();
                    loadKnowledgeBase();
                })}</div>`;
                resultEl.innerHTML = html;
            }
        } catch (err) {
            console.error('[knowledgebase] 加载失败:', err);
            resultEl.innerHTML = `<div class="empty-state">${I18n.t('common.load_failed')}: ${err.message}</div>`;
            showToast(I18n.t('toast.load_failed', {context: '知识库', reason: err.message}), 'error');
        }
    }

    // ------------------ Timeline ------------------
    async function renderTimeline(queryString) {
        const params = parseQuery(queryString);
        let currentRange = { year_from: params.year_from ? parseInt(params.year_from, 10) : null, year_to: params.year_to ? parseInt(params.year_to, 10) : null };

        content.innerHTML = `<h2 style="margin-top:0;">论文发表时间线</h2>
            <div id="timeline-slider" style="margin-bottom:16px;"></div>
            <div id="timeline-chart" class="timeline-chart"></div>
            <div class="card"><h3 class="card-title">该区间论文</h3><div id="timeline-papers"></div></div>`;

        const chartEl = document.getElementById('timeline-chart');
        const papersEl = document.getElementById('timeline-papers');
        const sliderEl = document.getElementById('timeline-slider');

        try {
            const data = await API.getTimeline({});
            // 过滤非法年份；时间线以论文发表年份为主轴，剔除无论文的年份
            const validYears = (data.years || []).filter(y => {
                if (!y || !/^\d{4}$/.test(String(y.year))) return false;
                return (y.paper_count || 0) > 0;
            });
            const years = validYears.map(y => parseInt(y.year, 10));
            const fallbackYear = new Date().getFullYear();
            const min = years.length ? Math.min(...years) : 2000;
            const max = years.length ? Math.max(...years) : fallbackYear;
            if (currentRange.year_from == null || isNaN(currentRange.year_from)) currentRange.year_from = min;
            if (currentRange.year_to == null || isNaN(currentRange.year_to)) currentRange.year_to = max;

            if (!years.length) {
                chartEl.innerHTML = '<div class="empty-state">暂无有效年份数据</div>';
                papersEl.innerHTML = '<div class="empty-state">暂无论文数据</div>';
                sliderEl.innerHTML = '';
                return;
            }

            sliderEl.innerHTML = Components.renderYearSlider(min, max, currentRange, (range) => {
                currentRange = range;
                updateTimelineUrl();
                loadTimeline();
            });

            const loadTimeline = async () => {
                const filtered = validYears.filter(y => {
                    const yv = parseInt(y.year, 10);
                    return yv >= currentRange.year_from && yv <= currentRange.year_to;
                });
                if (!filtered.length) {
                    chartEl.innerHTML = '<div class="empty-state">该区间暂无数据</div>';
                    papersEl.innerHTML = '<div class="empty-state">该区间暂无论文</div>';
                    return;
                }
                Charts.timelineChart(chartEl, filtered);
                try {
                    const paperData = await API.getPapersList({
                        year_from: currentRange.year_from,
                        year_to: currentRange.year_to,
                        limit: 100, sort: 'year_desc'
                    });
                    const columns = [
                        { key: 'title', label: '标题' },
                        { key: 'year', label: '年份' },
                        { key: 'journal', label: '期刊' },
                        { key: 'citation_count', label: '被引' }
                    ];
                    papersEl.innerHTML = Components.renderTable(paperData.papers, columns, {
                        onRowClick: (row) => { window.location.hash = `#/paper/${row.id}`; }
                    });
                } catch (err) {
                    console.error('[timeline] 论文列表加载失败:', err);
                    papersEl.innerHTML = `<div class="empty-state">${I18n.t('toast.load_failed', {context: '论文列表', reason: err.message})}</div>`;
                    showToast(I18n.t('toast.load_failed', {context: '时间线论文列表', reason: err.message}), 'error');
                }
            };

            const updateTimelineUrl = () => {
                window.location.hash = '#/timeline' + Utils.buildQueryString({
                    year_from: currentRange.year_from,
                    year_to: currentRange.year_to
                });
            };

            await loadTimeline();
        } catch (err) {
            console.error('[timeline] 时间线加载失败:', err);
            chartEl.innerHTML = `<div class="empty-state">${I18n.t('toast.load_failed', {context: '时间线', reason: err.message})}</div>`;
            showToast(I18n.t('toast.load_failed', {context: '时间线', reason: err.message}), 'error');
        }
    }

    // ------------------ 质量监控 ------------------
    async function renderQuality() {
        content.innerHTML = `
            <h2 style="margin-top:0;">质量监控面板</h2>
            <div id="quality-loading" class="loading-text">加载中...</div>
            <div id="quality-content" style="display:none;">
                <div class="quality-grid">
                    <div class="card" id="quality-coverage-card">
                        <h3 class="card-title">提取覆盖率</h3>
                        <div id="quality-coverage"></div>
                    </div>
                    <div class="card" id="quality-completeness-card">
                        <h3 class="card-title">字段完整率</h3>
                        <div id="quality-completeness"></div>
                    </div>
                    <div class="card" id="quality-score-card">
                        <h3 class="card-title">quality_score 分布</h3>
                        <div id="quality-score"></div>
                    </div>
                    <div class="card" id="quality-failures-card">
                        <h3 class="card-title">失败任务统计</h3>
                        <div id="quality-failures"></div>
                    </div>
                </div>
                <div class="card" style="margin-top:16px;">
                    <h3 class="card-title">Prompt A/B 测试对比</h3>
                    <div id="quality-prompt-compare"></div>
                </div>
                <div class="card" style="margin-top:16px;">
                    <h3 class="card-title">低质量论文列表 <span id="quality-low-threshold" style="font-size:0.85em;color:#888;"></span></h3>
                    <div id="quality-low-list"></div>
                </div>
            </div>
        `;

        try {
            const [stats, lowQuality, promptCompare] = await Promise.all([
                API.getQualityStats(),
                API.getQualityLowQuality({ threshold: 0.6, limit: 50 }),
                API.getQualityPromptCompare({})
            ]);

            document.getElementById('quality-loading').style.display = 'none';
            document.getElementById('quality-content').style.display = 'block';

            // 覆盖率
            const cov = stats.coverage;
            document.getElementById('quality-coverage').innerHTML = `
                <table class="data-table">
                    <thead><tr><th>提取类型</th><th>覆盖论文数</th><th>覆盖率</th></tr></thead>
                    <tbody>
                        <tr><td>知识卡片</td><td>${cov.knowledge_cards.count}</td><td>${cov.knowledge_cards.coverage}%</td></tr>
                        <tr><td>方法流程</td><td>${cov.methods.count}</td><td>${cov.methods.coverage}%</td></tr>
                        <tr><td>数据点</td><td>${cov.data_points.papers_count} (${cov.data_points.total_points} 条)</td><td>${cov.data_points.coverage}%</td></tr>
                    </tbody>
                </table>
                <p style="margin-top:8px;color:#888;font-size:0.85em;">总论文数（排除占位论文）：${stats.total_papers}</p>
            `;

            // 完整率
            const comp = stats.completeness;
            document.getElementById('quality-completeness').innerHTML = `
                <table class="data-table">
                    <thead><tr><th>字段</th><th>非空数量</th><th>完整率</th></tr></thead>
                    <tbody>
                        <tr><td>key_claims</td><td>${comp.has_key_claims.count}</td><td>${comp.has_key_claims.rate}%</td></tr>
                        <tr><td>core_answer</td><td>${comp.has_core_answer.count}</td><td>${comp.has_core_answer.rate}%</td></tr>
                    </tbody>
                </table>
            `;

            // quality_score 分布
            const dist = stats.quality_score.distribution;
            const avg = stats.quality_score.average;
            const scoreTiers = [
                { key: 'excellent', label: '优秀 (≥0.8)', count: dist.excellent || 0, color: '#22c55e' },
                { key: 'good', label: '良好 (0.6-0.8)', count: dist.good || 0, color: '#3b82f6' },
                { key: 'medium', label: '中等 (0.4-0.6)', count: dist.medium || 0, color: '#f59e0b' },
                { key: 'low', label: '低 (<0.4)', count: dist.low || 0, color: '#ef4444' },
                { key: 'null', label: '未评分', count: dist.null || 0, color: '#9ca3af' },
            ];
            const totalScored = scoreTiers.reduce((s, t) => s + t.count, 0);
            document.getElementById('quality-score').innerHTML = `
                <p style="margin:0 0 12px 0;font-size:0.9em;">${I18n.t('quality.score')}: <strong>${avg !== null ? avg : I18n.t('common.no_data')}</strong></p>
                <table class="data-table">
                    <thead><tr><th>等级</th><th>数量</th><th>占比</th><th>分布</th></tr></thead>
                    <tbody>
                        ${scoreTiers.map(t => `
                            <tr>
                                <td><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${t.color};margin-right:6px;"></span>${t.label}</td>
                                <td>${t.count}</td>
                                <td>${totalScored ? (t.count / totalScored * 100).toFixed(1) : 0}%</td>
                                <td><div style="background:#eee;border-radius:4px;height:16px;width:120px;display:inline-block;vertical-align:middle;">
                                    <div style="background:${t.color};height:100%;border-radius:4px;width:${totalScored ? (t.count / totalScored * 100) : 0}%;"></div>
                                </div></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;

            // 失败任务
            const failures = stats.failures || [];
            if (failures.length) {
                document.getElementById('quality-failures').innerHTML = `
                    <table class="data-table">
                        <thead><tr><th>阶段</th><th>错误类别</th><th>数量</th></tr></thead>
                        <tbody>${failures.map(f => `<tr><td>${f.stage}</td><td>${f.error_class || I18n.t('paper.meta.unknown')}</td><td>${f.c}</td></tr>`).join('')}</tbody>
                    </table>
                `;
            } else {
                document.getElementById('quality-failures').innerHTML = '<div class="empty-state">暂无失败任务</div>';
            }

            // Prompt A/B 对比
            const versions = promptCompare.versions || [];
            if (versions.length) {
                document.getElementById('quality-prompt-compare').innerHTML = `
                    <table class="data-table">
                        <thead><tr><th>Prompt 版本</th><th>论文数</th><th>已评分</th><th>未评分</th><th>平均分</th><th>最低分</th><th>最高分</th><th>通过率 (≥0.6)</th></tr></thead>
                        <tbody>${versions.map(v => `
                            <tr>
                                <td><code>${v.version}</code></td>
                                <td>${v.count}</td>
                                <td>${v.scored_count || 0}</td>
                                <td>${v.unscored_count || 0}</td>
                                <td>${v.avg_score !== null ? v.avg_score : '-'}</td>
                                <td>${v.min_score !== null ? v.min_score : '-'}</td>
                                <td>${v.max_score !== null ? v.max_score : '-'}</td>
                                <td>${v.pass_rate}%</td>
                            </tr>
                        `).join('')}</tbody>
                    </table>
                `;
            } else {
                document.getElementById('quality-prompt-compare').innerHTML = '<div class="empty-state">暂无多版本数据，需使用不同 prompt_version 提取后对比</div>';
            }

            // 低质量论文列表
            const thresholdText = lowQuality.include_unscored 
                ? `(阈值 < ${lowQuality.threshold} 或未评分)` 
                : `(阈值 < ${lowQuality.threshold})`;
            document.getElementById('quality-low-threshold').textContent = thresholdText;
            
            const lowPapers = lowQuality.papers || [];
            if (lowPapers.length) {
                // 统计未评分和低质量数量
                const unscoredCount = lowPapers.filter(p => p.quality_score === null || p.quality_score === undefined).length;
                const lowCount = lowPapers.length - unscoredCount;
                
                document.getElementById('quality-low-list').innerHTML = `
                    <table class="data-table">
                        <thead><tr><th>论文ID</th><th>标题</th><th>期刊</th><th>质量分</th><th>Prompt版本</th><th>操作</th></tr></thead>
                        <tbody>${lowPapers.map(p => {
                            const isUnscored = p.quality_score === null || p.quality_score === undefined;
                            const scoreDisplay = isUnscored 
                                ? '<span style="color:#9ca3af;font-weight:600;">未评分</span>'
                                : `<span style="color:#ef4444;font-weight:600;">${p.quality_score}</span>`;
                            return `
                                <tr>
                                    <td>${p.paper_id}</td>
                                    <td><a href="#/paper/${p.paper_id}" style="color:#3b82f6;text-decoration:none;">${(p.title || '').slice(0, 60)}${(p.title || '').length > 60 ? '...' : ''}</a></td>
                                    <td>${p.journal || '-'}</td>
                                    <td>${scoreDisplay}</td>
                                    <td><code>${p.prompt_version || '-'}</code></td>
                                    <td><button class="btn btn-secondary btn-sm" onclick="qualityReExtract(${p.paper_id})">重新提取</button></td>
                                </tr>
                            `;
                        }).join('')}</tbody>
                    </table>
                    <p style="margin-top:8px;color:#888;font-size:0.85em;">
                        共 ${lowQuality.total} 篇论文（低质量 ${lowCount} 篇，未评分 ${unscoredCount} 篇）
                    </p>
                `;
            } else {
                document.getElementById('quality-low-list').innerHTML = '<div class="empty-state">暂无低质量论文</div>';
            }
        } catch (err) {
            document.getElementById('quality-loading').innerHTML = `<div class="empty-state">${I18n.t('common.load_failed')}: ${err.message}</div>`;
            console.error('[quality] 加载失败:', err);
        }
    }

    // 全局函数：一键重新提取
    window.qualityReExtract = async function(paperId) {
        if (!confirm(`确认重新提取论文 ${paperId} 的知识卡片？`)) return;
        try {
            const result = await API.reExtract(paperId);
            showToast(`已提交重新提取任务 (task_id: ${result.task_id})`, 'success');
        } catch (err) {
            showToast(`重新提取失败: ${err.message}`, 'error');
        }
    };

    // ------------------ Modal ------------------
    function initModal() {
        document.getElementById('modal-close').addEventListener('click', closeModal);
        document.getElementById('modal-overlay').addEventListener('click', e => {
            if (e.target.id === 'modal-overlay') closeModal();
        });
    }

    function openModal(title, bodyHtml) {
        document.getElementById('modal-title').textContent = title;
        document.getElementById('modal-body').innerHTML = bodyHtml;
        document.getElementById('modal-overlay').classList.remove('hidden');
    }

    function closeModal() {
        document.getElementById('modal-overlay').classList.add('hidden');
    }

    // ------------------ 设置页面 ------------------
    // 统一 localStorage key 命名空间
    const UI_PREFS_KEY = 'litre_sys_ui_prefs_v1';

    // 默认 UI 偏好
    function getDefaultUIPrefs() {
        return {
            // 视图偏好
            default_view: 'dashboard',           // 进入系统时的默认页
            paper_default_tab: 'knowledge',      // 论文详情页默认 tab
            knowledge_compact: false,            // 知识卡片紧凑模式
            network_layout: 'force',             // 关系网络布局：force / circle / hierarchical
            network_node_size: 'normal',         // 关系网络节点尺寸：small / normal / large
            // 检索偏好
            search_default_mode: 'keyword',      // 检索默认模式
            search_results_per_page: 20,         // 每页条数
            fts_weight: 0.4,                     // 全文检索权重
            vector_weight: 0.6,                  // 向量检索权重
            highlight_keywords: true,            // 高亮关键词
            // 数据展示
            page_size: 20,                       // 列表默认分页大小
            show_empty_state: true,              // 显示空状态提示
            enable_animations: true,             // 启用交互动画
            density: 'comfortable',              // 列表密度：compact / comfortable / loose
            // 通知与提示
            show_toast_duration: 3,              // 提示显示秒数
            // 高级
            confirm_destructive: true,           // 危险操作前确认
            auto_refresh_dashboard: false,       // 仪表盘自动刷新
            dashboard_refresh_interval: 30       // 自动刷新间隔(秒)
        };
    }

    function loadUIPrefs() {
        try {
            const raw = localStorage.getItem(UI_PREFS_KEY);
            if (!raw) return getDefaultUIPrefs();
            const parsed = JSON.parse(raw);
            return Object.assign(getDefaultUIPrefs(), parsed);
        } catch (e) {
            return getDefaultUIPrefs();
        }
    }

    function saveUIPrefs(prefs) {
        try {
            localStorage.setItem(UI_PREFS_KEY, JSON.stringify(prefs));
            return true;
        } catch (e) {
            showToast('保存 UI 偏好失败: ' + e.message, 'error');
            return false;
        }
    }

    // 全局读取 UI 偏好的工具（其它模块可调用）
    window.UIPrefs = {
        get: loadUIPrefs,
        set: saveUIPrefs,
        getDefault: getDefaultUIPrefs
    };

    async function renderSettings() {
        content.innerHTML = `
            <h2 style="margin-top:0;">设置</h2>
            <p style="color:var(--text-secondary);font-size:13px;margin-top:0;">个性化界面偏好，并集中管理工作流相关配置。修改后点击"保存"即可生效。</p>
            <div class="settings-layout">
                <aside class="settings-nav" id="settings-nav">
                    <div class="settings-nav-section">
                        <div class="settings-nav-title">界面偏好</div>
                        <a class="settings-nav-item active" href="#/settings?cat=view" data-cat="view">
                            <span class="icon">◐</span> 视图偏好
                        </a>
                        <a class="settings-nav-item" href="#/settings?cat=search" data-cat="search">
                            <span class="icon">⌕</span> 检索偏好
                        </a>
                        <a class="settings-nav-item" href="#/settings?cat=display" data-cat="display">
                            <span class="icon">▤</span> 数据展示
                        </a>
                        <a class="settings-nav-item" href="#/settings?cat=notification" data-cat="notification">
                            <span class="icon">◔</span> 通知与提示
                        </a>
                        <a class="settings-nav-item" href="#/settings?cat=advanced" data-cat="advanced">
                            <span class="icon">⚙</span> 高级
                        </a>
                    </div>
                    <div class="settings-nav-section">
                        <div class="settings-nav-title">系统配置</div>
                        <a class="settings-nav-item" href="#/settings?cat=workflow" data-cat="workflow">
                            <span class="icon">⚙</span> 工作流配置
                        </a>
                        <a class="settings-nav-item" href="#/settings?cat=about" data-cat="about">
                            <span class="icon">ⓘ</span> 关于
                        </a>
                    </div>
                </aside>
                <div class="settings-content" id="settings-content">
                    <div class="loading-text">${I18n.t('common.loading')}</div>
                </div>
            </div>
        `;

        // 解析 ?cat= 参数
        const hash = window.location.hash || '';
        const qs = hash.split('?')[1] || '';
        const params = parseQuery(qs);
        const initialCat = params.cat || 'view';

        // 绑定左侧导航
        const navItems = document.querySelectorAll('#settings-nav .settings-nav-item');
        navItems.forEach(item => {
            item.addEventListener('click', e => {
                e.preventDefault();
                const cat = item.dataset.cat;
                // 更新 hash，触发路由刷新
                window.location.hash = '#/settings?cat=' + cat;
            });
        });

        await renderSettingsCategory(initialCat);
    }

    // 根据分类渲染右侧内容
    async function renderSettingsCategory(cat) {
        const root = document.getElementById('settings-content');
        if (!root) return;
        // 同步左侧激活状态
        document.querySelectorAll('#settings-nav .settings-nav-item').forEach(el => {
            el.classList.toggle('active', el.dataset.cat === cat);
        });

        const prefs = loadUIPrefs();

        if (cat === 'view') {
            root.innerHTML = `
                <div class="card">
                    <h3 class="card-title">视图偏好</h3>
                    <p class="settings-hint">控制默认进入页面、详情页默认标签、关系网络等视图选项。</p>
                    <div class="settings-form">
                        <div class="form-field">
                            <label for="ui-default-view">进入系统默认页</label>
                            <select id="ui-default-view">
                                <option value="dashboard">仪表盘</option>
                                <option value="search">检索</option>
                                <option value="knowledgebase">知识库</option>
                                <option value="timeline">时间线</option>
                                <option value="network">关系网络</option>
                            </select>
                        </div>
                        <div class="form-field">
                            <label for="ui-paper-tab">论文详情默认 Tab</label>
                            <select id="ui-paper-tab">
                                <option value="knowledge">知识卡片</option>
                                <option value="summary">摘要</option>
                                <option value="methods">方法流程</option>
                                <option value="data">数据点</option>
                                <option value="citations">引用</option>
                            </select>
                        </div>
                        <div class="form-field checkbox">
                            <label><input type="checkbox" id="ui-compact"> 知识卡片紧凑模式（缩小内边距与字号）</label>
                        </div>
                        <div class="form-field">
                            <label for="ui-network-layout">关系网络默认布局</label>
                            <select id="ui-network-layout">
                                <option value="force">力导向</option>
                                <option value="circle">环形</option>
                                <option value="hierarchical">分层</option>
                            </select>
                        </div>
                        <div class="form-field">
                            <label for="ui-network-size">关系网络节点尺寸</label>
                            <select id="ui-network-size">
                                <option value="small">小</option>
                                <option value="normal">标准</option>
                                <option value="large">大</option>
                            </select>
                        </div>
                    </div>
                </div>
            `;
            bindUIForm(root, prefs, {
                'default_view': 'ui-default-view',
                'paper_default_tab': 'ui-paper-tab',
                'knowledge_compact': 'ui-compact',
                'network_layout': 'ui-network-layout',
                'network_node_size': 'ui-network-size'
            });
        } else if (cat === 'search') {
            root.innerHTML = `
                <div class="card">
                    <h3 class="card-title">检索偏好</h3>
                    <p class="settings-hint">设置默认检索模式、每页条数与混合检索权重。</p>
                    <div class="settings-form">
                        <div class="form-field">
                            <label for="ui-search-mode">默认检索模式</label>
                            <select id="ui-search-mode">
                                <option value="keyword">关键词</option>
                                <option value="semantic">语义</option>
                                <option value="hybrid">混合</option>
                            </select>
                        </div>
                        <div class="form-field">
                            <label for="ui-search-page-size">每页条数</label>
                            <input type="number" id="ui-search-page-size" min="5" max="100" step="5">
                        </div>
                        <div class="form-field">
                            <label for="ui-fts-weight">全文检索权重（向量权重 = 1 - 该值）</label>
                            <input type="number" id="ui-fts-weight" min="0" max="1" step="0.1">
                        </div>
                        <div class="form-field checkbox">
                            <label><input type="checkbox" id="ui-highlight"> 在结果中高亮关键词</label>
                        </div>
                    </div>
                </div>
            `;
            bindUIForm(root, prefs, {
                'search_default_mode': 'ui-search-mode',
                'search_results_per_page': 'ui-search-page-size',
                'fts_weight': 'ui-fts-weight',
                'highlight_keywords': 'ui-highlight'
            });
        } else if (cat === 'display') {
            root.innerHTML = `
                <div class="card">
                    <h3 class="card-title">数据展示</h3>
                    <p class="settings-hint">列表分页、密度、动画与空状态等展示选项。</p>
                    <div class="settings-form">
                        <div class="form-field">
                            <label for="ui-page-size">列表默认分页大小</label>
                            <input type="number" id="ui-page-size" min="5" max="100" step="5">
                        </div>
                        <div class="form-field">
                            <label for="ui-density">列表密度</label>
                            <select id="ui-density">
                                <option value="compact">紧凑</option>
                                <option value="comfortable">舒适</option>
                                <option value="loose">宽松</option>
                            </select>
                        </div>
                        <div class="form-field checkbox">
                            <label><input type="checkbox" id="ui-show-empty"> 显示空状态提示</label>
                        </div>
                        <div class="form-field checkbox">
                            <label><input type="checkbox" id="ui-animations"> 启用交互动画（卡片悬浮、过渡等）</label>
                        </div>
                    </div>
                </div>
            `;
            bindUIForm(root, prefs, {
                'page_size': 'ui-page-size',
                'density': 'ui-density',
                'show_empty_state': 'ui-show-empty',
                'enable_animations': 'ui-animations'
            });
        } else if (cat === 'notification') {
            root.innerHTML = `
                <div class="card">
                    <h3 class="card-title">通知与提示</h3>
                    <p class="settings-hint">控制 Toast 提示的显示时长。</p>
                    <div class="settings-form">
                        <div class="form-field">
                            <label for="ui-toast-duration">Toast 显示时长（秒）</label>
                            <input type="number" id="ui-toast-duration" min="1" max="30" step="1">
                        </div>
                    </div>
                </div>
            `;
            bindUIForm(root, prefs, {
                'show_toast_duration': 'ui-toast-duration'
            });
        } else if (cat === 'advanced') {
            root.innerHTML = `
                <div class="card">
                    <h3 class="card-title">高级</h3>
                    <p class="settings-hint">危险操作确认、自动刷新等高级选项。</p>
                    <div class="settings-form">
                        <div class="form-field checkbox">
                            <label><input type="checkbox" id="ui-confirm-destructive"> 危险操作前弹出确认（如删除、归档）</label>
                        </div>
                        <div class="form-field checkbox">
                            <label><input type="checkbox" id="ui-auto-refresh"> 仪表盘自动刷新</label>
                        </div>
                        <div class="form-field">
                            <label for="ui-refresh-interval">自动刷新间隔（秒）</label>
                            <input type="number" id="ui-refresh-interval" min="5" max="600" step="5">
                        </div>
                        <div class="form-field" style="margin-top:18px;">
                            <button class="btn btn-secondary" id="ui-reset-prefs">恢复默认设置</button>
                            <button class="btn btn-primary" id="ui-save-prefs">保存偏好</button>
                            <span id="ui-save-status" style="margin-left:12px;font-size:13px;color:var(--text-secondary);"></span>
                        </div>
                    </div>
                </div>
            `;
            bindUIForm(root, prefs, {
                'confirm_destructive': 'ui-confirm-destructive',
                'auto_refresh_dashboard': 'ui-auto-refresh',
                'dashboard_refresh_interval': 'ui-refresh-interval'
            });
            document.getElementById('ui-reset-prefs').addEventListener('click', () => {
                if (!confirm('确定要恢复所有 UI 偏好的默认设置吗？')) return;
                saveUIPrefs(getDefaultUIPrefs());
                showToast('已恢复默认偏好', 'success');
                renderSettingsCategory('advanced');
            });
        } else if (cat === 'workflow') {
            // 工作流配置：复用 workflow 页面结构
            await renderSettingsWorkflow();
            return;
        } else if (cat === 'about') {
            root.innerHTML = `
                <div class="card">
                    <h3 class="card-title">关于</h3>
                    <div class="about-info">
                        <div class="about-row"><span class="about-label">系统名称</span><span class="about-value">文献系统</span></div>
                        <div class="about-row"><span class="about-label">版本</span><span class="about-value">v1.0.0</span></div>
                        <div class="about-row"><span class="about-label">构建日期</span><span class="about-value">2026-08-02</span></div>
                        <div class="about-row"><span class="about-label">前端</span><span class="about-value">原生 JavaScript + Chart.js + vis-network</span></div>
                        <div class="about-row"><span class="about-label">后端</span><span class="about-value">Koa 2.x + SQLite + sqlite-vec</span></div>
                        <div class="about-row"><span class="about-label">LLM</span><span class="about-value">通过 /workflow/settings 配置</span></div>
                    </div>
                </div>
                <div class="card">
                    <h3 class="card-title">数据说明</h3>
                    <ul class="about-list">
                        <li>UI 偏好保存在浏览器 localStorage（<code>litre_sys_ui_prefs_v1</code>），不会上传服务器。</li>
                        <li>工作流配置保存于 <code>workflow_settings</code> 表，API Key 仅显示前 4 位。</li>
                        <li>如需重置全部设置，请清除浏览器 localStorage 并重启服务。</li>
                    </ul>
                </div>
            `;
            return;
        }

        // 通用：除"高级"和"关于"和"工作流"外，自动绑定"保存"按钮（如有）
        const saveBtn = document.getElementById('ui-save-prefs');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                collectAndSaveUIPrefs(cat);
            });
        }
    }

    // 表单绑定：将 prefs 写入对应表单元素，并注册 input 事件即时更新
    function bindUIForm(root, prefs, map) {
        Object.entries(map).forEach(([key, elId]) => {
            const el = document.getElementById(elId);
            if (!el) return;
            const v = prefs[key];
            if (el.type === 'checkbox') {
                el.checked = !!v;
            } else {
                el.value = v !== undefined && v !== null ? v : '';
            }
        });

        // 通用保存按钮
        const saveBtn = document.getElementById('ui-save-prefs');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => collectAndSaveUIPrefs());
        }
    }

    // 从表单收集并保存
    function collectAndSaveUIPrefs(cat) {
        // 收集所有 UI 偏好表单元素
        const map = {
            'default_view': 'ui-default-view',
            'paper_default_tab': 'ui-paper-tab',
            'knowledge_compact': 'ui-compact',
            'network_layout': 'ui-network-layout',
            'network_node_size': 'ui-network-size',
            'search_default_mode': 'ui-search-mode',
            'search_results_per_page': 'ui-search-page-size',
            'fts_weight': 'ui-fts-weight',
            'highlight_keywords': 'ui-highlight',
            'page_size': 'ui-page-size',
            'density': 'ui-density',
            'show_empty_state': 'ui-show-empty',
            'enable_animations': 'ui-animations',
            'show_toast_duration': 'ui-toast-duration',
            'confirm_destructive': 'ui-confirm-destructive',
            'auto_refresh_dashboard': 'ui-auto-refresh',
            'dashboard_refresh_interval': 'ui-refresh-interval'
        };
        const prefs = loadUIPrefs();
        Object.entries(map).forEach(([key, elId]) => {
            const el = document.getElementById(elId);
            if (!el) return;
            if (el.type === 'checkbox') {
                prefs[key] = el.checked;
            } else if (el.type === 'number') {
                const n = parseFloat(el.value);
                prefs[key] = isNaN(n) ? prefs[key] : n;
            } else {
                prefs[key] = el.value;
            }
        });
        if (saveUIPrefs(prefs)) {
            showToast('设置已保存', 'success');
        }
    }

    // 工作流配置：复用后端 API
    async function renderSettingsWorkflow() {
        const root = document.getElementById('settings-content');
        if (!root) return;
        root.innerHTML = `<div class="loading-text">加载配置中...</div>`;
        let settings = {};
        try {
            settings = await API.getWorkflowSettings();
        } catch (err) {
            root.innerHTML = `<div class="empty-state">加载配置失败: ${Utils.escapeHtml(err.message)}</div>`;
            return;
        }
        // API key 脱敏：仅前 4 位可见
        const maskKey = (v) => {
            if (!v) return '';
            const s = String(v);
            if (s.length <= 4) return '****';
            return s.slice(0, 4) + '*'.repeat(Math.max(4, s.length - 4));
        };
        const masked = { ...settings };
        ['semantic_scholar_api_key', 'mineru_api_key', 'llm_api_key', 'embedding_api_key', 'wos_api_key', 'scopus_api_keys'].forEach(k => {
            masked[k] = maskKey(settings[k]);
        });

        const sources = settings.collect_sources || ['crossref'];
        const val = (k, d = '') => (masked[k] !== undefined && masked[k] !== null ? masked[k] : d);

        root.innerHTML = `
            <div class="card">
                <h3 class="card-title">工作流配置（API & 策略）</h3>
                <p class="settings-hint">与"工作流"页面的"工作流配置"区域一致。修改后保存即生效；API Key 仅显示前 4 位以避免泄露。</p>
                <div class="settings-form">
                    <h4 class="settings-form-section-title">采集源</h4>
                    <div class="settings-grid">
                        <div class="form-field checkbox">
                            <label><input type="checkbox" id="cfg-source-crossref" ${sources.includes('crossref') ? 'checked' : ''}> Crossref</label>
                            <label style="margin-left:18px;"><input type="checkbox" id="cfg-source-semantic_scholar" ${sources.includes('semantic_scholar') ? 'checked' : ''}> Semantic Scholar</label>
                        </div>
                    </div>
                    <h4 class="settings-form-section-title">API Keys</h4>
                    <div class="settings-grid">
                        <div class="form-field"><label>Semantic Scholar API Key（可选）</label><input type="password" id="cfg-semantic_scholar_api_key" value="${Utils.escapeHtml(val('semantic_scholar_api_key'))}"></div>
                        <div class="form-field"><label>MinerU API Key（必填）</label><input type="password" id="cfg-mineru_api_key" value="${Utils.escapeHtml(val('mineru_api_key'))}"></div>
                        <div class="form-field"><label>LLM API Key（必填）</label><input type="password" id="cfg-llm_api_key" value="${Utils.escapeHtml(val('llm_api_key'))}"></div>
                        <div class="form-field"><label>Embedding API Key（必填）</label><input type="password" id="cfg-embedding_api_key" value="${Utils.escapeHtml(val('embedding_api_key'))}"></div>
                        <div class="form-field"><label>Web of Science API Key（可选）</label><input type="password" id="cfg-wos_api_key" value="${Utils.escapeHtml(val('wos_api_key'))}"></div>
                        <div class="form-field"><label>Scopus API Keys（可选，逗号分隔）</label><input type="password" id="cfg-scopus_api_keys" value="${Utils.escapeHtml(val('scopus_api_keys'))}"></div>
                    </div>
                    <h4 class="settings-form-section-title">PDF 下载策略优先级</h4>
                    <p class="settings-hint">数字越小越优先，0=禁用</p>
                    <div class="settings-grid">
                        <div class="form-field"><label>Crossref Text Mining</label><input type="number" min="0" max="9" id="cfg-pdf_strategy_crossref_text_mining" value="${val('pdf_strategy_crossref_text_mining', 0)}"></div>
                        <div class="form-field"><label>Crossref PDF</label><input type="number" min="0" max="9" id="cfg-pdf_strategy_crossref_pdf" value="${val('pdf_strategy_crossref_pdf', 0)}"></div>
                        <div class="form-field"><label>OA URL 直接下载</label><input type="number" min="0" max="9" id="cfg-pdf_strategy_oa_url" value="${val('pdf_strategy_oa_url', 0)}"></div>
                        <div class="form-field"><label>DOI 重定向</label><input type="number" min="0" max="9" id="cfg-pdf_strategy_doi_redirect" value="${val('pdf_strategy_doi_redirect', 0)}"></div>
                        <div class="form-field"><label>Unpaywall</label><input type="number" min="0" max="9" id="cfg-pdf_strategy_unpaywall" value="${val('pdf_strategy_unpaywall', 0)}"></div>
                    </div>
                    <h4 class="settings-form-section-title">LLM 提炼参数</h4>
                    <div class="settings-grid">
                        <div class="form-field wide"><label>LLM Base URL</label><input type="text" id="cfg-llm_base_url" value="${Utils.escapeHtml(val('llm_base_url'))}"></div>
                        <div class="form-field"><label>模型</label><input type="text" id="cfg-llm_model" value="${Utils.escapeHtml(val('llm_model'))}"></div>
                        <div class="form-field"><label>Max Tokens</label><input type="number" min="1" id="cfg-llm_max_tokens" value="${val('llm_max_tokens', 4096)}"></div>
                        <div class="form-field"><label>Temperature</label><input type="number" step="0.1" min="0" max="2" id="cfg-llm_temperature" value="${val('llm_temperature', 0.2)}"></div>
                        <div class="form-field"><label>Timeout（秒）</label><input type="number" min="1" id="cfg-llm_request_timeout" value="${val('llm_request_timeout', 300)}"></div>
                        <div class="form-field"><label>最大重试</label><input type="number" min="0" id="cfg-llm_max_retries" value="${val('llm_max_retries', 3)}"></div>
                    </div>
                    <h4 class="settings-form-section-title">Embedding 参数</h4>
                    <div class="settings-grid">
                        <div class="form-field wide"><label>Embedding Base URL</label><input type="text" id="cfg-embedding_base_url" value="${Utils.escapeHtml(val('embedding_base_url'))}"></div>
                        <div class="form-field"><label>模型</label><input type="text" id="cfg-embedding_model" value="${Utils.escapeHtml(val('embedding_model'))}"></div>
                        <div class="form-field"><label>维度</label><input type="number" min="1" id="cfg-embedding_dim" value="${val('embedding_dim', 1536)}"></div>
                        <div class="form-field"><label>Batch Size</label><input type="number" min="1" id="cfg-embedding_batch_size" value="${val('embedding_batch_size', 32)}"></div>
                    </div>
                    <div style="margin-top:18px;">
                        <button class="btn btn-primary" id="cfg-save">保存配置</button>
                        <span id="cfg-save-status" style="margin-left:12px;font-size:13px;color:var(--text-secondary);"></span>
                    </div>
                </div>
            </div>
        `;

        document.getElementById('cfg-save').addEventListener('click', async () => {
            const statusEl = document.getElementById('cfg-save-status');
            const data = {
                collect_sources: [
                    ...(document.getElementById('cfg-source-crossref').checked ? ['crossref'] : []),
                    ...(document.getElementById('cfg-source-semantic_scholar').checked ? ['semantic_scholar'] : [])
                ],
                semantic_scholar_api_key: document.getElementById('cfg-semantic_scholar_api_key').value,
                mineru_api_key: document.getElementById('cfg-mineru_api_key').value,
                llm_api_key: document.getElementById('cfg-llm_api_key').value,
                embedding_api_key: document.getElementById('cfg-embedding_api_key').value,
                wos_api_key: document.getElementById('cfg-wos_api_key').value,
                scopus_api_keys: document.getElementById('cfg-scopus_api_keys').value,
                pdf_strategy_crossref_text_mining: parseInt(document.getElementById('cfg-pdf_strategy_crossref_text_mining').value, 10) || 0,
                pdf_strategy_crossref_pdf: parseInt(document.getElementById('cfg-pdf_strategy_crossref_pdf').value, 10) || 0,
                pdf_strategy_oa_url: parseInt(document.getElementById('cfg-pdf_strategy_oa_url').value, 10) || 0,
                pdf_strategy_doi_redirect: parseInt(document.getElementById('cfg-pdf_strategy_doi_redirect').value, 10) || 0,
                pdf_strategy_unpaywall: parseInt(document.getElementById('cfg-pdf_strategy_unpaywall').value, 10) || 0,
                llm_base_url: document.getElementById('cfg-llm_base_url').value,
                llm_model: document.getElementById('cfg-llm_model').value,
                llm_max_tokens: parseInt(document.getElementById('cfg-llm_max_tokens').value, 10) || 4096,
                llm_temperature: parseFloat(document.getElementById('cfg-llm_temperature').value) || 0.2,
                llm_request_timeout: parseInt(document.getElementById('cfg-llm_request_timeout').value, 10) || 300,
                llm_max_retries: parseInt(document.getElementById('cfg-llm_max_retries').value, 10) || 3,
                embedding_base_url: document.getElementById('cfg-embedding_base_url').value,
                embedding_model: document.getElementById('cfg-embedding_model').value,
                embedding_dim: parseInt(document.getElementById('cfg-embedding_dim').value, 10) || 1536,
                embedding_batch_size: parseInt(document.getElementById('cfg-embedding_batch_size').value, 10) || 32
            };
            statusEl.textContent = '保存中...';
            try {
                await API.setWorkflowSettings(data);
                statusEl.textContent = '已保存';
                showToast('工作流配置已保存', 'success');
                setTimeout(() => { statusEl.textContent = ''; }, 2000);
            } catch (err) {
                statusEl.textContent = '保存失败';
                showToast('保存失败: ' + err.message, 'error');
            }
        });
    }

    // ------------------ Helpers ------------------
    function parseQuery(qs) {
        const params = {};
        if (!qs) return params;
        qs.split('&').forEach(part => {
            const idx = part.indexOf('=');
            const k = decodeURIComponent(idx > -1 ? part.slice(0, idx) : part);
            const v = decodeURIComponent(idx > -1 ? part.slice(idx + 1) : '');
            if (k) params[k] = v;
        });
        return params;
    }
})();
