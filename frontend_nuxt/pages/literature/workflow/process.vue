<template>
  <main class="paper-shell">
    <div class="paper-container admin-container">
      <header class="paper-workspace-header">
        <div>
          <div class="paper-page-eyebrow">Knowledge Base / Administration</div>
          <h1 class="paper-page-title">Collect and process</h1>
          <p class="paper-page-description">
            Run the complete online literature pipeline or execute one processing stage.
          </p>
        </div>
      </header>
      <LiteratureKnowledgeNav />
      <LiteratureAdminNav />
      <p v-if="message" class="admin-notice" :class="{ error }">{{ message }}</p>
      <section class="quality-grid">
        <form class="paper-panel admin-card" @submit.prevent="run('/pipeline/run', pipeline)">
          <h2>Complete pipeline</h2>
          <div class="admin-form">
            <label class="wide">Search topic<input v-model="pipeline.keyword" required /></label
            ><label
              >Source<select v-model="pipeline.collection_source">
                <option v-for="s in sources" :key="s" :value="s">{{ s }}</option>
              </select></label
            ><label
              >Records per page<input
                v-model.number="pipeline.rows"
                type="number"
                min="1"
                max="100" /></label
            ><label
              >Maximum pages<input
                v-model.number="pipeline.max_pages"
                type="number"
                min="1"
                max="20" /></label
            ><label>From year<input v-model="pipeline.year_from" /></label
            ><label>To year<input v-model="pipeline.year_to" /></label
            ><label>Journal<input v-model="pipeline.journal" /></label
            ><label
              >PDF source<select v-model="pipeline.parse_source">
                <option v-for="s in parseSources" :key="s.value" :value="s.value">
                  {{ s.label }}
                </option>
              </select></label
            ><label
              >Parse limit<input
                v-model.number="pipeline.parse_limit"
                type="number"
                min="1"
                max="50"
            /></label>
          </div>
          <button class="admin-action" :disabled="busy">
            Collect, download, parse and extract
          </button>
        </form>
        <form class="paper-panel admin-card" @submit.prevent="run('/collect', collect)">
          <h2>Metadata collection only</h2>
          <div class="admin-form">
            <label class="wide">Search topic<input v-model="collect.keyword" required /></label
            ><label
              >Source<select v-model="collect.collection_source">
                <option v-for="s in sources" :key="s" :value="s">{{ s }}</option>
              </select></label
            ><label
              >Records per page<input
                v-model.number="collect.rows"
                type="number"
                min="1"
                max="100" /></label
            ><label
              >Maximum pages<input
                v-model.number="collect.max_pages"
                type="number"
                min="1"
                max="20" /></label
            ><label>From year<input v-model="collect.year_from" /></label
            ><label>To year<input v-model="collect.year_to" /></label
            ><label>Journal<input v-model="collect.journal" /></label>
          </div>
          <button class="admin-action" :disabled="busy">Collect metadata</button>
        </form>
      </section>
      <section class="paper-panel admin-card">
        <h2>Individual processing stages</h2>
        <div class="stage-grid">
          <label
            >PDF source<select v-model="parse.source">
              <option v-for="s in parseSources" :key="s.value" :value="s.value">
                {{ s.label }}
              </option>
            </select></label
          ><label
            >Batch limit<input v-model.number="parse.limit" type="number" min="1" max="50" /></label
          ><label><input v-model="parse.force" type="checkbox" /> Reparse completed PDFs</label
          ><button class="admin-action" @click="run('/parse', parse)">Parse PDFs</button
          ><button class="admin-action" @click="run('/extract', {})">
            Extract pending knowledge</button
          ><button class="admin-action" @click="rebuildIndex">Rebuild search index</button>
        </div>
      </section>
      <section class="paper-panel admin-card">
        <h2>Synchronize one paper</h2>
        <div class="sync-row">
          <input
            v-model.number="paperId"
            type="number"
            min="1"
            placeholder="Literature paper ID"
          /><button
            class="admin-action"
            :disabled="!paperId || busy"
            @click="run('/sync', { paper_id: paperId })"
          >
            Synchronize paper
          </button>
        </div>
      </section>
      <section v-if="task" class="paper-panel admin-card">
        <h2>Current task</h2>
        <p>{{ task.message || task.status }}</p>
        <progress max="100" :value="task.progress || 0" /><AdminObjectTable :value="task.result" />
      </section>
    </div>
  </main>
</template>
<script setup>
import '~/assets/paper-platform.css'
import { authState, loadCurrentUser } from '~/utils/auth'
definePageMeta({ middleware: 'auth-client' })
useHead({ title: 'Literature Processing - OpenIsle' })
const api = useLiteratureAdmin(),
  sources = [
    'crossref',
    'all_open',
    'arxiv',
    'pmc',
    'openalex',
    'semanticscholar',
    'pubmed',
    'wos',
    'scopus',
  ],
  parseSources = [
    { value: 'all', label: 'All sources' },
    { value: 'arxiv', label: 'arXiv' },
    { value: 'crossref', label: 'Crossref' },
    { value: 'semantic_scholar', label: 'Semantic Scholar' },
    { value: 'pmc', label: 'PubMed Central' },
  ],
  pipeline = reactive({
    keyword: '',
    collection_source: 'crossref',
    rows: 20,
    max_pages: 2,
    year_from: '',
    year_to: '',
    journal: '',
    parse_source: 'all',
    parse_limit: 5,
  }),
  collect = reactive({
    keyword: '',
    collection_source: 'crossref',
    rows: 20,
    max_pages: 2,
    year_from: '',
    year_to: '',
    journal: '',
  }),
  parse = reactive({ source: 'all', limit: 5, force: false }),
  paperId = ref(null),
  busy = ref(false),
  message = ref(''),
  error = ref(false),
  task = ref(null)
const delay = (ms) => new Promise((r) => setTimeout(r, ms))
const terminalStatuses = new Set([
  'done',
  'completed',
  'success',
  'failed',
  'permanent_failed',
  'cancelled',
  'canceled',
  'skipped',
  'superseded',
])
const failedStatuses = new Set(['failed', 'permanent_failed', 'cancelled', 'canceled'])
const ensure = async () => {
  if (!authState.role) await loadCurrentUser()
  if (authState.role !== 'ADMIN') return navigateTo('/literature/workflow')
}
const run = async (path, body) => {
  busy.value = true
  message.value = ''
  error.value = false
  task.value = null
  try {
    const accepted = await api.post(path, body)
    if (accepted.task_id) {
      let status = ''
      do {
        task.value = await api.get(`/progress/${accepted.task_id}`)
        status = String(task.value.status || '').toLowerCase()
        if (!terminalStatuses.has(status)) await delay(1200)
      } while (!terminalStatuses.has(status))
      if (failedStatuses.has(status))
        throw new Error(task.value.error || task.value.error_message || task.value.message)
    }
    message.value = 'Operation completed.'
  } catch (e) {
    error.value = true
    message.value = e?.data?.message || e?.data?.error || e.message
  } finally {
    busy.value = false
  }
}
const rebuildIndex = () => {
  if (
    !window.confirm(
      'Rebuild the complete literature search index now? Search results may be temporarily incomplete while this runs.',
    )
  )
    return
  run('/rebuild', {})
}
onMounted(ensure)
</script>
<style scoped src="~/assets/literature-admin.css"></style>
<style scoped>
.quality-grid form {
  margin: 0;
}
.stage-grid {
  display: flex;
  align-items: end;
  flex-wrap: wrap;
  gap: 12px;
}
.stage-grid label {
  display: grid;
  gap: 5px;
  color: var(--paper-muted);
  font-size: 12px;
  font-weight: 750;
}
.stage-grid input,
.stage-grid select,
.sync-row input {
  min-height: 38px;
  border: 1px solid var(--paper-line);
  padding: 8px;
  background: #fff;
}
.sync-row {
  display: flex;
  gap: 10px;
}
.sync-row input {
  min-width: 280px;
}
progress {
  width: 100%;
  height: 12px;
}
</style>
