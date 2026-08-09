// 可复用 UI 组件
const Components = {
    statCard(label, value) {
        return `<div class="card stat-card">
            <div class="value">${value}</div>
            <div class="label">${label}</div>
        </div>`;
    },

    renderFacets(aggregations, activeFilters, onFilter) {
        if (!aggregations || Object.keys(aggregations).length === 0) {
            return '<div class="empty-state">' + I18n.t('facet.no_data') + '</div>';
        }
        const facetNames = {
            year: I18n.t('facet.year'), journal: I18n.t('facet.journal'), language: I18n.t('facet.language'),
            source: I18n.t('facet.source'), author: I18n.t('facet.author'), keyword: I18n.t('facet.keyword')
        };
        let html = '';
        for (const [key, items] of Object.entries(aggregations)) {
            if (!items || !items.length) continue;
            html += `<div class="facet-group">
                <h4>${facetNames[key] || key}</h4>
                ${items.slice(0, 10).map(item => {
                    const isActive = activeFilters[key] === item.key;
                    return `<div class="facet-item ${isActive ? 'active' : ''}" data-facet="${key}" data-key="${Utils.escapeHtml(item.key)}">
                        <span>${Utils.escapeHtml(item.key)}</span>
                        <span class="count">${item.count}</span>
                    </div>`;
                }).join('')}
            </div>`;
        }
        // 绑定事件
        setTimeout(() => {
            document.querySelectorAll('.facet-item').forEach(el => {
                el.addEventListener('click', () => {
                    const facet = el.dataset.facet;
                    const key = el.dataset.key;
                    onFilter(facet, key);
                });
            });
        }, 0);
        return html;
    },

    renderSearchResult(hit, index) {
        const title = hit.title || I18n.t('common.no_title');
        const snippet = hit.abstract_snippet || '';
        const authors = Utils.joinAuthors(hit.authors);
        const pid = hit.paper_id || hit.id;
        const attrs = pid ? `data-paper-id="${pid}"` : '';
        return `<div class="result-card" ${attrs}>
            <div class="result-title">${title}</div>
            <div class="result-meta">
                <span>${hit.published_year || I18n.t('common.unknown_year')}</span>
                <span>${hit.journal || ''}</span>
                <span>${authors ? Utils.truncate(authors, 80) : ''}</span>
            </div>
            <div class="result-snippet">${snippet}</div>
        </div>`;
    },

    renderTabs(tabs, active, onChange) {
        // tabs: [{id, label}]
        let html = '<div class="tabs">';
        tabs.forEach(tab => {
            html += `<button class="tab ${tab.id === active ? 'active' : ''}" data-tab="${tab.id}">${tab.label}</button>`;
        });
        html += '</div>';
        setTimeout(() => {
            document.querySelectorAll('.tab').forEach(btn => {
                btn.addEventListener('click', () => onChange(btn.dataset.tab));
            });
        }, 0);
        return html;
    },

    renderKnowledge(knowledge) {
        if (!knowledge) return '<div class="empty-state">' + I18n.t('knowledge.no_card') + '</div>';
        const sections = [];

        // 1. 研究问题（蓝色）
        if (knowledge.research_question) {
            sections.push(this._renderKnowledgeSection({
                type: 'question',
                icon: '?',
                title: I18n.t('knowledge.research_question'),
                badge: 'Q',
                content: knowledge.research_question
            }));
        }

        // 2. 核心回答（绿色）
        if (knowledge.core_answer) {
            sections.push(this._renderKnowledgeSection({
                type: 'answer',
                icon: 'A',
                title: I18n.t('knowledge.core_answer'),
                badge: 'A',
                content: knowledge.core_answer
            }));
        }

        // 3. 关键主张（紫色）- 列表化
        if (knowledge.key_claims && Array.isArray(knowledge.key_claims) && knowledge.key_claims.length) {
            sections.push(this._renderKeyClaimsSection(knowledge.key_claims));
        }

        // 4. 证据产生（青色）
        if (knowledge.evidence_generation) {
            sections.push(this._renderKnowledgeSection({
                type: 'evidence-gen',
                icon: 'E',
                title: I18n.t('knowledge.evidence_generation'),
                badge: 'E',
                content: knowledge.evidence_generation
            }));
        }

        // 5. 边界（橙色 3 桶）— 动态 badge 显示条目数
        if (knowledge.boundaries) {
            const bTotal = this._countBoundaryItems(knowledge.boundaries);
            sections.push(this._renderBoundariesSection(knowledge.boundaries, bTotal));
        }

        // 6. 可复用启发（粉色 chip）— 动态 badge 显示条数
        if (knowledge.reusable_inspiration) {
            const iTotal = this._countInspirationItems(knowledge.reusable_inspiration);
            sections.push(this._renderInspirationSection(knowledge.reusable_inspiration, iTotal));
        }

        if (!sections.length) {
            return '<div class="empty-state">' + I18n.t('knowledge.no_card_text') + '</div>';
        }
        return `<div class="knowledge-container">${sections.join('')}</div>`;
    },

    // 统计边界总条数（用于 badge）
    _countBoundaryItems(b) {
        if (Array.isArray(b)) return b.length;
        if (typeof b === 'object' && b) {
            return Object.values(b).filter(v => Array.isArray(v)).reduce((s, v) => s + v.length, 0);
        }
        return typeof b === 'string' ? 1 : 0;
    },

    // 统计启发总条数（用于 badge）
    _countInspirationItems(i) {
        if (Array.isArray(i)) return i.length;
        if (typeof i === 'object' && i) {
            return Object.values(i).reduce((s, v) => {
                if (Array.isArray(v)) return s + v.length;
                if (typeof v === 'string') return s + 1;
                return s;
            }, 0);
        }
        return typeof i === 'string' ? i.split(/[;\n；]/).filter(Boolean).length : 0;
    },

    // 单类型知识板块
    _renderKnowledgeSection({ type, icon, title, badge, content }) {
        return `<div class="knowledge-section knowledge-section--${type}">
            <div class="knowledge-section-header">
                <span class="knowledge-section-icon">${icon}</span>
                <span class="knowledge-section-title">${title}</span>
                <span class="knowledge-section-badge">${badge}</span>
            </div>
            <div class="knowledge-content">${Utils.escapeHtml(content)}</div>
        </div>`;
    },

    // 关键主张列表
    _renderKeyClaimsSection(claims) {
        const cards = claims.map((c, i) => this._renderKeyClaimCard(c, i + 1)).join('');
        return `<div class="knowledge-section knowledge-section--claims">
            <div class="knowledge-section-header">
                <span class="knowledge-section-icon">★</span>
                <span class="knowledge-section-title">${I18n.t('knowledge.key_claims_title')}</span>
                <span class="knowledge-section-badge">${I18n.t('knowledge.items_count', {count: claims.length})}</span>
            </div>
            <div class="key-claim-list">${cards}</div>
        </div>`;
    },

    // 单个关键主张
    _renderKeyClaimCard(claim, num) {
        const source = (claim.source || claim.origin || 'author').toLowerCase();
        const sourceLabelMap = { author: I18n.t('knowledge.claim_source.author'), user: I18n.t('knowledge.claim_source.user'), llm: I18n.t('knowledge.claim_source.llm') };
        const sourceLabel = sourceLabelMap[source] || (source === 'user' ? I18n.t('knowledge.claim_source.user') : I18n.t('knowledge.claim_source.author'));
        const text = this._highlightNumerics(claim.claim || claim.text || '');

        const meta = [];
        if (claim.evidence) {
            meta.push(`<div class="key-claim-meta-row">
                <span class="key-claim-meta-label">${I18n.t('knowledge.claim_evidence')}</span>
                <span class="key-claim-meta-content evidence-content">${Utils.escapeHtml(claim.evidence)}</span>
            </div>`);
        }
        if (claim.condition) {
            meta.push(`<div class="key-claim-meta-row">
                <span class="key-claim-meta-label">${I18n.t('knowledge.claim_condition')}</span>
                <span class="key-claim-meta-content counter-content">${Utils.escapeHtml(claim.condition)}</span>
            </div>`);
        }
        if (claim.counter || claim.counter_evidence) {
            meta.push(`<div class="key-claim-meta-row">
                <span class="key-claim-meta-label">${I18n.t('knowledge.claim_counter')}</span>
                <span class="key-claim-meta-content counter-content">${Utils.escapeHtml(claim.counter || claim.counter_evidence)}</span>
            </div>`);
        }
        if (claim.anchor) {
            meta.push(`<div class="key-claim-meta-row">
                <span class="key-claim-meta-label">${I18n.t('knowledge.claim_anchor')}</span>
                <span class="key-claim-meta-content">${this._renderAnchor(claim.anchor)}</span>
            </div>`);
        }

        return `<div class="key-claim-card">
            <div class="key-claim-header">
                <span class="key-claim-num">${num}</span>
                <span class="key-claim-source-tag ${source === 'user' ? 'user' : 'author'}">${sourceLabel}</span>
            </div>
            <div class="key-claim-text">${text}</div>
            ${meta.length ? `<div class="key-claim-meta">${meta.join('')}</div>` : ''}
        </div>`;
    },

    // 高亮关键数值
    _highlightNumerics(text) {
        if (!text) return '';
        const escaped = Utils.escapeHtml(text);
        // 匹配：百分比 (12.3% / 12 %)、含单位的数字 (10 kg, 5.6 t/ha)、纯数字 (1,234 / 1.2 / 10)
        return escaped.replace(/(\d[\d,\.]*\s?(?:%|kg|t|g|ha|km|m|cm|mm|°C|°|head|heads|THS_HD|LU|LSU|year|years|yr|h|days?|months?)\b|\d[\d,\.]*%)/g,
            '<span class="numeric-highlight">$1</span>');
    },

    // 渲染锚点为可点击 pill
    _renderAnchor(anchor) {
        if (!anchor) return '';
        // anchor 可能是对象或数组
        if (Array.isArray(anchor)) {
            return anchor.map(a => this._renderSingleAnchor(a)).filter(Boolean).join('');
        }
        if (typeof anchor === 'object') {
            return this._renderSingleAnchor(anchor) || '';
        }
        // 字符串：尝试解析为 figure/section 锚点
        return this._renderSingleAnchor({ type: 'section', label: String(anchor) }) || '';
    },

    _renderSingleAnchor(a) {
        if (!a) return '';
        const type = a.type || a.kind || (a.figure_id || a.fig_label ? 'figure' : (a.section_id || a.section ? 'section' : 'ref'));
        let pillClass = 'anchor-pill';
        let icon = '🔗';
        let label = a.label || a.text || a.name || '';
        let offset = '';

        if (type === 'figure' || a.fig_label || a.figure_id) {
            pillClass += ' figure-pill';
            icon = '📊';
            label = label || a.fig_label || a.figure_id || '图';
        } else if (type === 'section' || a.section_id || a.section) {
            pillClass += ' section-pill';
            icon = '§';
            label = label || a.section || a.section_id || '章节';
        } else if (type === 'table') {
            pillClass += ' figure-pill';
            icon = '📋';
            label = label || a.table_label || '表';
        }

        if (a.page || a.page_start) {
            offset = ` <span class="anchor-offset">p.${a.page || a.page_start}</span>`;
        }

        const data = [];
        if (a.figure_id || a.fig_label) data.push(`data-figure="${Utils.escapeHtml(a.fig_label || a.figure_id)}"`);
        if (a.section_id) data.push(`data-section="${Utils.escapeHtml(a.section_id)}"`);
        if (a.page) data.push(`data-page="${a.page}"`);

        return `<span class="${pillClass}" ${data.join(' ')} title="跳转到证据">${icon} ${Utils.escapeHtml(label)}${offset}</span>`;
    },

    // 边界问题 3 桶布局
    _renderBoundariesSection(boundaries, totalCount) {
        let buckets = { acknowledged: [], result_shown: [], unconfirmed: [] };
        let bucketLabels = { acknowledged: I18n.t('knowledge.boundary_acknowledged'), result_shown: I18n.t('knowledge.boundary_result_shown'), unconfirmed: I18n.t('knowledge.boundary_unconfirmed') };

        // 优先匹配 3 桶语义结构（author_acknowledged / result_shown / unconfirmed）
        if (typeof boundaries === 'object' && !Array.isArray(boundaries)) {
            const ack = boundaries.author_acknowledged || boundaries.acknowledged || boundaries.作者承认;
            const res = boundaries.result_shown || boundaries.shown || boundaries.results_shown || boundaries.结果所示;
            const unc = boundaries.unconfirmed || boundaries.uncertain || boundaries.未确认;
            if (ack || res || unc) {
                buckets.acknowledged = ack || [];
                buckets.result_shown = res || [];
                buckets.unconfirmed = unc || [];
            } else {
                // 兼容时间/空间/方法学 3 桶
                buckets = {
                    acknowledged: boundaries.temporal || boundaries.time || boundaries.时间 || [],
                    result_shown: boundaries.spatial || boundaries.space || boundaries.region || boundaries.空间 || [],
                    unconfirmed: boundaries.methodological || boundaries.method || boundaries.方法 || []
                };
                bucketLabels = { acknowledged: I18n.t('knowledge.boundary_temporal'), result_shown: I18n.t('knowledge.boundary_spatial'), unconfirmed: I18n.t('knowledge.boundary_methodological') };
            }
        } else if (Array.isArray(boundaries)) {
            // 数组形式：按 category 归类
            boundaries.forEach(b => {
                const cat = (b.category || b.type || b.bucket || '').toLowerCase();
                if (cat.includes('ack') || cat.includes('承认') || cat.includes('limit')) {
                    buckets.acknowledged.push(b);
                } else if (cat.includes('result') || cat.includes('shown') || cat.includes('结果')) {
                    buckets.result_shown.push(b);
                } else if (cat.includes('unconfirm') || cat.includes('未确认') || cat.includes('uncertain')) {
                    buckets.unconfirmed.push(b);
                } else if (cat.includes('time') || cat.includes('temporal') || cat.includes('时') || cat.includes('期')) {
                    buckets.acknowledged.push(b);
                } else if (cat.includes('space') || cat.includes('region') || cat.includes('空') || cat.includes('地理')) {
                    buckets.result_shown.push(b);
                } else {
                    buckets.unconfirmed.push(b);
                }
            });
        } else if (typeof boundaries === 'string') {
            buckets.unconfirmed = [{ text: boundaries }];
        }

        const renderBucket = (key, icon, title, items) => {
            let body;
            if (items.length) {
                body = `<ul>${items.map(it => {
                    const text = typeof it === 'string' ? it : (it.text || it.description || it.content || JSON.stringify(it));
                    return `<li>${Utils.escapeHtml(text)}</li>`;
                }).join('')}</ul>`;
            } else {
                body = '<div class="boundary-bucket-empty">' + I18n.t('knowledge.boundary_empty') + '</div>';
            }
            return `<div class="boundary-bucket boundary-bucket--${key}">
                <div class="boundary-bucket-title">${icon} ${title} <span style="color:var(--text-secondary);font-weight:500;">(${items.length})</span></div>
                ${body}
            </div>`;
        };

        const badgeText = (totalCount !== undefined ? I18n.t('knowledge.items_count', {count: totalCount}) : 'B');
        return `<div class="knowledge-section knowledge-section--boundary">
            <div class="knowledge-section-header">
                <span class="knowledge-section-icon" style="background:var(--boundary);">!</span>
                <span class="knowledge-section-title">${I18n.t('knowledge.boundaries_title')}</span>
                <span class="knowledge-section-badge">${badgeText}</span>
            </div>
            <div class="boundaries-grid">
                ${renderBucket('acknowledged', '📋', bucketLabels.acknowledged, buckets.acknowledged)}
                ${renderBucket('result_shown', '📈', bucketLabels.result_shown, buckets.result_shown)}
                ${renderBucket('unconfirmed', '❓', bucketLabels.unconfirmed, buckets.unconfirmed)}
            </div>
        </div>`;
    },

    // 可复用启发 chip 布局
    _renderInspirationSection(inspiration, totalCount) {
        let chips = [];
        let isStructured = false;

        if (Array.isArray(inspiration)) {
            isStructured = true;
            inspiration.forEach(it => {
                const text = typeof it === 'string' ? it : (it.text || it.content || it.description || '');
                const type = (it && (it.type || it.category)) || 'general';
                if (text) chips.push({ type, text });
            });
        } else if (typeof inspiration === 'object') {
            // 启发可能是 {method: [], dataset: [], framework: []} 或单一对象
            const groups = inspiration;
            ['method', 'dataset', 'framework', 'metric', 'tool', 'methods', 'datasets', 'frameworks', 'metrics', 'tools'].forEach(k => {
                if (Array.isArray(groups[k])) {
                    isStructured = true;
                    groups[k].forEach(t => chips.push({ type: k.replace(/s$/, ''), text: typeof t === 'string' ? t : (t.text || JSON.stringify(t)) }));
                } else if (typeof groups[k] === 'string') {
                    isStructured = true;
                    chips.push({ type: k.replace(/s$/, ''), text: groups[k] });
                }
            });
            // 其它字段也尝试收集
            if (!isStructured) {
                Object.entries(groups).forEach(([k, v]) => {
                    if (typeof v === 'string') chips.push({ type: k, text: v });
                });
            }
        } else if (typeof inspiration === 'string') {
            // 按分号或换行拆分
            inspiration.split(/[;\n；]/).map(s => s.trim()).filter(Boolean).forEach(t => chips.push({ type: 'general', text: t }));
        }

        let body;
        if (chips.length) {
            const typeLabels = { method: I18n.t('knowledge.inspiration.method'), dataset: I18n.t('knowledge.inspiration.dataset'), framework: I18n.t('knowledge.inspiration.framework'), metric: I18n.t('knowledge.inspiration.metric'), tool: I18n.t('knowledge.inspiration.tool'), general: I18n.t('knowledge.inspiration.general') };
            body = `<div class="inspiration-chips">${chips.map(c => {
                const label = typeLabels[c.type] || c.type;
                return `<div class="inspiration-chip">
                    <span class="inspiration-chip-type">${Utils.escapeHtml(label)}</span>
                    <span class="inspiration-chip-content">${Utils.escapeHtml(c.text)}</span>
                </div>`;
            }).join('')}</div>`;
        } else {
            // 退化：直接展示 JSON
            body = `<pre style="font-size:12px;white-space:pre-wrap;background:var(--bg);padding:10px;border-radius:var(--radius-sm);">${Utils.escapeHtml(JSON.stringify(inspiration, null, 2))}</pre>`;
        }

        const badgeText = (totalCount !== undefined ? I18n.t('knowledge.items_count', {count: totalCount}) : 'I');
        return `<div class="knowledge-section knowledge-section--inspire">
            <div class="knowledge-section-header">
                <span class="knowledge-section-icon" style="background:var(--inspire);">💡</span>
                <span class="knowledge-section-title">${I18n.t('knowledge.reusable_title')}</span>
                <span class="knowledge-section-badge">${badgeText}</span>
            </div>
            ${body}
        </div>`;
    },

    renderMethods(methods) {
        if (!methods) return '<div class="empty-state">' + I18n.t('methods.no_data') + '</div>';
        let html = '';
        if (methods.methodology) {
            html += `<div class="claim-card"><div class="claim">${I18n.t('methods.methodology')}</div><div class="evidence">${Utils.escapeHtml(methods.methodology)}</div></div>`;
        }
        if (methods.workflow) {
            html += `<div class="claim-card"><div class="claim">${I18n.t('methods.workflow')}</div><pre style="font-size:12px;white-space:pre-wrap;">${Utils.escapeHtml(JSON.stringify(methods.workflow, null, 2))}</pre></div>`;
        }
        if (methods.data_sources) {
            html += `<div class="claim-card"><div class="claim">${I18n.t('methods.data_sources')}</div><pre style="font-size:12px;white-space:pre-wrap;">${Utils.escapeHtml(JSON.stringify(methods.data_sources, null, 2))}</pre></div>`;
        }
        if (methods.models_algorithms) {
            html += `<div class="claim-card"><div class="claim">${I18n.t('methods.models_algorithms')}</div><pre style="font-size:12px;white-space:pre-wrap;">${Utils.escapeHtml(JSON.stringify(methods.models_algorithms, null, 2))}</pre></div>`;
        }
        if (methods.evaluation_metrics) {
            html += `<div class="claim-card"><div class="claim">${I18n.t('methods.evaluation_metrics')}</div><pre style="font-size:12px;white-space:pre-wrap;">${Utils.escapeHtml(JSON.stringify(methods.evaluation_metrics, null, 2))}</pre></div>`;
        }
        return html;
    },

    renderDataPoints(data) {
        if (!data || !data.data_points || !data.data_points.length) {
            return '<div class="empty-state">' + I18n.t('datapoints.no_data') + '</div>';
        }
        let html = `<table class="data-table">
            <thead><tr>
                <th>${I18n.t('datapoints.metric')}</th><th>${I18n.t('datapoints.value')}</th><th>${I18n.t('datapoints.unit')}</th><th>${I18n.t('datapoints.context')}</th><th>${I18n.t('datapoints.page')}</th><th>${I18n.t('datapoints.confidence')}</th>
            </tr></thead><tbody>`;
        data.data_points.forEach(dp => {
            html += `<tr>
                <td>${Utils.escapeHtml(dp.metric_name || I18n.t('datapoints.unnamed'))}</td>
                <td>${dp.metric_value !== null ? dp.metric_value : ''}</td>
                <td>${Utils.escapeHtml(dp.unit || '')}</td>
                <td>${Utils.escapeHtml(Utils.truncate(dp.context || '', 80))}</td>
                <td>${dp.page || ''}</td>
                <td>${Utils.escapeHtml(dp.confidence || '')}</td>
            </tr>`;
        });
        html += '</tbody></table>';
        return html;
    },

    renderSections(sections) {
        if (!sections || !sections.length) return '<div class="empty-state">' + I18n.t('sections.no_data') + '</div>';
        return sections.map((s, i) => {
            const heading = s.heading || s.section_type || `章节 ${i + 1}`;
            const content = Utils.escapeHtml(s.content || '');
            return `<div class="section-item">
                <div class="section-heading" data-section="${i}">
                    <span>[${s.section_type || 'other'}] ${heading}</span>
                    <span>${s.page_start || ''}${s.page_end && s.page_end !== s.page_start ? '-' + s.page_end : ''}</span>
                </div>
                <div class="section-content" id="section-content-${i}" style="display:none;">${content}</div>
            </div>`;
        }).join('');
    },

    bindSectionToggles() {
        document.querySelectorAll('.section-heading').forEach(h => {
            h.addEventListener('click', () => {
                const idx = h.dataset.section;
                const el = document.getElementById('section-content-' + idx);
                el.style.display = el.style.display === 'none' ? 'block' : 'none';
            });
        });
    },

    // 知识卡片锚点 pill 点击 → 跳转到证据（章节/图表）
    bindAnchorPills() {
        document.querySelectorAll('.anchor-pill').forEach(pill => {
            pill.addEventListener('click', (e) => {
                e.stopPropagation();
                const figure = pill.dataset.figure;
                const section = pill.dataset.section;
                const page = pill.dataset.page;
                if (figure) {
                    // 切换到图表 tab 并定位
                    const figuresTab = document.querySelector('.tab[data-tab="figures"]');
                    if (figuresTab) figuresTab.click();
                    setTimeout(() => {
                        const target = Array.from(document.querySelectorAll('.result-card'))
                            .find(el => el.textContent.includes(figure));
                        if (target) {
                            target.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            target.style.transition = 'box-shadow 0.3s';
                            target.style.boxShadow = '0 0 0 3px var(--primary)';
                            setTimeout(() => { target.style.boxShadow = ''; }, 1500);
                        }
                    }, 80);
                } else if (section) {
                    // 切换到章节 tab 并展开
                    const sectionsTab = document.querySelector('.tab[data-tab="sections"]');
                    if (sectionsTab) sectionsTab.click();
                    setTimeout(() => {
                        const heading = Array.from(document.querySelectorAll('.section-heading'))
                            .find(el => el.textContent.includes(section));
                        if (heading) {
                            heading.click();
                            heading.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        }
                    }, 80);
                } else if (page) {
                    showToast(`锚点位于第 ${page} 页`, 'info');
                }
            });
        });
    },

    renderFigures(figures) {
        if (!figures || !figures.length) return '<div class="empty-state">' + I18n.t('figures.no_data') + '</div>';
        return figures.map(f => {
            const imgUrl = f.file_path ? `/static/${f.file_path}` : '';
            return `<div class="result-card" style="margin-bottom:12px;">
                <div class="result-title">${Utils.escapeHtml(f.fig_label || '')} (${f.fig_type || ''})</div>
                <div class="result-meta">${I18n.t('figures.page_label')}: ${f.page || I18n.t('figures.unknown_page')}</div>
                ${imgUrl ? `<img src="${imgUrl}" style="max-width:100%;max-height:300px;border:1px solid var(--border);border-radius:4px;margin:8px 0;" onerror="this.style.display='none'">` : ''}
                <div class="result-snippet">${Utils.escapeHtml(f.caption || '')}</div>
            </div>`;
        }).join('');
    },

    renderCitations(citations) {
        if (!citations || !citations.length) return '<div class="empty-state">' + I18n.t('citations.no_data') + '</div>';
        return `<table class="data-table">
            <thead><tr><th>年份</th><th>标题</th><th>作者</th><th>期刊</th><th>DOI</th></tr></thead>
            <tbody>${citations.map(c => `<tr>
                <td>${Utils.escapeHtml(c.cited_year || '')}</td>
                <td>${Utils.escapeHtml(c.cited_title || '')}</td>
                <td>${Utils.escapeHtml(Utils.truncate(c.cited_authors || '', 40))}</td>
                <td>${Utils.escapeHtml(c.cited_journal || '')}</td>
                <td>${c.cited_doi ? `<a href="https://doi.org/${c.cited_doi}" target="_blank">${c.cited_doi}</a>` : ''}</td>
            </tr>`).join('')}</tbody>
        </table>`;
    },

    renderSimilarPapers(data) {
        if (!data || !data.results || !data.results.length) {
            return '<div class="empty-state">' + I18n.t('similar.no_data') + '</div>';
        }
        return `<div id="similar-chart" style="margin-bottom:12px;"></div>
                ${data.results.map(r => `<div class="result-card" style="margin-bottom:8px;cursor:pointer;" data-paper-id="${r.id}">
                    <div class="result-title">${Utils.escapeHtml(r.title || `论文 ${r.id}`)}</div>
                    <div class="result-meta">${I18n.t('similar.similarity')}: ${(r.similarity * 100).toFixed(1)}% | ${r.journal || ''} | ${r.published_date || ''}</div>
                </div>`).join('')}`;
    },

    drawSimilarChart(data) {
        const el = document.getElementById('similar-chart');
        if (!el || !data || !data.results) return;
        const items = data.results.map(r => ({
            label: Utils.truncate(r.title || r.doi || `论文 ${r.id}`, 25),
            value: r.similarity || 0
        }));
        Charts.horizontalBar(el, items, { height: items.length * 34 + 30 });
    },

    // ------------------ 可视化组件 ------------------
    renderGraphToolbar(state, onChange) {
        const entityTypes = state.entity_types || { paper: true, author: true, keyword: true, data_point: true };
        const html = `<div class="graph-toolbar">
            <div class="range-slider">
                <label>${I18n.t('graph.toolbar.year')}:</label>
                <input type="number" id="graph-year-from" value="${state.year_from || ''}" placeholder="${I18n.t('filter.start_year')}">
                <span>-</span>
                <input type="number" id="graph-year-to" value="${state.year_to || ''}" placeholder="${I18n.t('filter.end_year')}">
            </div>
            <div>
                <label>${I18n.t('graph.toolbar.min_citations')}:</label>
                <input type="number" id="graph-min-citations" value="${state.min_citations || 0}" min="0">
            </div>
            <div>
                <label>${I18n.t('graph.toolbar.max_nodes')}:</label>
                <input type="number" id="graph-max-nodes" value="${state.max_nodes || 80}" min="20" max="500" style="width:70px;">
            </div>
            <div class="checkbox-group">
                <label><input type="checkbox" id="graph-type-paper" ${entityTypes.paper ? 'checked' : ''}> ${I18n.t('graph.paper')}</label>
                <label><input type="checkbox" id="graph-type-author" ${entityTypes.author ? 'checked' : ''}> ${I18n.t('graph.author')}</label>
                <label><input type="checkbox" id="graph-type-keyword" ${entityTypes.keyword ? 'checked' : ''}> ${I18n.t('graph.keyword')}</label>
                <label><input type="checkbox" id="graph-type-data" ${entityTypes.data_point ? 'checked' : ''}> ${I18n.t('graph.data_point')}</label>
                <label><input type="checkbox" id="graph-citation-only" ${state.citation_only ? 'checked' : ''}> ${I18n.t('graph.sidebar.citation_only')}</label>
                <label><input type="checkbox" id="graph-show-labels" ${state.show_labels !== false ? 'checked' : ''}> ${I18n.t('graph.sidebar.show_labels')}</label>
            </div>
            <button class="btn btn-primary" id="graph-refresh">${I18n.t('graph.toolbar.refresh')}</button>
        </div>`;
        setTimeout(() => {
            const refresh = () => {
                const newState = {
                    year_from: document.getElementById('graph-year-from').value,
                    year_to: document.getElementById('graph-year-to').value,
                    min_citations: parseInt(document.getElementById('graph-min-citations').value || '0', 10),
                    max_nodes: parseInt(document.getElementById('graph-max-nodes').value || '80', 10),
                    entity_types: {
                        paper: document.getElementById('graph-type-paper').checked,
                        author: document.getElementById('graph-type-author').checked,
                        keyword: document.getElementById('graph-type-keyword').checked,
                        data_point: document.getElementById('graph-type-data').checked,
                    },
                    citation_only: document.getElementById('graph-citation-only').checked,
                    show_labels: document.getElementById('graph-show-labels').checked
                };
                onChange(newState);
            };
            document.getElementById('graph-refresh').addEventListener('click', refresh);
            document.querySelectorAll('.graph-toolbar input').forEach(el => el.addEventListener('change', refresh));
        }, 0);
        return html;
    },

    renderGraphLegend() {
        const items = [
            { type: 'paper', color: '#2563eb', label: I18n.t('graph.paper') },
            { type: 'author', color: '#6366f1', label: I18n.t('graph.author') },
            { type: 'keyword', color: '#f59e0b', label: I18n.t('graph.keyword') },
            { type: 'data_point', color: '#10b981', label: I18n.t('graph.data_point') }
        ];
        return `<div class="graph-legend">${items.map(it => `
            <div class="graph-legend-item">
                <span class="graph-legend-dot" style="background:${it.color}"></span>
                <span>${it.label}</span>
            </div>
        `).join('')}</div>`;
    },

    // 左侧图谱筛选面板（参考 Agent Star Map 的分类板思路）
    renderGraphSidebar(state, onChange, options = {}) {
        const entityTypes = state.entity_types || { paper: true, author: true, keyword: true, data_point: true };
        const nodeSearch = state.node_search || '';
        const html = `<div class="graph-sidebar">
            <div class="filter-section">
                <h4>${I18n.t('graph.sidebar.node_types')}</h4>
                <div class="checkbox-group">
                    <label><input type="checkbox" id="gs-type-paper" ${entityTypes.paper ? 'checked' : ''}> ${I18n.t('graph.paper')}</label>
                    <label><input type="checkbox" id="gs-type-author" ${entityTypes.author ? 'checked' : ''}> ${I18n.t('graph.author')}</label>
                    <label><input type="checkbox" id="gs-type-keyword" ${entityTypes.keyword ? 'checked' : ''}> ${I18n.t('graph.keyword')}</label>
                    <label><input type="checkbox" id="gs-type-data" ${entityTypes.data_point ? 'checked' : ''}> ${I18n.t('graph.data_point')}</label>
                </div>
            </div>
            <div class="filter-section">
                <h4>${I18n.t('graph.sidebar.year_range')}</h4>
                <div class="filter-row">
                    <input type="number" id="gs-year-from" value="${state.year_from || ''}" placeholder="${I18n.t('filter.start_year')}">
                    <span>-</span>
                    <input type="number" id="gs-year-to" value="${state.year_to || ''}" placeholder="${I18n.t('filter.end_year')}">
                </div>
            </div>
            <div class="filter-section">
                <h4>${I18n.t('graph.sidebar.citations_nodes')}</h4>
                <div class="filter-row">
                    <label>${I18n.t('graph.sidebar.min_citations')}</label>
                    <input type="number" id="gs-min-citations" value="${state.min_citations || 0}" min="0">
                </div>
                <div class="filter-row" style="margin-top:6px;">
                    <label>${I18n.t('graph.sidebar.max_nodes')}</label>
                    <input type="number" id="gs-max-nodes" value="${state.max_nodes || 80}" min="20" max="500">
                </div>
            </div>
            <div class="filter-section">
                <h4>${I18n.t('graph.sidebar.display_options')}</h4>
                <div class="checkbox-group">
                    <label><input type="checkbox" id="gs-citation-only" ${state.citation_only ? 'checked' : ''}> ${I18n.t('graph.sidebar.citation_only')}</label>
                    <label><input type="checkbox" id="gs-show-labels" ${state.show_labels !== false ? 'checked' : ''}> ${I18n.t('graph.sidebar.show_labels')}</label>
                </div>
            </div>
            <div class="filter-section">
                <h4>${I18n.t('graph.sidebar.node_locate')}</h4>
                <div class="filter-row">
                    <input type="text" id="gs-node-search" value="${Utils.escapeHtml(nodeSearch)}" placeholder="${I18n.t('graph.sidebar.node_search_placeholder')}">
                </div>
                <div class="hint">${I18n.t('graph.sidebar.node_search_hint')}</div>
            </div>
            <div class="filter-section">
                <h4>${I18n.t('graph.sidebar.graph_health')}</h4>
                <div id="graph-diag-badge"><span style="color:#6b7280;">${I18n.t('graph.sidebar.health_loading')}</span></div>
            </div>
            <div class="filter-section" style="margin-top:auto;">
                <button class="btn btn-primary" id="gs-refresh" style="width:100%;">${I18n.t('graph.sidebar.refresh')}</button>
            </div>
        </div>`;
        setTimeout(() => {
            const gather = () => ({
                year_from: document.getElementById('gs-year-from').value,
                year_to: document.getElementById('gs-year-to').value,
                min_citations: parseInt(document.getElementById('gs-min-citations').value || '0', 10),
                max_nodes: parseInt(document.getElementById('gs-max-nodes').value || '80', 10),
                entity_types: {
                    paper: document.getElementById('gs-type-paper').checked,
                    author: document.getElementById('gs-type-author').checked,
                    keyword: document.getElementById('gs-type-keyword').checked,
                    data_point: document.getElementById('gs-type-data').checked,
                },
                citation_only: document.getElementById('gs-citation-only').checked,
                show_labels: document.getElementById('gs-show-labels').checked,
                node_search: document.getElementById('gs-node-search').value.trim()
            });
            const refresh = () => onChange({ ...gather(), action: 'refresh' });
            const searchInput = document.getElementById('gs-node-search');
            if (searchInput) {
                searchInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        onChange({ ...gather(), action: 'locate' });
                    }
                });
            }
            document.getElementById('gs-refresh').addEventListener('click', refresh);
            document.querySelectorAll('.graph-sidebar input').forEach(el => {
                if (el.id !== 'gs-node-search') el.addEventListener('change', refresh);
            });
        }, 0);
        return html;
    },

    renderTable(rows, columns, options = {}) {
        const onRowClick = options.onRowClick;
        const formatters = options.formatters || {};
        if (!rows || !rows.length) {
            return '<div class="empty-state">' + I18n.t('table.no_data') + '</div>';
        }
        const tableId = 'table-' + Math.random().toString(36).slice(2, 9);
        let html = `<div class="knowledgebase-table" id="${tableId}"><table class="data-table"><thead><tr>`;
        columns.forEach(col => {
            html += `<th>${Utils.escapeHtml(col.label)}</th>`;
        });
        html += '</tr></thead><tbody>';
        rows.forEach(row => {
            const rowId = row.id || row.paper_id || row.data_point_id || '';
            const clickAttr = onRowClick ? `style="cursor:pointer" data-row-id="${rowId}"` : '';
            html += `<tr ${clickAttr}>`;
            columns.forEach(col => {
                const raw = row[col.key];
                let cell;
                if (formatters[col.key]) {
                    cell = formatters[col.key](raw, row);
                } else if (col.render) {
                    cell = col.render(raw, row);
                } else {
                    cell = raw === undefined || raw === null ? '' : Utils.escapeHtml(String(raw));
                }
                html += `<td>${cell}</td>`;
            });
            html += '</tr>';
        });
        html += '</tbody></table></div>';
        if (onRowClick) {
            setTimeout(() => {
                const wrapper = document.getElementById(tableId);
                if (!wrapper) return;
                wrapper.querySelectorAll('[data-row-id]').forEach(tr => {
                    tr.addEventListener('click', () => {
                        const row = rows.find(r => String(r.id || r.paper_id || r.data_point_id) === tr.dataset.rowId);
                        if (row) onRowClick(row);
                    });
                });
            }, 0);
        }
        return html;
    },

    renderTagCloud(items, onClick, options = {}) {
        if (!items || !items.length) return '<div class="empty-state">' + I18n.t('tagcloud.no_data') + '</div>';
        const max = Math.max(...items.map(i => i.count || 1));
        return `<div class="tag-cloud">${items.map(item => {
            const size = 11 + Math.round(((item.count || 1) / max) * 5);
            return `<span class="tag" data-tag="${Utils.escapeHtml(item.key)}" style="font-size:${size}px;cursor:pointer">${Utils.escapeHtml(item.key)} (${item.count || 0})</span>`;
        }).join('')}</div>`;
    },

    renderYearSlider(min, max, current, onChange) {
        const cfrom = (current.year_from != null && !isNaN(current.year_from)) ? current.year_from : min;
        const cto = (current.year_to != null && !isNaN(current.year_to)) ? current.year_to : max;
        const html = `<div class="range-slider">
            <label>年份范围:</label>
            <input type="range" id="year-from" min="${min}" max="${max}" value="${cfrom}">
            <span id="year-from-label">${cfrom}</span>
            <span>-</span>
            <input type="range" id="year-to" min="${min}" max="${max}" value="${cto}">
            <span id="year-to-label">${cto}</span>
        </div>`;
        setTimeout(() => {
            const fromEl = document.getElementById('year-from');
            const toEl = document.getElementById('year-to');
            const fromLabel = document.getElementById('year-from-label');
            const toLabel = document.getElementById('year-to-label');
            if (!fromEl || !toEl || !fromLabel || !toLabel) return;
            const emit = Utils.debounce(() => {
                let f = parseInt(fromEl.value, 10);
                let t = parseInt(toEl.value, 10);
                if (isNaN(f)) f = min;
                if (isNaN(t)) t = max;
                if (f > t) { const tmp = f; f = t; t = tmp; }
                fromLabel.textContent = f;
                toLabel.textContent = t;
                onChange({ year_from: f, year_to: t });
            }, 200);
            fromEl.addEventListener('input', emit);
            toEl.addEventListener('input', emit);
        }, 0);
        return html;
    },

    renderPagination(total, limit, offset, onPage) {
        const current = Math.floor(offset / limit) + 1;
        const totalPages = Math.ceil(total / limit);
        if (totalPages <= 1) return '';
        let html = '<div style="display:flex;gap:8px;align-items:center;margin-top:16px;">';
        html += `<button class="btn btn-secondary" ${current <= 1 ? 'disabled' : ''} data-page="${current - 1}">${I18n.t('pagination.prev')}</button>`;
        html += `<span style="font-size:13px;color:var(--text-secondary);">${I18n.t('pagination.info', {current: current, total: totalPages, total_items: total})}</span>`;
        html += `<button class="btn btn-secondary" ${current >= totalPages ? 'disabled' : ''} data-page="${current + 1}">${I18n.t('pagination.next')}</button>`;
        html += '</div>';
        setTimeout(() => {
            const container = document.querySelector('[data-pagination]');
            if (!container) return;
            container.querySelectorAll('button[data-page]').forEach(btn => {
                btn.addEventListener('click', () => onPage(parseInt(btn.dataset.page)));
            });
        }, 0);
        return html;
    }
};
