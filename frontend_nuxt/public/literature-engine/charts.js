// SVG 图表绘制（零依赖）
const Charts = {
    barChart(container, data, options = {}) {
        // data: [{label, value, color?}]
        container.innerHTML = '';
        if (!data || !data.length) {
            container.innerHTML = '<div class="empty-state">' + I18n.t('common.no_data') + '</div>';
            return;
        }
        const width = options.width || container.clientWidth || 600;
        const height = options.height || 300;
        const margin = { top: 20, right: 20, bottom: 60, left: 50 };
        const chartW = width - margin.left - margin.right;
        const chartH = height - margin.top - margin.bottom;

        const maxValue = Math.max(...data.map(d => d.value));
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', width);
        svg.setAttribute('height', height);
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);

        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('transform', `translate(${margin.left},${margin.top})`);
        svg.appendChild(g);

        // Y 轴网格线
        const ticks = 5;
        for (let i = 0; i <= ticks; i++) {
            const y = chartH - (i / ticks) * chartH;
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', 0);
            line.setAttribute('x2', chartW);
            line.setAttribute('y1', y);
            line.setAttribute('y2', y);
            line.setAttribute('stroke', '#e5e7eb');
            g.appendChild(line);

            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', -8);
            text.setAttribute('y', y + 4);
            text.setAttribute('text-anchor', 'end');
            text.setAttribute('font-size', '11');
            text.setAttribute('fill', '#6b7280');
            text.textContent = Math.round((i / ticks) * maxValue);
            g.appendChild(text);
        }

        // 柱子
        const barW = Math.min(60, chartW / data.length * 0.6);
        const step = chartW / data.length;
        data.forEach((d, i) => {
            const h = maxValue ? (d.value / maxValue) * chartH : 0;
            const x = i * step + (step - barW) / 2;
            const y = chartH - h;
            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', x);
            rect.setAttribute('y', y);
            rect.setAttribute('width', barW);
            rect.setAttribute('height', h);
            rect.setAttribute('fill', d.color || '#2563eb');
            rect.setAttribute('rx', 3);
            g.appendChild(rect);

            // X 轴标签
            const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            label.setAttribute('x', x + barW / 2);
            label.setAttribute('y', chartH + 18);
            label.setAttribute('text-anchor', 'middle');
            label.setAttribute('font-size', '11');
            label.setAttribute('fill', '#374151');
            label.textContent = Utils.truncate(d.label, 12);
            g.appendChild(label);
        });

        container.appendChild(svg);
    },

    horizontalBar(container, data, options = {}) {
        // data: [{label, value, color?}]
        container.innerHTML = '';
        if (!data || !data.length) {
            container.innerHTML = '<div class="empty-state">' + I18n.t('common.no_data') + '</div>';
            return;
        }
        const width = options.width || container.clientWidth || 300;
        const height = options.height || data.length * 34 + 30;
        const margin = { top: 10, right: 50, bottom: 20, left: 120 };
        const chartW = width - margin.left - margin.right;
        const chartH = height - margin.top - margin.bottom;
        const maxValue = Math.max(...data.map(d => d.value));

        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', width);
        svg.setAttribute('height', height);
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);

        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('transform', `translate(${margin.left},${margin.top})`);
        svg.appendChild(g);

        const rowH = chartH / data.length;
        data.forEach((d, i) => {
            const y = i * rowH + 4;
            const barH = rowH - 10;
            const barW = maxValue ? (d.value / maxValue) * chartW : 0;

            const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            label.setAttribute('x', -10);
            label.setAttribute('y', y + barH / 2 + 4);
            label.setAttribute('text-anchor', 'end');
            label.setAttribute('font-size', '12');
            label.setAttribute('fill', '#374151');
            label.textContent = Utils.truncate(d.label, 18);
            g.appendChild(label);

            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', 0);
            rect.setAttribute('y', y);
            rect.setAttribute('width', barW);
            rect.setAttribute('height', barH);
            rect.setAttribute('fill', d.color || '#3b82f6');
            rect.setAttribute('rx', 3);
            g.appendChild(rect);

            const valText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            valText.setAttribute('x', barW + 6);
            valText.setAttribute('y', y + barH / 2 + 4);
            valText.setAttribute('font-size', '11');
            valText.setAttribute('fill', '#374151');
            valText.textContent = d.value.toFixed ? d.value.toFixed(3) : d.value;
            g.appendChild(valText);
        });

        container.appendChild(svg);
    },

    pieChart(container, data, options = {}) {
        // data: [{label, value, color?}]
        container.innerHTML = '';
        if (!data || !data.length) {
            container.innerHTML = '<div class="empty-state">' + I18n.t('common.no_data') + '</div>';
            return;
        }
        const size = options.size || 240;
        const radius = size / 2 - 20;
        const cx = size / 2;
        const cy = size / 2;
        const total = data.reduce((a, b) => a + b.value, 0);
        const colors = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', size + 140);
        svg.setAttribute('height', size);
        svg.setAttribute('viewBox', `0 0 ${size + 140} ${size}`);

        let startAngle = 0;
        data.forEach((d, i) => {
            const frac = total ? d.value / total : 0;
            const angle = frac * Math.PI * 2;
            const endAngle = startAngle + angle;
            const x1 = cx + radius * Math.cos(startAngle);
            const y1 = cy + radius * Math.sin(startAngle);
            const x2 = cx + radius * Math.cos(endAngle);
            const y2 = cy + radius * Math.sin(endAngle);
            const largeArc = angle > Math.PI ? 1 : 0;
            const pathData = `M ${cx} ${cy} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`;

            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('d', pathData);
            path.setAttribute('fill', d.color || colors[i % colors.length]);
            path.setAttribute('stroke', '#fff');
            path.setAttribute('stroke-width', '2');
            svg.appendChild(path);

            startAngle = endAngle;
        });

        // 图例
        let ly = 20;
        data.forEach((d, i) => {
            const color = d.color || colors[i % colors.length];
            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', size + 10);
            rect.setAttribute('y', ly);
            rect.setAttribute('width', 12);
            rect.setAttribute('height', 12);
            rect.setAttribute('fill', color);
            svg.appendChild(rect);

            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', size + 28);
            text.setAttribute('y', ly + 10);
            text.setAttribute('font-size', '12');
            text.setAttribute('fill', '#374151');
            const pct = total ? ((d.value / total) * 100).toFixed(1) : 0;
            text.textContent = `${Utils.truncate(d.label, 14)} (${pct}%)`;
            svg.appendChild(text);
            ly += 22;
        });

        container.appendChild(svg);
    },

    simpleNetwork(container, nodes, links, options = {}) {
        // nodes: [{id, label, group?}], links: [{source, target}]
        container.innerHTML = '';
        if (!nodes || !nodes.length) {
            container.innerHTML = '<div class="empty-state">' + I18n.t('common.no_data') + '</div>';
            return;
        }
        const width = options.width || container.clientWidth || 600;
        const height = options.height || 500;
        const colors = ['#2563eb', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4'];

        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', '100%');
        svg.setAttribute('height', height);
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
        svg.classList.add('network-svg');

        // 简单同心圆布局：中心节点在中心，其他围绕
        const center = { x: width / 2, y: height / 2 };
        const radius = Math.min(width, height) / 2 - 60;
        const nodePositions = {};

        // 找到中心节点（假设为第一个或 group=0）
        let centerNode = nodes.find(n => n.group === 0) || nodes[0];
        nodePositions[centerNode.id] = center;

        const others = nodes.filter(n => n.id !== centerNode.id);
        others.forEach((n, i) => {
            const angle = (i / Math.max(1, others.length)) * Math.PI * 2;
            nodePositions[n.id] = {
                x: center.x + radius * Math.cos(angle),
                y: center.y + radius * Math.sin(angle)
            };
        });

        // 连线
        links.forEach(l => {
            const s = nodePositions[l.source];
            const t = nodePositions[l.target];
            if (!s || !t) return;
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', s.x);
            line.setAttribute('y1', s.y);
            line.setAttribute('x2', t.x);
            line.setAttribute('y2', t.y);
            line.setAttribute('stroke', '#cbd5e1');
            line.setAttribute('stroke-width', '1.5');
            svg.appendChild(line);
        });

        // 节点
        nodes.forEach(n => {
            const pos = nodePositions[n.id];
            const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            g.setAttribute('transform', `translate(${pos.x},${pos.y})`);

            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('r', n.id === centerNode.id ? 18 : 10);
            circle.setAttribute('fill', colors[(n.group || 0) % colors.length]);
            circle.setAttribute('stroke', '#fff');
            circle.setAttribute('stroke-width', '2');
            g.appendChild(circle);

            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('y', n.id === centerNode.id ? 34 : 22);
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('font-size', n.id === centerNode.id ? '13' : '11');
            text.setAttribute('fill', '#374151');
            text.textContent = Utils.truncate(n.label, 20);
            g.appendChild(text);

            svg.appendChild(g);
        });

        container.appendChild(svg);
    },

    forceGraph(container, nodes, edges, options = {}) {
        // nodes: [{id, label, type, ...}], edges: [{source, target, type, weight?}]
        container.innerHTML = '';
        if (!nodes || !nodes.length) {
            container.innerHTML = '<div class="empty-state">' + I18n.t('graph.no_nodes') + '</div>';
            return;
        }

        // 容器宽度保护：若父级尚未展开或视口极窄，使用保底尺寸避免 viewBox 为 0
        const containerWidth = Math.max(320, container.clientWidth || 800);
        const containerHeight = Math.max(240, container.clientHeight || 620);
        const width = options.width || containerWidth;
        const height = options.height || containerHeight;
        const onNodeClick = options.onNodeClick || (() => {});
        const showLabels = options.show_labels !== false;
        const relayout = options.relayout;
        const nCount = nodes.length;

        // ============== 配色方案 ==============
        // 节点色：5 类分布在色相轮上，避免相邻色相干扰识别
        const typeColor = {
            paper:       '#1d4ed8', // 蓝-700  核心节点，鲜明专业
            author:      '#9333ea', // 紫-600  与蓝色有明显色相差
            keyword:     '#ea580c', // 橙-600  暖色，标签语义
            data_point:  '#0d9488', // 青-600  冷色，区分"数据"
            institution: '#be185d'  // 玫红-700 区分个人
        };
        const typeLabel = {
            paper: I18n.t('graph.paper'),
            author: I18n.t('graph.author'),
            keyword: I18n.t('graph.keyword'),
            data_point: I18n.t('graph.data_point'),
            institution: I18n.t('graph.institution')
        };
        // 边色：按关系类型分配透明度梯度与线型，
        // 主关系(cites/coauthored)用 1.2px 实线强调，辅助关系用 1px + 虚线弱化
        const edgeStyle = {
            cites:             { color: '#64748b', width: 1.2, dash: 'none' },
            authored:          { color: '#9ca3af', width: 1.0, dash: 'none' },
            has_keyword:       { color: '#fb923c', width: 1.0, dash: '4,3' },
            has_data:          { color: '#5eead4', width: 1.0, dash: 'none' },
            coauthored:        { color: '#c084fc', width: 1.2, dash: 'none' },
            affiliated_with:   { color: '#f0abfc', width: 0.9, dash: '4,3' },
            institution_collab:{ color: '#e879f9', width: 1.2, dash: 'none' }
        };
        // 方向高亮配色：避开节点色相，确保高亮时不与节点混淆
        const directionColor = {
            upstream:   '#06b6d4', // 青-500 上游（被当前节点引用）
            downstream: '#f43f5e', // 玫红-500 下游（引用当前节点）
            dist2:      '#84cc16'  // 青柠-500 2阶邻居
        };
        // 透明度梯度：聚焦路径全亮，失焦元素大幅淡化
        const opacityFocus = 1.0;
        const opacityDim   = 0.12;
        const opacityNodeDim = 0.18;
        const baseRadius = { paper: 9, author: 6, keyword: 5, data_point: 4, institution: 10 };
        // 节点过多时进一步缩小半径，降低视觉密度
        const densityFactor = nCount > 80 ? 0.82 : nCount > 50 ? 0.9 : 1;
        const maxCitation = Math.max(...nodes.filter(n => n.type === 'paper').map(n => n.citation_count || 0), 1);

        const nodeMap = {};
        nodes.forEach(n => nodeMap[n.id] = n);

        // 邻接索引与度数
        const neighbors = {};
        nodes.forEach(n => neighbors[n.id] = new Set());
        edges.forEach(e => {
            if (neighbors[e.source]) neighbors[e.source].add(e.target);
            if (neighbors[e.target]) neighbors[e.target].add(e.source);
        });

        // 有向邻接：用于引用网络的上游/下游方向分析
        // 仅 citation / coauthored / institution_collab 边被视为有向；其余边不参与方向分析
        const outNeighbors = {};
        const inNeighbors = {};
        nodes.forEach(n => { outNeighbors[n.id] = new Set(); inNeighbors[n.id] = new Set(); });
        edges.forEach(e => {
            const directed = e.type === 'cites' || e.type === 'institution_collab' || e.type === 'coauthored';
            if (directed) {
                if (outNeighbors[e.source]) outNeighbors[e.source].add(e.target);
                if (inNeighbors[e.target]) inNeighbors[e.target].add(e.source);
            }
        });

        const degree = {};
        nodes.forEach(n => degree[n.id] = neighbors[n.id].size);

        // 半径：论文按被引缩放，机构/作者按度数轻微缩放；密度因子整体缩放
        nodes.forEach(n => {
            n.degree = degree[n.id] || 0;
            if (n.type === 'paper') {
                const citationRatio = Math.sqrt((n.citation_count || 0) / maxCitation);
                n.radius = (baseRadius.paper + citationRatio * 10) * densityFactor;
            } else if (n.type === 'institution') {
                n.radius = (baseRadius.institution + Math.min(8, n.degree * 0.6)) * densityFactor;
            } else if (n.type === 'author') {
                n.radius = (baseRadius.author + Math.min(5, n.degree * 0.35)) * densityFactor;
            } else {
                n.radius = (baseRadius[n.type] || 5) * densityFactor;
            }
        });

        // 识别中心节点：显式 is_center > 度数最大 > 第一个节点
        let centerNode = nodes.find(n => n.is_center);
        if (!centerNode) {
            centerNode = nodes.reduce((max, n) => (n.degree > max.degree ? n : max), nodes[0]);
        }

        // 基于 BFS 的拓扑分层（到中心节点的最短跳数）
        const level = {};
        nodes.forEach(n => level[n.id] = -1);
        const queue = [centerNode.id];
        level[centerNode.id] = 0;
        let head = 0;
        while (head < queue.length) {
            const cur = queue[head++];
            neighbors[cur].forEach(nid => {
                if (level[nid] === -1) {
                    level[nid] = level[cur] + 1;
                    queue.push(nid);
                }
            });
        }
        nodes.forEach(n => { if (level[n.id] === -1) level[n.id] = 99; });
        const maxLevel = Math.max(...Object.values(level));

        // 初始位置：中心节点居中，其余按拓扑层分布在同心圆上
        const positions = {};
        const center = { x: width / 2, y: height / 2 };
        const seed = relayout ? Math.random() : 1;
        const maxRadius = Math.min(width, height) * 0.42;

        nodes.forEach((n, i) => {
            let radius, angle;
            if (n.id === centerNode.id) {
                positions[n.id] = { x: center.x + (Math.random() - 0.5) * 20 * seed, y: center.y + (Math.random() - 0.5) * 20 * seed, vx: 0, vy: 0 };
                return;
            }
            const lvl = level[n.id];
            radius = maxRadius * (0.25 + 0.75 * (lvl / Math.max(maxLevel, 1)));
            // 同层节点均匀分布，并按类型微调角度避免完全重叠
            const sameLevel = nodes.filter(m => m.id !== centerNode.id && level[m.id] === lvl);
            const idx = sameLevel.findIndex(m => m.id === n.id);
            const jitter = (Math.random() - 0.5) * 0.25 * seed;
            angle = (idx / Math.max(sameLevel.length, 1)) * Math.PI * 2 + jitter;
            positions[n.id] = {
                x: center.x + Math.cos(angle) * radius,
                y: center.y + Math.sin(angle) * radius,
                vx: 0, vy: 0
            };
        });

        // 力导向迭代：更稳定的参数
        const area = width * height;
        // 理想距离随节点数增加而增大，避免拥挤
        const k = Math.sqrt(area / nCount) * (nCount > 60 ? 1.45 : nCount > 30 ? 1.25 : 1.1);
        const iterations = Math.min(400, Math.max(100, Math.floor(12000 / Math.max(nCount, 10))));
        let temperature = Math.min(width, height) / 8;

        for (let iter = 0; iter < iterations; iter++) {
            // 斥力：与节点半径和质量相关，带硬壳排斥避免重叠
            for (let i = 0; i < nodes.length; i++) {
                for (let j = i + 1; j < nodes.length; j++) {
                    const a = nodes[i], b = nodes[j];
                    const pa = positions[a.id], pb = positions[b.id];
                    let dx = pa.x - pb.x;
                    let dy = pa.y - pb.y;
                    let dist = Math.sqrt(dx * dx + dy * dy) || 0.001;
                    const minDist = a.radius + b.radius + 8;
                    const mass = (a.radius + b.radius + 4) * (1 + (a.degree + b.degree) * 0.08);
                    let force = (k * k * mass) / (dist * dist);
                    // 硬壳：距离小于最小间距时强力推开
                    if (dist < minDist) {
                        force += (minDist - dist) * 0.8;
                    }
                    const fx = (dx / dist) * force;
                    const fy = (dy / dist) * force;
                    pa.vx += fx; pa.vy += fy;
                    pb.vx -= fx; pb.vy -= fy;
                }
            }

            // 弹簧引力：按边权重调整目标距离，权重越大距离越近
            edges.forEach(e => {
                const s = positions[e.source], t = positions[e.target];
                if (!s || !t) return;
                let dx = t.x - s.x;
                let dy = t.y - s.y;
                let dist = Math.sqrt(dx * dx + dy * dy) || 0.001;
                const weight = Math.max(1, (e.weight || 1));
                const idealLen = k * (0.8 + 1.5 / Math.sqrt(weight));
                const displacement = dist - idealLen;
                const force = displacement * 0.04;
                const fx = (dx / dist) * force;
                const fy = (dy / dist) * force;
                s.vx += fx; s.vy += fy;
                t.vx -= fx; t.vy -= fy;
            });

            // 中心引力：中心节点强固定，其他节点轻微向中心
            nodes.forEach(n => {
                const p = positions[n.id];
                if (n.id === centerNode.id) {
                    p.vx += (center.x - p.x) * 0.15;
                    p.vy += (center.y - p.y) * 0.15;
                } else {
                    p.vx += (center.x - p.x) * 0.008;
                    p.vy += (center.y - p.y) * 0.008;
                }
            });

            // 更新位置并降温
            nodes.forEach(n => {
                const p = positions[n.id];
                const mag = Math.sqrt(p.vx * p.vx + p.vy * p.vy) || 1;
                p.vx = (p.vx / mag) * Math.min(mag, temperature);
                p.vy = (p.vy / mag) * Math.min(mag, temperature);
                p.x += p.vx; p.y += p.vy;
                const pad = n.radius + 8;
                p.x = Math.max(pad, Math.min(width - pad, p.x));
                p.y = Math.max(pad, Math.min(height - pad, p.y));
                p.vx *= 0.6; p.vy *= 0.6;
            });
            temperature *= 0.985;
        }

        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', '100%');
        svg.setAttribute('height', height);
        // 增加 viewBox 边距，避免边缘节点标签被截断
        const viewPad = 50;
        svg.setAttribute('viewBox', `${-viewPad} ${-viewPad} ${width + viewPad * 2} ${height + viewPad * 2}`);
        svg.style.cursor = 'grab';

        // 缩放/平移状态
        let scale = 1, tx = 0, ty = 0;
        let isDragging = false, dragStart = null, panStart = null;
        const mainGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        svg.appendChild(mainGroup);
        // 更新标签可见性（考虑缩放级别与简单碰撞避让）
        const updateLabelVisibility = () => {
            const visibleLabels = [];
            nodeEls.forEach(({ el, node, labelEl }) => {
                if (!labelEl) return;
                const show = shouldShowLabel(node, scale);
                if (show) {
                    const rect = labelEl.getBoundingClientRect();
                    visibleLabels.push({ el: labelEl, node, rect });
                } else {
                    labelEl.style.opacity = '0';
                }
            });
            // 简单碰撞避让：隐藏与更高度数节点标签重叠的低度数节点标签
            visibleLabels.sort((a, b) => (b.node.degree || 0) - (a.node.degree || 0));
            const kept = [];
            visibleLabels.forEach(item => {
                const r1 = item.rect;
                const overlap = kept.some(k => {
                    const r2 = k.rect;
                    return !(r1.right < r2.left || r1.left > r2.right || r1.bottom < r2.top || r1.top > r2.bottom);
                });
                if (overlap) {
                    item.el.style.opacity = '0';
                } else {
                    item.el.style.opacity = '1';
                    kept.push(item);
                }
            });
        };

        const updateTransform = () => {
            mainGroup.setAttribute('transform', `translate(${tx},${ty}) scale(${scale})`);
            updateLabelVisibility();
        };

        // 定义箭头与滤镜（箭头颜色与 cites 边一致）
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        defs.innerHTML = `
            <marker id="arrow-cites" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="${edgeStyle.cites.color}"/>
            </marker>
            <filter id="node-glow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="3.5" result="blur"/>
                <feMerge>
                    <feMergeNode in="blur"/>
                    <feMergeNode in="SourceGraphic"/>
                </feMerge>
            </filter>
        `;
        svg.appendChild(defs);

        container.style.position = 'relative';

        // Tooltip
        const tooltip = document.createElement('div');
        tooltip.className = 'graph-tooltip';
        container.appendChild(tooltip);
        const showTooltip = (e, html) => {
            tooltip.innerHTML = html;
            tooltip.style.display = 'block';
            const rect = container.getBoundingClientRect();
            tooltip.style.left = (e.clientX - rect.left + 12) + 'px';
            tooltip.style.top = (e.clientY - rect.top + 12) + 'px';
        };
        const hideTooltip = () => { tooltip.style.display = 'none'; };

        // 标签显示策略：按缩放级别与节点重要性动态显示，避免小视口下标签重叠
        const avgDegree = nodes.reduce((s, n) => s + n.degree, 0) / Math.max(1, nodes.length);
        const shouldShowLabel = (n, currentScale = scale) => {
            if (!showLabels) return false;
            if (n.id === centerNode.id) return true;
            if (n.type === 'institution') return true;
            if (n.type === 'paper') return currentScale >= 0.75;
            if (n.degree >= Math.max(3, avgDegree * 1.1)) return currentScale >= 0.9;
            if (n.degree >= 2) return currentScale >= 1.25;
            return currentScale >= 1.8;
        };

        // 边
        const edgeEls = [];
        edges.forEach(e => {
            const s = positions[e.source], t = positions[e.target];
            if (!s || !t) return;
            const style = edgeStyle[e.type] || edgeStyle.has_data;
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', s.x);
            line.setAttribute('y1', s.y);
            line.setAttribute('x2', t.x);
            line.setAttribute('y2', t.y);
            line.setAttribute('stroke', style.color);
            line.setAttribute('stroke-width', style.width);
            line.setAttribute('stroke-dasharray', style.dash);
            line.setAttribute('opacity', '0.72');
            if (e.type === 'cites') {
                line.setAttribute('marker-end', 'url(#arrow-cites)');
            }
            line.classList.add('graph-link', e.type || 'link');
            line.dataset.source = e.source;
            line.dataset.target = e.target;
            line.dataset.type = e.type || 'link';
            mainGroup.appendChild(line);
            edgeEls.push({ el: line, source: e.source, target: e.target, type: e.type });
        });

        // 节点
        const nodeEls = [];
        nodes.forEach(n => {
            const p = positions[n.id];
            const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            g.classList.add('graph-node');
            g.dataset.id = n.id;
            g.setAttribute('transform', `translate(${p.x.toFixed(2)},${p.y.toFixed(2)})`);

            const r = n.radius;
            const color = typeColor[n.type] || '#94a3b8';

            // 外圈光晕（中心节点更显眼）
            if (n.id === centerNode.id || n.degree >= avgDegree * 2) {
                const halo = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                halo.setAttribute('r', r + 5);
                halo.setAttribute('fill', color);
                // 中心节点光晕更深、范围更大；高连接度节点次之
                if (n.id === centerNode.id) {
                    halo.setAttribute('opacity', '0.22');
                    halo.setAttribute('r', r + 8);
                } else {
                    halo.setAttribute('opacity', '0.15');
                }
                halo.classList.add('node-halo');
                g.appendChild(halo);
            }

            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('r', r);
            circle.setAttribute('fill', color);
            circle.setAttribute('stroke', '#fff');
            circle.setAttribute('stroke-width', n.id === centerNode.id ? '3' : '2');
            g.appendChild(circle);

            // 问题节点警示环（数据质量诊断标记）
            const problemNodeIds = options.problemNodeIds || new Set();
            if (problemNodeIds.has(n.id)) {
                const warn = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                warn.setAttribute('r', r + 4);
                warn.setAttribute('fill', 'none');
                warn.setAttribute('stroke', '#ef4444');
                warn.setAttribute('stroke-width', '2');
                warn.setAttribute('stroke-dasharray', '3,2');
                warn.classList.add('node-problem-ring');
                g.appendChild(warn);
            }

            const showNodeLabel = shouldShowLabel(n);
            if (showNodeLabel) {
                const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                label.setAttribute('y', r + 14);
                label.setAttribute('text-anchor', 'middle');
                label.setAttribute('font-size', n.type === 'paper' ? '12' : n.type === 'institution' ? '11' : '10');
                label.setAttribute('font-weight', n.type === 'paper' || n.id === centerNode.id ? '600' : '400');
                label.setAttribute('fill', '#1f2937');
                label.setAttribute('stroke', '#fff');
                label.setAttribute('stroke-width', '3');
                label.setAttribute('paint-order', 'stroke');
                label.textContent = Utils.truncate(n.label, n.type === 'paper' ? 26 : n.type === 'institution' ? 22 : 14);
                g.appendChild(label);
            }

            g.addEventListener('click', (e) => {
                e.stopPropagation();
                if (focusNodeId === n.id) {
                    onNodeClick(n);
                } else {
                    setFocus(n.id);
                }
            });
            g.addEventListener('dblclick', (e) => { e.stopPropagation(); onNodeClick(n); });
            g.addEventListener('mouseenter', (e) => {
                let info = `<strong>${Utils.escapeHtml(n.label)}</strong><br>${I18n.t('tooltip.type')}: ${typeLabel[n.type] || n.type}`;
                if (n.year) info += `<br>${I18n.t('tooltip.year')}: ${n.year}`;
                if (n.citation_count !== undefined && n.citation_count !== null) info += `<br>${I18n.t('tooltip.citations')}: ${n.citation_count}`;
                if (n.degree) info += `<br>${I18n.t('tooltip.connections')}: ${n.degree}`;
                if (n.count) info += `<br>${I18n.t('tooltip.occurrences')}: ${n.count}`;
                if (n.paper_count) info += `<br>${I18n.t('tooltip.paper_count')}: ${n.paper_count}`;
                if (n.type === 'paper' && n.paper_id) info += `<br><em style="opacity:.8">${I18n.t('tooltip.click_focus')}</em>`;
                showTooltip(e, info);
            });
            g.addEventListener('mousemove', (e) => showTooltip(e, tooltip.innerHTML));
            g.addEventListener('mouseleave', hideTooltip);

            mainGroup.appendChild(g);
            nodeEls.push({ el: g, node: n, labelEl: g.querySelector('text') });
        });

        // 初始标签可见性更新
        updateLabelVisibility();

        // 高亮交互（悬停）
        let activeNodeId = null;
        const setHighlight = (nodeId) => {
            activeNodeId = nodeId;
            if (focusNodeId) return;
            const activeSet = new Set();
            const upSet = new Set();
            const downSet = new Set();
            if (nodeId) {
                activeSet.add(nodeId);
                (neighbors[nodeId] || new Set()).forEach(id => activeSet.add(id));
                (outNeighbors[nodeId] || new Set()).forEach(id => upSet.add(id));
                (inNeighbors[nodeId] || new Set()).forEach(id => downSet.add(id));
            }
            nodeEls.forEach(({ el, node, labelEl }) => {
                const circle = el.querySelector('circle');
                if (!nodeId) {
                    el.style.opacity = '1';
                    circle.setAttribute('stroke-width', node.id === centerNode.id ? '3' : '2');
                    circle.setAttribute('stroke', '#fff');
                    circle.removeAttribute('filter');
                    if (labelEl) labelEl.style.opacity = shouldShowLabel(node, scale) ? '1' : '0';
                } else if (activeSet.has(node.id)) {
                    el.style.opacity = '1';
                    const isCenter = node.id === nodeId;
                    circle.setAttribute('stroke-width', isCenter ? '4' : '3');
                    let strokeColor = '#fff';
                    if (!isCenter) {
                        if (upSet.has(node.id)) strokeColor = directionColor.upstream;
                        else if (downSet.has(node.id)) strokeColor = directionColor.downstream;
                    }
                    circle.setAttribute('stroke', strokeColor);
                    circle.setAttribute('filter', 'url(#node-glow)');
                    if (labelEl) labelEl.style.opacity = '1';
                } else {
                    el.style.opacity = '0.12';
                    circle.setAttribute('stroke-width', '2');
                    circle.setAttribute('stroke', '#fff');
                    circle.removeAttribute('filter');
                    if (labelEl) labelEl.style.opacity = '0';
                }
            });
            edgeEls.forEach(({ el, source, target }) => {
                if (!nodeId) {
                    el.setAttribute('opacity', '0.72');
                    el.setAttribute('stroke-width', edgeStyle[el.dataset.type]?.width || 1);
                    el.setAttribute('stroke', edgeStyle[el.dataset.type]?.color || '#94a3b8');
                } else if (source === nodeId || target === nodeId) {
                    el.setAttribute('opacity', '1');
                    el.setAttribute('stroke-width', '2.5');
                    let ec = edgeStyle[el.dataset.type]?.color || '#94a3b8';
                    if (el.dataset.type === 'cites') {
                        if (source === nodeId) ec = directionColor.upstream;
                        else if (target === nodeId) ec = directionColor.downstream;
                    }
                    el.setAttribute('stroke', ec);
                } else {
                    el.setAttribute('opacity', '0.10');
                    el.setAttribute('stroke', edgeStyle[el.dataset.type]?.color || '#94a3b8');
                }
            });
        };
        nodeEls.forEach(({ el, node }) => {
            el.addEventListener('mouseenter', () => setHighlight(node.id));
            el.addEventListener('mouseleave', () => setHighlight(null));
        });

        // 聚焦模式
        let focusNodeId = null;
        let focusHopDepth = Math.min(Math.max(parseInt(options.focusHopDepth, 10) || 1, 1), 2);
        const focusBadge = document.createElement('div');
        focusBadge.className = 'graph-focus-badge';
        focusBadge.style.display = 'none';
        container.appendChild(focusBadge);

        // BFS 计算指定跳数内的节点与方向分类
        const computeFocusSets = (rootId, depth) => {
            const activeSet = new Set([rootId]);
            const upSet = new Set();
            const downSet = new Set();
            const dist2Set = new Set();
            if (depth <= 0) return { activeSet, upSet, downSet, dist2Set };
            // 1-hop
            (outNeighbors[rootId] || new Set()).forEach(id => { activeSet.add(id); upSet.add(id); });
            (inNeighbors[rootId] || new Set()).forEach(id => { activeSet.add(id); downSet.add(id); });
            // 2-hop：通过非当前 root 的 1-hop 节点扩展
            if (depth >= 2) {
                activeSet.forEach(mid => {
                    if (mid === rootId) return;
                    (neighbors[mid] || new Set()).forEach(nid => {
                        if (!activeSet.has(nid)) {
                            dist2Set.add(nid);
                            activeSet.add(nid);
                        }
                    });
                });
            }
            return { activeSet, upSet, downSet, dist2Set };
        };

        const applyFocus = () => {
            const { activeSet, upSet, downSet, dist2Set } = focusNodeId
                ? computeFocusSets(focusNodeId, focusHopDepth)
                : { activeSet: new Set(), upSet: new Set(), downSet: new Set(), dist2Set: new Set() };
            nodeEls.forEach(({ el, node, labelEl }) => {
                const circle = el.querySelector('circle');
                if (!focusNodeId || activeSet.has(node.id)) {
                    el.style.opacity = '1';
                    const isFocus = node.id === focusNodeId;
                    circle.setAttribute('stroke-width', isFocus ? '5' : (node.id === centerNode.id ? '3' : '2'));
                    if (isFocus) {
                        circle.setAttribute('stroke', '#fff');
                        circle.setAttribute('filter', 'url(#node-glow)');
                    } else {
                        circle.removeAttribute('filter');
                        let strokeColor = '#fff';
                        if (upSet.has(node.id)) strokeColor = directionColor.upstream;
                        else if (downSet.has(node.id)) strokeColor = directionColor.downstream;
                        else if (dist2Set.has(node.id)) strokeColor = directionColor.dist2;
                        circle.setAttribute('stroke', strokeColor);
                    }
                    if (labelEl) labelEl.style.opacity = '1';
                } else {
                    el.style.opacity = '0.08';
                    circle.setAttribute('stroke-width', '2');
                    circle.setAttribute('stroke', '#fff');
                    circle.removeAttribute('filter');
                    if (labelEl) labelEl.style.opacity = '0';
                }
            });
            edgeEls.forEach(({ el, source, target }) => {
                if (!focusNodeId) {
                    el.setAttribute('opacity', '0.72');
                    el.setAttribute('stroke-width', edgeStyle[el.dataset.type]?.width || 1);
                    el.setAttribute('stroke', edgeStyle[el.dataset.type]?.color || '#94a3b8');
                    return;
                }
                const sIn = activeSet.has(source);
                const tIn = activeSet.has(target);
                if (sIn && tIn) {
                    el.setAttribute('opacity', '1');
                    const isDirect = source === focusNodeId || target === focusNodeId;
                    el.setAttribute('stroke-width', isDirect ? '2.5' : '1.5');
                    let ec = edgeStyle[el.dataset.type]?.color || '#94a3b8';
                    if (el.dataset.type === 'cites') {
                        if (source === focusNodeId) ec = directionColor.upstream;
                        else if (target === focusNodeId) ec = directionColor.downstream;
                    }
                    el.setAttribute('stroke', ec);
                } else {
                    el.setAttribute('opacity', '0.08');
                    el.setAttribute('stroke', edgeStyle[el.dataset.type]?.color || '#94a3b8');
                }
            });
            if (focusNodeId) {
                const n = nodeMap[focusNodeId];
                focusBadge.innerHTML = `聚焦: <strong>${Utils.escapeHtml(n ? n.label : focusNodeId)}</strong> <span style="margin-left:8px;cursor:pointer;text-decoration:underline;">清除</span>`;
                focusBadge.style.display = 'block';
            } else {
                focusBadge.style.display = 'none';
            }
        };

        const setFocus = (nodeId) => {
            focusNodeId = nodeId;
            applyFocus();
        };

        const clearFocus = () => {
            focusNodeId = null;
            applyFocus();
        };
        focusBadge.addEventListener('click', clearFocus);

        // 外部可通过自定义事件触发聚焦（如左侧节点定位）
        container.addEventListener('graph:focus', (e) => {
            const { nodeId, hopDepth } = e.detail || {};
            if (nodeId && nodeMap[nodeId]) {
                if (hopDepth !== undefined) {
                    focusHopDepth = Math.min(Math.max(parseInt(hopDepth, 10) || 1, 1), 2);
                }
                setFocus(nodeId);
            }
        });

        svg.addEventListener('click', (e) => { if (e.target === svg || e.target === mainGroup) clearFocus(); });

        // 鼠标滚轮缩放
        svg.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            const rect = svg.getBoundingClientRect();
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;
            const newScale = Math.max(0.3, Math.min(5, scale * delta));
            tx = mx - (mx - tx) * (newScale / scale);
            ty = my - (my - ty) * (newScale / scale);
            scale = newScale;
            updateTransform();
        }, { passive: false });

        // 拖拽平移
        svg.addEventListener('mousedown', (e) => {
            if (e.target.tagName === 'circle' || e.target.tagName === 'text') return;
            isDragging = true;
            dragStart = { x: e.clientX, y: e.clientY };
            panStart = { x: tx, y: ty };
            svg.style.cursor = 'grabbing';
        });
        window.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            tx = panStart.x + (e.clientX - dragStart.x);
            ty = panStart.y + (e.clientY - dragStart.y);
            updateTransform();
        });
        window.addEventListener('mouseup', () => { isDragging = false; svg.style.cursor = 'grab'; });

        // 控制按钮区（可折叠，避免遮挡图主体）
        const controls = document.createElement('div');
        controls.className = 'graph-controls';

        const togglePanelBtn = document.createElement('button');
        togglePanelBtn.className = 'btn btn-secondary graph-controls-toggle';
        togglePanelBtn.innerHTML = I18n.t('graph.controls.title');
        togglePanelBtn.title = I18n.t('graph.controls.toggle');
        controls.appendChild(togglePanelBtn);

        const panel = document.createElement('div');
        panel.className = 'graph-controls-panel';

        const resetBtn = document.createElement('button');
        resetBtn.className = 'btn btn-sm btn-secondary';
        resetBtn.textContent = I18n.t('graph.controls.reset');
        resetBtn.addEventListener('click', () => { clearFocus(); scale = 1; tx = 0; ty = 0; updateTransform(); updateLabelVisibility(); });
        panel.appendChild(resetBtn);

        const relayoutBtn = document.createElement('button');
        relayoutBtn.className = 'btn btn-sm btn-secondary';
        relayoutBtn.textContent = I18n.t('graph.controls.relayout');
        relayoutBtn.addEventListener('click', () => {
            clearFocus();
            Charts.forceGraph(container, nodes, edges, { ...options, relayout: true });
        });
        panel.appendChild(relayoutBtn);

        const toggleLabelsBtn = document.createElement('button');
        toggleLabelsBtn.className = 'btn btn-sm btn-secondary';
        let labelsAlwaysOn = false;
        toggleLabelsBtn.textContent = I18n.t('graph.controls.show_all_labels');
        toggleLabelsBtn.addEventListener('click', () => {
            labelsAlwaysOn = !labelsAlwaysOn;
            toggleLabelsBtn.textContent = labelsAlwaysOn ? I18n.t('graph.controls.smart_labels') : I18n.t('graph.controls.show_all_labels');
            nodeEls.forEach(({ el, node, labelEl }) => {
                if (!labelEl) return;
                if (labelsAlwaysOn) {
                    labelEl.style.opacity = '1';
                } else {
                    labelEl.style.opacity = shouldShowLabel(node, scale) ? '1' : '0';
                }
            });
            if (!labelsAlwaysOn) updateLabelVisibility();
        });
        panel.appendChild(toggleLabelsBtn);

        const hopBtn = document.createElement('button');
        hopBtn.className = 'btn btn-sm btn-secondary';
        hopBtn.textContent = I18n.t('graph.controls.focus_depth', {depth: focusHopDepth});
        hopBtn.title = '切换聚焦高亮的邻居跳数（1阶/2阶）';
        hopBtn.addEventListener('click', () => {
            focusHopDepth = focusHopDepth === 1 ? 2 : 1;
            hopBtn.textContent = I18n.t('graph.controls.focus_depth', {depth: focusHopDepth});
            applyFocus();
        });
        panel.appendChild(hopBtn);

        controls.appendChild(panel);
        container.appendChild(controls);

        let controlsExpanded = false;
        const updateControlsVisibility = () => {
            controlsExpanded = !controlsExpanded;
            panel.style.display = controlsExpanded ? 'flex' : 'none';
            togglePanelBtn.classList.toggle('active', controlsExpanded);
        };
        togglePanelBtn.addEventListener('click', (e) => { e.stopPropagation(); updateControlsVisibility(); });
        // 默认折叠，减少初始视觉干扰
        panel.style.display = 'none';

        // 图例
        const legend = document.createElement('div');
        legend.className = 'graph-legend';

        const presentTypes = [...new Set(nodes.map(n => n.type))];
        presentTypes.forEach(t => {
            const item = document.createElement('div');
            item.style.display = 'flex';
            item.style.alignItems = 'center';
            item.style.gap = '8px';
            const dot = document.createElement('span');
            dot.style.width = '10px';
            dot.style.height = '10px';
            dot.style.borderRadius = '50%';
            dot.style.background = typeColor[t] || '#94a3b8';
            item.appendChild(dot);
            item.appendChild(document.createTextNode(typeLabel[t] || t));
            legend.appendChild(item);
        });
        // 方向图例：仅引用/合作类边存在方向意义时显示
        const hasDirected = edges.some(e => e.type === 'cites' || e.type === 'coauthored' || e.type === 'institution_collab');
        if (hasDirected) {
            [
                { color: directionColor.upstream, label: I18n.t('graph.legend.upstream') },
                { color: directionColor.downstream, label: I18n.t('graph.legend.downstream') },
                { color: directionColor.dist2, label: I18n.t('graph.legend.two_hop') }
            ].forEach(it => {
                const item = document.createElement('div');
                item.style.display = 'flex';
                item.style.alignItems = 'center';
                item.style.gap = '8px';
                const dot = document.createElement('span');
                dot.style.width = '10px';
                dot.style.height = '10px';
                dot.style.borderRadius = '50%';
                dot.style.background = it.color;
                item.appendChild(dot);
                item.appendChild(document.createTextNode(it.label));
                legend.appendChild(item);
            });
        }
        container.appendChild(legend);

        container.appendChild(svg);
    },

    timelineChart(container, data, options = {}) {
        // data: [{year, paper_count, data_point_count, parse_done_count}]
        container.innerHTML = '';
        if (!data || !data.length) {
            container.innerHTML = '<div class="empty-state">' + I18n.t('timeline.no_data') + '</div>';
            return;
        }
        const width = options.width || container.clientWidth || 800;
        const height = options.height || 340;
        const margin = { top: 36, right: 56, bottom: 50, left: 56 };
        const chartW = width - margin.left - margin.right;
        const chartH = height - margin.top - margin.bottom;

        // 论文数与论文解析完成数：条形图，共用蓝色系（同色不同深浅）
        // 数据点数：点线图，独立的橙色（右 Y 轴）
        const PAPER_COLOR = '#3b82f6';          // 论文数（蓝）
        const PARSE_COLOR = '#1d4ed8';          // 论文解析完成数（深蓝，区分但同色系）
        const DATA_COLOR = '#ea580c';           // 数据点数（橙，区分色系）
        const DATA_LINE_COLOR = '#fb923c';      // 数据点折线（浅橙）

        const maxPaper = Math.max(...data.map(d => Math.max(d.paper_count || 0, d.parse_done_count || 0)), 1);
        const maxData = Math.max(...data.map(d => d.data_point_count || 0), 1);

        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', width);
        svg.setAttribute('height', height);
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);

        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('transform', `translate(${margin.left},${margin.top})`);
        svg.appendChild(g);

        const step = chartW / data.length;
        // 组内宽度：单柱宽度，两柱并排
        const groupW = Math.min(48, step * 0.7);
        const singleW = (groupW - 3) / 2;     // 留 3px 间隙

        // 左 Y 轴（论文数 + 解析完成数）
        const ticks = 5;
        for (let i = 0; i <= ticks; i++) {
            const y = chartH - (i / ticks) * chartH;
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', 0); line.setAttribute('x2', chartW);
            line.setAttribute('y1', y); line.setAttribute('y2', y);
            line.setAttribute('stroke', '#e5e7eb');
            g.appendChild(line);
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', -8); text.setAttribute('y', y + 4);
            text.setAttribute('text-anchor', 'end'); text.setAttribute('font-size', '10');
            text.setAttribute('fill', PAPER_COLOR);
            text.textContent = Math.round((i / ticks) * maxPaper);
            g.appendChild(text);
        }
        // 左 Y 轴标签
        const yLeftLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        yLeftLabel.setAttribute('x', -margin.left + 6);
        yLeftLabel.setAttribute('y', -22);
        yLeftLabel.setAttribute('font-size', '10');
        yLeftLabel.setAttribute('fill', PAPER_COLOR);
        yLeftLabel.setAttribute('font-weight', '600');
        yLeftLabel.textContent = I18n.t('timeline.chart.y_left_label');
        g.appendChild(yLeftLabel);

        // 右 Y 轴（数据点数）
        for (let i = 0; i <= ticks; i++) {
            const y = chartH - (i / ticks) * chartH;
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', chartW + 8); text.setAttribute('y', y + 4);
            text.setAttribute('font-size', '10'); text.setAttribute('fill', DATA_COLOR);
            text.textContent = Math.round((i / ticks) * maxData);
            g.appendChild(text);
        }
        const yRightLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        yRightLabel.setAttribute('x', chartW + 8);
        yRightLabel.setAttribute('y', -22);
        yRightLabel.setAttribute('font-size', '10');
        yRightLabel.setAttribute('fill', DATA_COLOR);
        yRightLabel.setAttribute('font-weight', '600');
        yRightLabel.textContent = I18n.t('timeline.chart.y_right_label');
        g.appendChild(yRightLabel);

        // 数据点折线（点线图）— 先画线（在柱子下方）
        const dataPoints = [];
        data.forEach((d, i) => {
            const cx = i * step + step / 2;
            const cy = chartH - (maxData ? (d.data_point_count / maxData) * chartH : 0);
            dataPoints.push({ x: cx, y: cy, value: d.data_point_count || 0 });
        });
        if (dataPoints.length > 1) {
            const linePath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            linePath.setAttribute('d', 'M ' + dataPoints.map(p => `${p.x},${p.y}`).join(' L '));
            linePath.setAttribute('fill', 'none');
            linePath.setAttribute('stroke', DATA_LINE_COLOR);
            linePath.setAttribute('stroke-width', '1.8');
            linePath.setAttribute('stroke-dasharray', '5 3');
            g.appendChild(linePath);
        }
        // 数据点圆点（实心橙）
        dataPoints.forEach(pt => {
            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('cx', pt.x);
            circle.setAttribute('cy', pt.y);
            circle.setAttribute('r', 3.5);
            circle.setAttribute('fill', DATA_COLOR);
            circle.setAttribute('stroke', '#fff');
            circle.setAttribute('stroke-width', '1');
            g.appendChild(circle);
        });

        // 论文数柱 + 论文解析完成数柱（并排，同蓝色系不同深浅）
        data.forEach((d, i) => {
            const cx = i * step + step / 2;
            const hPaper = maxPaper ? (d.paper_count / maxPaper) * chartH : 0;
            const hParse = maxPaper ? (d.parse_done_count / maxPaper) * chartH : 0;

            // 论文数（蓝色实心）
            const rectP = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rectP.setAttribute('x', cx - groupW / 2);
            rectP.setAttribute('y', chartH - hPaper);
            rectP.setAttribute('width', singleW);
            rectP.setAttribute('height', hPaper);
            rectP.setAttribute('fill', PAPER_COLOR);
            rectP.setAttribute('rx', 2);
            g.appendChild(rectP);

            // 论文解析完成数（深蓝实心）
            const rectD = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rectD.setAttribute('x', cx - groupW / 2 + singleW + 3);
            rectD.setAttribute('y', chartH - hParse);
            rectD.setAttribute('width', singleW);
            rectD.setAttribute('height', hParse);
            rectD.setAttribute('fill', PARSE_COLOR);
            rectD.setAttribute('rx', 2);
            g.appendChild(rectD);

            // X 轴标签
            const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            label.setAttribute('x', cx);
            label.setAttribute('y', chartH + 20);
            label.setAttribute('text-anchor', 'middle');
            label.setAttribute('font-size', '10');
            label.setAttribute('fill', '#6b7280');
            label.textContent = d.year;
            g.appendChild(label);
        });

        // 图例（顶部一行）
        let lx = 0;
        // 论文数（图例：蓝色实心矩形）
        const rectLegendP = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rectLegendP.setAttribute('x', lx); rectLegendP.setAttribute('y', -22);
        rectLegendP.setAttribute('width', 12); rectLegendP.setAttribute('height', 10);
        rectLegendP.setAttribute('fill', PAPER_COLOR);
        rectLegendP.setAttribute('rx', 2);
        g.appendChild(rectLegendP);
        const textP = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        textP.setAttribute('x', lx + 18); textP.setAttribute('y', -14);
        textP.setAttribute('font-size', '11'); textP.setAttribute('fill', '#374151');
        textP.textContent = I18n.t('timeline.chart.paper_count');
        g.appendChild(textP);
        lx += 18 + 4 * 12 + 14;

        // 论文解析完成数（图例：深蓝实心矩形）
        const rectLegendParse = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rectLegendParse.setAttribute('x', lx); rectLegendParse.setAttribute('y', -22);
        rectLegendParse.setAttribute('width', 12); rectLegendParse.setAttribute('height', 10);
        rectLegendParse.setAttribute('fill', PARSE_COLOR);
        rectLegendParse.setAttribute('rx', 2);
        g.appendChild(rectLegendParse);
        const textParse = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        textParse.setAttribute('x', lx + 18); textParse.setAttribute('y', -14);
        textParse.setAttribute('font-size', '11'); textParse.setAttribute('fill', '#374151');
        textParse.textContent = I18n.t('timeline.chart.parse_done');
        g.appendChild(textParse);
        lx += 18 + 8 * 12 + 14;

        // 数据点数（图例：橙色圆点 + 虚线）
        const lineLegend = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        lineLegend.setAttribute('x1', lx); lineLegend.setAttribute('x2', lx + 18);
        lineLegend.setAttribute('y1', -17); lineLegend.setAttribute('y2', -17);
        lineLegend.setAttribute('stroke', DATA_LINE_COLOR);
        lineLegend.setAttribute('stroke-width', '1.8');
        lineLegend.setAttribute('stroke-dasharray', '5 3');
        g.appendChild(lineLegend);
        const dotLegend = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        dotLegend.setAttribute('cx', lx + 9); dotLegend.setAttribute('cy', -17);
        dotLegend.setAttribute('r', 3.5);
        dotLegend.setAttribute('fill', DATA_COLOR);
        dotLegend.setAttribute('stroke', '#fff');
        dotLegend.setAttribute('stroke-width', '1');
        g.appendChild(dotLegend);
        const textD = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        textD.setAttribute('x', lx + 26); textD.setAttribute('y', -14);
        textD.setAttribute('font-size', '11'); textD.setAttribute('fill', '#374151');
        textD.textContent = I18n.t('timeline.chart.data_points');
        g.appendChild(textD);

        container.appendChild(svg);
    }
};

// OpenIsle integration export. The graph implementation above is kept
// byte-for-byte compatible with the original literature workspace.
window.OpenIsleLiteratureCharts = Charts;
