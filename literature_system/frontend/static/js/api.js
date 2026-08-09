// API 封装
const API_BASE = '';

async function request(url, options = {}) {
    const res = await fetch(API_BASE + url, options);
    if (!res.ok) {
        const text = await res.text();
        let errMsg = `HTTP ${res.status}`;
        try {
            const data = JSON.parse(text);
            errMsg = data.error || errMsg;
        } catch {}
        throw new Error(errMsg);
    }
    return res.json();
}

const API = {
    health() {
        return request('/health');
    },
    stats() {
        return request('/stats');
    },
    search(params) {
        return request('/search' + Utils.buildQueryString(params));
    },
    aggregate(params) {
        return request('/aggregate' + Utils.buildQueryString(params));
    },
    vectorSearch(params) {
        return request('/vector/search' + Utils.buildQueryString(params));
    },
    vectorStats(params) {
        return request('/vector/stats' + Utils.buildQueryString(params));
    },
    hybridSearch(params) {
        return request('/hybrid/search' + Utils.buildQueryString(params));
    },
    getPaper(id) {
        return request(`/paper/${id}`);
    },
    getPaperSimilar(id, top_k = 5) {
        return request(`/paper/${id}/similar` + Utils.buildQueryString({ top_k }));
    },
    getPaperKnowledge(id) {
        return request(`/paper/${id}/knowledge`);
    },
    getPaperMethods(id) {
        return request(`/paper/${id}/methods`);
    },
    getPaperDataPoints(id) {
        return request(`/paper/${id}/data_points`);
    },
    getPaperCitations(id) {
        return request(`/paper/${id}/citations`);
    },
    getPaperAuthors(id) {
        return request(`/paper/${id}/authors`);
    },
    compareMetric(metric_name, top_k = 20) {
        return request('/compare/metric' + Utils.buildQueryString({ metric_name, top_k }));
    },
    listAuthors(params) {
        return request('/authors/list' + Utils.buildQueryString(params));
    },
    getAuthor(author_id) {
        return request(`/author/${author_id}`);
    },
    getAuthorPapers(author_id, params = {}) {
        return request(`/author/${author_id}/papers` + Utils.buildQueryString(params));
    },
    getAuthorNetwork(author_id, max_nodes = 50) {
        return request(`/author/${author_id}/network` + Utils.buildQueryString({ max_nodes }));
    },
    getInstitutionNetwork(params) {
        return request('/institution/network' + Utils.buildQueryString(params));
    },
    rebuild() {
        return request('/rebuild', { method: 'POST' });
    },
    sync(paper_id) {
        return request('/sync', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paper_id })
        });
    },
    getProgress(taskId) {
        return request(`/progress/${taskId}`);
    },
    getGraph(params) {
        return request('/graph' + Utils.buildQueryString(params));
    },
    getGraphDiagnostics(params) {
        return request('/graph/diagnostics' + Utils.buildQueryString(params));
    },
    getPapersList(params) {
        return request('/papers/list' + Utils.buildQueryString(params));
    },
    getDataPointsList(params) {
        return request('/data_points/list' + Utils.buildQueryString(params));
    },
    getKnowledgeList(params) {
        return request('/knowledge/list' + Utils.buildQueryString(params));
    },
    getMethodsList(params) {
        return request('/methods/list' + Utils.buildQueryString(params));
    },
    getWorkflowSettings() {
        return request('/workflow/settings');
    },
    setWorkflowSettings(data) {
        return request('/workflow/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    },
    getTimeline(params) {
        return request('/timeline' + Utils.buildQueryString(params));
    },
    getJobs(params) {
        return request('/jobs' + Utils.buildQueryString(params));
    },
    getJobStats() {
        return request('/jobs/stats');
    },
    archiveJobs(data) {
        return request('/jobs/archive', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data || {}) });
    },
    collect(data) {
        return request('/collect', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    },
    parse(data) {
        return request('/parse', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    },
    extract() {
        return request('/extract', { method: 'POST' });
    },
    retryJob(data) {
        return request('/retry', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    },
    getQualityStats() {
        return request('/quality/stats');
    },
    getQualityLowQuality(params) {
        return request('/quality/low_quality' + Utils.buildQueryString(params));
    },
    getQualityPromptCompare(params) {
        return request('/quality/prompt_compare' + Utils.buildQueryString(params));
    },
    reExtract(paper_id) {
        return request('/quality/re_extract', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ paper_id }) });
    },
    mergeAuthors(primary_id, duplicate_ids) {
        return request('/authors/merge', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ primary_id, duplicate_ids }) 
        });
    },
    testConnection(data) {
        return request('/test/connection', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(data) 
        });
    },
    pipelineRun(data) {
        return request('/pipeline/run', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(data) 
        });
    }
};
