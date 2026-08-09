// 工具函数
const Utils = {
    escapeHtml(str) {
        if (str == null) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    },

    formatDate(dateStr) {
        if (!dateStr) return '未知';
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleDateString('zh-CN');
    },

    joinAuthors(authors) {
        if (!authors) return '';
        if (typeof authors === 'string') return authors;
        if (Array.isArray(authors)) {
            return authors.map(a => {
                if (typeof a === 'string') return a;
                return a.name || `${a.given || ''} ${a.family || ''}`.trim();
            }).filter(Boolean).join(', ');
        }
        return '';
    },

    joinKeywords(keywords) {
        if (!keywords) return '';
        if (typeof keywords === 'string') return keywords;
        if (Array.isArray(keywords)) return keywords.join(', ');
        return '';
    },

    truncate(str, maxLen = 200) {
        if (!str) return '';
        const s = String(str);
        if (s.length <= maxLen) return s;
        return s.slice(0, maxLen) + '...';
    },

    debounce(fn, wait = 300) {
        let timer;
        return (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => fn(...args), wait);
        };
    },

    buildQueryString(params) {
        if (!params || typeof params !== 'object') return '';
        const parts = [];
        for (const [k, v] of Object.entries(params)) {
            if (v === undefined || v === null || v === '') continue;
            parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(v)}`);
        }
        return parts.length ? '?' + parts.join('&') : '';
    },

    parseAuthorsFromString(s) {
        if (!s) return [];
        return s.split(';').map(x => x.trim()).filter(Boolean);
    },

    renderHighlight(html) {
        // 后端已用 <em> 包裹高亮词
        return html;
    },

    async pollProgress(taskId, onUpdate, onDone) {
        const poll = async () => {
            try {
                const res = await API.getProgress(taskId);
                onUpdate(res);
                if (res.status === 'done' || res.status === 'failed') {
                    onDone(res);
                    return;
                }
                setTimeout(poll, 800);
            } catch (err) {
                onUpdate({ status: 'failed', message: '轮询失败: ' + err.message });
                onDone({ status: 'failed', message: err.message });
            }
        };
        poll();
    }
};

// 全局 Toast
function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 200);
    }, duration);
}
