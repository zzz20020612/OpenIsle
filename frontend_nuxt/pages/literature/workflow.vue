<template>
  <main class="paper-shell">
    <div class="paper-container literature-workflow-container">
      <header class="paper-workspace-header">
        <div>
          <div class="paper-page-eyebrow">Knowledge Base / Administration</div>
          <h1 class="paper-page-title">Literature processing workflow</h1>
          <p class="paper-page-description">Collect metadata, download open PDFs, parse full text, and extract knowledge. Every action is recorded in OpenIsle.</p>
        </div>
        <div class="workflow-actions"><NuxtLink class="paper-button" to="/literature">View knowledge base</NuxtLink><button class="paper-button" @click="refresh">Refresh</button></div>
      </header>

      <div v-if="message" class="workflow-message" :class="{ error: failed, partial }">{{ message }}</div>
      <section v-if="activeTask" class="paper-panel task-progress" aria-live="polite">
        <div class="task-progress-heading">
          <div>
            <strong>{{ taskStatusLabel }}</strong>
            <p>{{ activeTask.message || 'Waiting for the processing service…' }}</p>
          </div>
          <b>{{ Math.round(Number(activeTask.progress || 0)) }}%</b>
        </div>
        <div class="task-progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="Number(activeTask.progress || 0)">
          <span :style="{ width: `${Math.max(0, Math.min(100, Number(activeTask.progress || 0)))}%` }" />
        </div>
        <dl v-if="taskResultRows.length" class="task-result-grid">
          <div v-for="row in taskResultRows" :key="row.label"><dt>{{ row.label }}</dt><dd>{{ row.value }}</dd></div>
        </dl>
      </section>
      <section class="workflow-grid">
        <article class="paper-panel workflow-card">
          <h2>Run complete pipeline</h2>
          <label>Search topic<input v-model="pipeline.keyword" placeholder="e.g. climate adaptation" /></label>
          <label>Metadata source<select v-model="pipeline.collection_source"><option v-for="source in collectionSources" :key="source.value" :value="source.value">{{ source.label }}</option></select></label>
          <div class="field-row"><label>Records/page<input v-model.number="pipeline.rows" type="number" min="1" max="100" /></label><label>Pages<input v-model.number="pipeline.max_pages" type="number" min="1" max="20" /></label></div>
          <div class="field-row"><label>From year<input v-model="pipeline.year_from" placeholder="2020" /></label><label>To year<input v-model="pipeline.year_to" placeholder="2026" /></label></div>
          <button class="primary-action" :disabled="busy || !pipeline.keyword.trim()" @click="run('/pipeline/run', pipeline)">Collect, parse and extract</button>
        </article>

        <article class="paper-panel workflow-card">
          <h2>Individual stages</h2>
          <p>Use these controls to resume or repeat one stage without restarting the whole workflow.</p>
          <div class="stage-actions">
            <button :disabled="busy" @click="run('/parse', { source: 'all', limit: 15, force: false })">Parse pending PDFs</button>
            <button :disabled="busy" @click="run('/extract', {})">Extract pending knowledge</button>
            <button :disabled="busy" @click="run('/rebuild', {})">Rebuild search index</button>
          </div>
          <p class="readiness" :class="{ missing: !embeddingConfigured }"><strong>Semantic search:</strong> {{ embeddingConfigured ? 'ready' : 'waiting for EMBEDDING_API_KEY' }}</p>
          <p class="hint">Keyword search, metadata collection, PDF parsing, and LLM extraction work without the embedding key.</p>
        </article>
      </section>

      <section class="paper-panel advanced-panel">
        <div><h2>Advanced maintenance</h2><p>Quality review, author merging, connection checks, single-paper sync, and workflow settings remain available through the audited bridge.</p></div>
        <label>Operation<select v-model="advancedPath"><option v-for="item in advancedOperations" :key="item.path" :value="item.path">{{ item.label }}</option></select></label>
        <label>JSON parameters<textarea v-model="advancedBody" rows="5" spellcheck="false" /></label>
        <button class="primary-action" :disabled="busy" @click="runAdvanced">Run advanced operation</button>
      </section>

      <section class="paper-panel jobs-panel">
        <div class="panel-heading"><div><h2>Recent processing jobs</h2><p>{{ statsText }}</p></div><button :disabled="busy" @click="run('/jobs/archive', { days: 7, batch: 1000 })">Archive old jobs</button></div>
        <div v-if="loading" class="empty">Loading jobs...</div>
        <div v-else-if="!jobs.length" class="empty">No processing jobs yet.</div>
        <div v-else class="job-table-wrap"><table><thead><tr><th>Stage</th><th>Paper</th><th>Status</th><th>Started</th><th>Message</th><th></th></tr></thead><tbody><tr v-for="job in jobs" :key="job.id"><td>{{ job.stage || job.job_type || '—' }}</td><td>{{ job.paper_id || '—' }}</td><td><span class="status" :class="String(job.status).toLowerCase()">{{ job.status }}</span></td><td>{{ formatTime(job.started_at || job.created_at) }}</td><td>{{ job.error_message || job.message || '—' }}</td><td><button v-if="String(job.status).toLowerCase() === 'failed' && job.paper_id" @click="retry(job)">Retry</button></td></tr></tbody></table></div>
      </section>
    </div>
  </main>
</template>

<script setup>
import '~/assets/paper-platform.css'
import { authState, getToken, loadCurrentUser } from '~/utils/auth'

definePageMeta({ middleware: 'auth-client', keepalive: false })
useHead({ title: 'Knowledge Workflow - OpenIsle' })

const config = useRuntimeConfig()
const jobs = ref([])
const jobStats = ref({})
const loading = ref(true)
const busy = ref(false)
const message = ref('')
const failed = ref(false)
const partial = ref(false)
const activeTask = ref(null)
const embeddingConfigured = ref(false)
const collectionSources = [
  { value: 'crossref', label: 'Crossref (recommended)' },
  { value: 'all_open', label: 'All open sources' },
  { value: 'arxiv', label: 'arXiv' },
  { value: 'pmc', label: 'PubMed Central' },
  { value: 'openalex', label: 'OpenAlex' },
  { value: 'semanticscholar', label: 'Semantic Scholar' },
  { value: 'pubmed', label: 'PubMed' },
  { value: 'wos', label: 'Web of Science (API key required)' },
  { value: 'scopus', label: 'Scopus (API key required)' },
]
const pipeline = reactive({ keyword: '', collection_source: 'crossref', rows: 20, max_pages: 3, year_from: '', year_to: '', journal: '', parse_source: 'all', parse_limit: 15 })
const advancedOperations = [
  { path:'/collect',label:'Collect metadata only',body:{ keyword:'',collection_source:'crossref',rows:20,max_pages:3,year_from:'',year_to:'',journal:'' } },
  { path:'/sync',label:'Synchronize one paper',body:{ paper_id:1 } },
  { path:'/quality/re_extract',label:'Re-extract one low-quality paper',body:{ paper_id:1 } },
  { path:'/authors/merge',label:'Merge duplicate authors',body:{ primary_id:1,duplicate_ids:[] } },
  { path:'/test/connection',label:'Test external service connection',body:{ service:'llm' } },
  { path:'/workflow/settings',label:'Update workflow settings',body:{} },
]
const advancedPath = ref(advancedOperations[0].path)
const advancedBody = ref(JSON.stringify(advancedOperations[0].body, null, 2))
watch(advancedPath, value => { advancedBody.value = JSON.stringify(advancedOperations.find(item => item.path === value)?.body || {}, null, 2) })
const statsText = computed(() => Object.entries(jobStats.value || {}).map(([key, value]) => `${key}: ${value}`).join(' · ') || 'Current task history')
const taskStatusLabel = computed(() => {
  const status = String(activeTask.value?.status || 'pending').toLowerCase()
  if (status === 'done') return partial.value ? 'Completed with warnings' : 'Pipeline completed'
  if (status === 'failed') return 'Pipeline failed'
  if (status === 'running') return 'Pipeline running'
  return 'Pipeline queued'
})
const taskResultRows = computed(() => {
  const result = activeTask.value?.result
  if (!result || typeof result !== 'object') return []
  const rows = []
  if (result.collect) {
    rows.push({ label: 'Metadata', value: `${result.collect.inserted || 0} new · ${(result.collect.paper_ids || []).length} matched` })
  }
  if (result.parse) {
    rows.push({ label: 'PDF parsing', value: `${result.parse.success || 0} succeeded · ${result.parse.skipped || 0} skipped · ${result.parse.failed || 0} failed` })
  }
  if (result.extract) {
    rows.push({ label: 'Knowledge extraction', value: `${result.extract.knowledge_cards || 0} cards · ${result.extract.methods || 0} methods · ${result.extract.data_points || 0} data points · ${result.extract.errors || 0} errors` })
  }
  if (!rows.length) {
    Object.entries(result).forEach(([label, value]) => {
      if (value == null || typeof value === 'object') return
      rows.push({ label: label.replaceAll('_', ' '), value: String(value) })
    })
  }
  return rows
})
const endpoint = (path) => `${config.public.apiBaseUrl}/api/literature/admin${path}`
const headers = () => ({ Authorization: `Bearer ${getToken()}` })

const request = (path, options = {}) => $fetch(endpoint(path), { ...options, headers: { ...headers(), ...(options.headers || {}) } })
const refresh = async () => {
  loading.value = true
  try {
    const [jobResult, statsResult, workflowSettings] = await Promise.all([request('/jobs?limit=100'), request('/jobs/stats'), request('/workflow/settings')])
    jobs.value = jobResult.jobs || jobResult.items || jobResult || []
    jobStats.value = statsResult
    embeddingConfigured.value = Boolean(workflowSettings.embedding_api_key_configured || workflowSettings.EMBEDDING_API_KEY_configured || workflowSettings.embedding?.configured)
  } catch (cause) {
    failed.value = true
    message.value = cause?.data?.message || cause?.data?.error || cause?.message || 'Unable to load the literature workflow.'
  } finally { loading.value = false }
}
let pollGeneration = 0
const delay = (milliseconds) => new Promise(resolve => setTimeout(resolve, milliseconds))
const pollTask = async (taskId, generation) => {
  while (generation === pollGeneration) {
    const task = await request(`/progress/${encodeURIComponent(taskId)}`)
    activeTask.value = task
    const status = String(task.status || '').toLowerCase()
    if (status === 'done') return task
    if (status === 'failed') throw new Error(task.error || task.message || 'The processing task failed.')
    await delay(1200)
  }
  throw new Error('Task monitoring was cancelled.')
}
const hasPartialFailures = (result) => Number(result?.parse?.failed || 0) > 0 || Number(result?.extract?.errors || 0) > 0 || result?.status === 'partial'
const run = async (path, body) => {
  const generation = ++pollGeneration
  busy.value = true; failed.value = false; partial.value = false; message.value = ''; activeTask.value = null
  try {
    const result = await request(path, { method: 'POST', body })
    if (result.task_id) {
      activeTask.value = { task_id: result.task_id, status: 'pending', progress: 0, message: 'Task accepted by the processing service.' }
      const completed = await pollTask(result.task_id, generation)
      partial.value = hasPartialFailures(completed.result)
      message.value = partial.value
        ? 'Processing finished, but some PDFs or knowledge fields could not be completed. Review the result and retry failed records below.'
        : 'Processing completed successfully. The new literature records are now available in the knowledge base.'
    } else {
      message.value = 'Operation completed.'
    }
    await refresh()
  } catch (cause) {
    if (generation !== pollGeneration) return
    failed.value = true
    message.value = cause?.data?.message || cause?.data?.error || cause?.message || 'Operation failed.'
  } finally {
    if (generation === pollGeneration) busy.value = false
  }
}
const retry = (job) => run('/retry', { paper_id: job.paper_id, stage: job.stage || job.job_type, job_id: job.id })
const runAdvanced = async () => { try { await run(advancedPath.value, JSON.parse(advancedBody.value || '{}')) } catch { failed.value = true; message.value = 'Advanced parameters must be valid JSON.' } }
const formatTime = (value) => value ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(/Z|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`)) : '—'

onMounted(async () => {
  if (!authState.role) await loadCurrentUser()
  if (authState.role !== 'ADMIN') return navigateTo('/literature', { replace: true })
  await refresh()
})
onBeforeUnmount(() => { pollGeneration++ })
</script>

<style scoped>
.literature-workflow-container { max-width: 1240px; }
.workflow-actions,.stage-actions,.field-row,.panel-heading { display:flex; gap:10px; }
.workflow-actions { flex-wrap:wrap; }
.workflow-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; margin-bottom:14px; }
.workflow-card,.jobs-panel,.advanced-panel { padding:20px; }
.workflow-card h2,.panel-heading h2 { margin:0 0 8px; font-family:Georgia,serif; font-weight:500; }
.workflow-card label { display:grid; gap:5px; margin:12px 0; color:var(--paper-muted); font-size:12px; font-weight:700; }
.workflow-card input,.workflow-card select { min-height:40px; border:1px solid var(--paper-line); padding:8px 10px; background:#fff; color:var(--paper-ink); }
.field-row label { flex:1; }
.primary-action,.stage-actions button,.jobs-panel button { min-height:38px; border:1px solid var(--paper-teal); padding:8px 12px; background:var(--paper-teal); color:white; font-weight:750; cursor:pointer; }
button:disabled { opacity:.5; cursor:wait; }
.stage-actions { flex-wrap:wrap; margin:20px 0; }
.readiness { padding:10px; background:#edf7f3; color:#22624e; }.readiness.missing { background:#fff6e8; color:#835713; }.hint { color:var(--paper-muted); font-size:12px; }
.advanced-panel{display:grid;grid-template-columns:1fr minmax(220px,.45fr) minmax(300px,.75fr) auto;align-items:end;gap:12px;margin-bottom:14px}.advanced-panel h2{margin:0 0 6px;font-family:Georgia,serif;font-weight:500}.advanced-panel p{margin:0;color:var(--paper-muted);font-size:12px}.advanced-panel label{display:grid;gap:5px;color:var(--paper-muted);font-size:12px;font-weight:700}.advanced-panel select,.advanced-panel textarea{border:1px solid var(--paper-line);padding:8px;background:#fff;font:inherit}.advanced-panel textarea{font-family:monospace;font-size:11px}
.workflow-message { margin-bottom:14px; border:1px solid #a9cfbf; padding:11px 14px; background:#eff8f4; color:#245e49; }.workflow-message.error { border-color:#e0b5af; background:#fff7f6; color:#923b32; }
.workflow-message.partial { border-color:#e3c27d; background:#fff8e9; color:#795517; }
.task-progress{padding:18px 20px;margin-bottom:14px}.task-progress-heading{display:flex;align-items:start;justify-content:space-between;gap:16px}.task-progress-heading p{margin:4px 0 0;color:var(--paper-muted);font-size:12px}.task-progress-heading b{color:var(--paper-green);font-size:22px}.task-progress-track{height:8px;margin:14px 0;border-radius:999px;background:var(--paper-line);overflow:hidden}.task-progress-track span{display:block;height:100%;border-radius:inherit;background:var(--paper-teal);transition:width .25s ease}.task-result-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:12px 0 0}.task-result-grid div{padding:10px;border:1px solid var(--paper-line);background:var(--paper-surface-soft)}.task-result-grid dt{color:var(--paper-soft);font-size:10px;font-weight:800;text-transform:uppercase}.task-result-grid dd{margin:4px 0 0;color:var(--paper-ink);font-size:12px}
.panel-heading { justify-content:space-between; align-items:start; }.panel-heading p { margin:0; color:var(--paper-muted); font-size:12px; }
.job-table-wrap { overflow:auto; } table { width:100%; border-collapse:collapse; font-size:12px; } th,td { padding:10px; border-top:1px solid var(--paper-line); text-align:left; vertical-align:top; } .status { font-weight:800; text-transform:uppercase; }.status.failed { color:#a33d34; }.status.completed,.status.success { color:#236b52; }.empty { padding:40px; text-align:center; color:var(--paper-muted); }
@media(max-width:1000px){.advanced-panel{grid-template-columns:1fr 1fr}.workflow-grid{grid-template-columns:1fr}.task-result-grid{grid-template-columns:1fr}}
</style>
