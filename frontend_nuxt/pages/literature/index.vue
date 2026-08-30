<template>
  <main class="paper-shell">
    <div class="paper-container literature-container">
      <header class="paper-workspace-header">
        <div>
          <div class="paper-page-eyebrow">Knowledge Base</div>
          <h1 class="paper-page-title">Explore the existing literature corpus</h1>
          <p class="paper-page-description">
            Search published literature and inspect the structured knowledge extracted from each record.
            These records are separate from author submissions.
          </p>
        </div>
        <div class="literature-header-actions">
          <NuxtLink class="paper-button" to="/papers">Submission papers</NuxtLink>
          <NuxtLink class="paper-button" to="/literature/explore">Advanced exploration</NuxtLink>
          <NuxtLink class="paper-button primary" to="/literature/workflow">Knowledge workflow</NuxtLink>
        </div>
      </header>

      <LiteratureKnowledgeNav />

      <nav class="knowledge-tabs" aria-label="Knowledge base record types">
        <NuxtLink class="active" to="/literature">Papers</NuxtLink>
        <NuxtLink to="/literature/explore?mode=data">Data points</NuxtLink>
        <NuxtLink to="/literature/explore?mode=knowledge">Knowledge</NuxtLink>
        <NuxtLink to="/literature/explore?mode=methods">Methods</NuxtLink>
      </nav>

      <section class="paper-panel advanced-search">
        <div class="advanced-heading"><div><strong>Advanced field search</strong><span>The original system supports up to six field rows.</span></div><button type="button" @click="advancedOpen=!advancedOpen">{{ advancedOpen?'Collapse':'Expand' }}</button></div>
        <div v-if="advancedOpen" class="advanced-body">
          <div v-for="(row,index) in fieldRows" :key="index" class="field-row"><select v-model="row.field"><option v-for="field in searchFields" :key="field.id" :value="field.id">{{ field.label }}</option></select><input v-model="row.value" :placeholder="row.field==='year'?'e.g. 2020-2024':`Enter ${searchFields.find(item=>item.id===row.field)?.label.toLowerCase()}`" @keydown.enter.prevent="applyAdvancedSearch" /><button type="button" :disabled="fieldRows.length===1" aria-label="Remove field" @click="removeField(index)">×</button></div>
          <div class="advanced-controls"><label>Search mode<select v-model="searchMode"><option value="keyword">Keyword</option><option value="phrase">Phrase</option><option value="fuzzy">Fuzzy</option><option value="vector">Vector</option><option value="hybrid">Hybrid</option></select></label><button class="paper-button" type="button" :disabled="fieldRows.length>=6" @click="fieldRows.push({field:'all',value:''})">Add field</button><button class="paper-button primary" type="button" @click="applyAdvancedSearch">Search</button><button class="paper-button" type="button" @click="clearAdvanced">Clear</button></div>
          <div class="tier-row"><span>Journal tier</span><label v-for="tier in tiers" :key="tier.id"><input v-model="journalTiers" type="checkbox" :value="tier.id" /> {{ tier.label }}</label></div>
          <p v-if="['vector','hybrid'].includes(searchMode)" class="vector-hint">Vector and hybrid modes use the original embedding service. They require indexed vectors and an Embedding API key.</p>
        </div>
      </section>

      <form class="literature-search paper-panel" @submit.prevent="applySearch">
        <label>
          <span>Search title, abstract, or journal</span>
          <input v-model="searchInput" type="search" placeholder="e.g. deep learning" />
        </label>
        <label class="literature-sort">
          <span>Sort</span>
          <select v-model="sort">
            <option value="year_desc">Newest first</option>
            <option value="year_asc">Oldest first</option>
            <option value="citations_desc">Most cited</option>
            <option value="title_asc">Title A–Z</option>
          </select>
        </label>
        <label class="literature-sort">
          <span>Processing state</span>
          <select v-model="stateFilter">
            <option value="">All states</option>
            <option value="complete">Complete</option>
            <option value="processing">Processing</option>
            <option value="retryable">Needs retry</option>
            <option value="incomplete">Incomplete</option>
            <option value="terminal">Cannot process</option>
          </select>
        </label>
        <button class="paper-button primary" type="submit">Search</button>
      </form>

      <section v-if="pending" class="paper-card literature-state" aria-live="polite">
        Loading literature records…
      </section>

      <section v-else-if="error" class="paper-card literature-state unavailable" role="alert">
        <strong>Knowledge service unavailable</strong>
        <p>
          The literature service is not running or cannot be reached. Submission and screening remain
          available.
        </p>
        <button class="paper-button" type="button" @click="refresh()">Try again</button>
      </section>

      <template v-else>
        <div class="literature-summary">
          <strong>{{ total }}</strong> literature records
          <span v-if="query">matching “{{ query }}”</span>
          <span> · {{ papers.length }} shown</span>
        </div>

        <section v-if="papers.length" class="literature-list paper-panel">
          <NuxtLink
            v-for="paper in papers"
            :key="paper.id"
            class="literature-row"
            :to="`/literature/${paper.id}`"
          >
            <div class="literature-row-main">
              <h2>{{ paper.title || 'Untitled literature record' }}</h2>
              <p>{{ formatAuthors(paper.author) }}</p>
              <div class="paper-meta-row">
                <span v-if="paper.journal" class="paper-pill subject">{{ paper.journal }}</span>
                <span v-if="paper.year" class="paper-pill">{{ paper.year }}</span>
                <span v-if="paper.source" class="paper-pill">{{ paper.source }}</span>
                <span v-if="paper.language" class="paper-pill">{{ paper.language }}</span>
                <span class="paper-pill literature-status" :class="paper.completeness?.state">
                  {{ completenessLabel(paper.completeness) }}
                </span>
              </div>
            </div>
            <div class="literature-citations">
              <strong>{{ Number(paper.citation_count || 0).toLocaleString() }}</strong>
              <span>citations</span>
            </div>
          </NuxtLink>
        </section>

        <section v-else class="paper-card literature-state">
          <strong>No literature records found</strong>
          <p>Try a broader title, abstract, or journal keyword.</p>
        </section>
      </template>
    </div>
  </main>
</template>

<script setup>
import '~/assets/paper-platform.css'
import LiteratureKnowledgeNav from '~/components/LiteratureKnowledgeNav.vue'

const route = useRoute()
const router = useRouter()
const { listLiterature } = useLiteratureApi()

useHead({ title: 'Knowledge Base - OpenIsle' })

const query = ref(typeof route.query.q === 'string' ? route.query.q : '')
const searchInput = ref(query.value)
const sort = ref(typeof route.query.sort === 'string' ? route.query.sort : 'year_desc')
const stateFilter = ref(typeof route.query.state === 'string' ? route.query.state : '')
const advancedOpen = ref(false)
const searchMode = ref('keyword')
const fieldRows = ref([{ field: 'all', value: query.value }])
const journalTiers = ref([])
const searchFields = [
  { id:'all',label:'All fields' },{ id:'title',label:'Title' },{ id:'abstract',label:'Abstract' },{ id:'keywords',label:'Keywords' },{ id:'author',label:'Author' },{ id:'journal',label:'Journal' },{ id:'doi',label:'DOI' },{ id:'year',label:'Year' },{ id:'fulltext',label:'Full text' },
]
const tiers=[{id:'tier1',label:'T1'},{id:'tier2',label:'T2'},{id:'tier3',label:'T3'},{id:'other',label:'Unrated'}]
const requestParams = computed(() => ({ q: query.value, sort: sort.value, limit: 50, offset: 0 }))

const { data, pending, error, refresh } = await useAsyncData(
  'literature:list',
  () => listLiterature(requestParams.value),
  { watch: [requestParams] },
)

const papers = computed(() => {
  const rows = Array.isArray(data.value?.papers) ? data.value.papers : []
  return stateFilter.value ? rows.filter(paper => paper.completeness?.state === stateFilter.value) : rows
})
const total = computed(() => Number(data.value?.total || 0).toLocaleString())

watch(sort, async () => {
  await updateRoute()
})
watch(stateFilter, updateRoute)

async function applySearch() {
  query.value = searchInput.value.trim()
  await updateRoute()
}

async function applyAdvancedSearch() {
  const all = fieldRows.value.find(row => row.field === 'all' && row.value.trim())
  const fallback = fieldRows.value.find(row => row.value.trim())
  searchInput.value = (all || fallback)?.value?.trim() || ''
  query.value = searchInput.value
  if (searchMode.value === 'vector') return router.push({ path:'/literature/vector', query:{ q:query.value, mode:'vector' } })
  if (searchMode.value === 'hybrid') return router.push({ path:'/literature/vector', query:{ q:query.value, mode:'hybrid' } })
  await updateRoute()
}
function removeField(index){if(fieldRows.value.length>1)fieldRows.value.splice(index,1)}
function clearAdvanced(){fieldRows.value=[{field:'all',value:''}];journalTiers.value=[];searchMode.value='keyword';searchInput.value='';query.value=''}

async function updateRoute() {
  await router.replace({
    query: {
      q: query.value || undefined,
      sort: sort.value === 'year_desc' ? undefined : sort.value,
      state: stateFilter.value || undefined,
    },
  })
}

function completenessLabel(value) {
  return ({
    complete: 'Complete', processing: 'Processing', retryable: 'Needs retry',
    incomplete: 'Incomplete', terminal: 'Cannot process',
  })[value?.state] || 'Not audited'
}

function formatAuthors(value) {
  if (!value) return 'Authors not available'
  if (Array.isArray(value)) {
    const names = value
      .map((author) => {
        if (typeof author === 'string') return author
        return author?.name || author?.full_name ||
          [author?.given || author?.given_name, author?.family || author?.family_name].filter(Boolean).join(' ')
      })
      .filter(Boolean)
    return names.length ? names.join(', ') : 'Authors not available'
  }
  return String(value)
}
</script>

<style scoped>
.literature-container {
  max-width: 1040px;
}

.literature-header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.literature-search {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 160px 160px auto;
  gap: 12px;
  align-items: end;
  padding: 16px;
  margin-bottom: 18px;
}
.knowledge-tabs{display:flex;gap:1px;margin-bottom:12px;border:1px solid var(--paper-line);background:var(--paper-line)}.knowledge-tabs a{flex:1;padding:11px 15px;background:#fff;color:var(--paper-muted);font-size:12px;font-weight:800;text-align:center;text-decoration:none}.knowledge-tabs a.active{background:var(--paper-teal);color:#fff}.advanced-search{overflow:hidden;margin-bottom:12px}.advanced-heading{display:flex;justify-content:space-between;align-items:center;padding:12px 15px}.advanced-heading div{display:grid;gap:3px}.advanced-heading span{color:var(--paper-muted);font-size:10px}.advanced-heading button{border:0;background:none;color:var(--paper-teal);font-weight:750;cursor:pointer}.advanced-body{display:grid;gap:9px;padding:14px 15px;border-top:1px solid var(--paper-line)}.field-row{display:grid;grid-template-columns:140px 1fr 38px;gap:7px}.field-row select,.field-row input,.advanced-controls select{min-height:38px;border:1px solid var(--paper-line);background:#fff;padding:7px 9px}.field-row button{border:1px solid var(--paper-line);background:#fff;color:var(--paper-muted);font-size:18px}.advanced-controls{display:flex;align-items:end;gap:8px;flex-wrap:wrap}.advanced-controls label{display:grid;gap:4px;color:var(--paper-muted);font-size:10px}.tier-row{display:flex;align-items:center;gap:15px;padding-top:8px;border-top:1px solid var(--paper-line);color:var(--paper-muted);font-size:11px}.tier-row label{display:flex;align-items:center;gap:5px}.vector-hint{margin:0;padding:9px 11px;background:#fff8e6;color:#71510b;font-size:11px}

.literature-search label {
  display: grid;
  gap: 7px;
  color: var(--paper-muted);
  font-size: 12px;
  font-weight: 700;
}

.literature-search input,
.literature-search select {
  min-height: 40px;
  width: 100%;
  padding: 0 12px;
  border: 1px solid var(--paper-line);
  border-radius: 0;
  color: var(--paper-ink);
  background: var(--paper-panel-subtle);
  font: inherit;
}

.literature-summary {
  margin: 0 2px 10px;
  color: var(--paper-muted);
  font-size: 13px;
}

.literature-summary strong {
  color: var(--paper-ink);
}

.literature-list {
  overflow: hidden;
}

.literature-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 88px;
  gap: 18px;
  align-items: center;
  padding: 19px 20px;
  border-bottom: 1px solid var(--paper-line);
  color: inherit;
  text-decoration: none;
}

.literature-row:last-child {
  border-bottom: 0;
}

.literature-row:hover {
  background: color-mix(in srgb, var(--paper-teal) 5%, transparent);
}

.literature-row h2 {
  margin: 0;
  font-family: var(--paper-font-title);
  font-size: 20px;
  line-height: 1.3;
}

.literature-row-main > p {
  margin: 7px 0 0;
  color: var(--paper-muted);
  font-size: 13px;
  line-height: 1.45;
}

.literature-citations {
  display: grid;
  text-align: right;
}

.literature-citations strong {
  font-size: 19px;
}

.literature-citations span {
  color: var(--paper-soft);
  font-size: 11px;
}

.literature-status.complete { color: #22624e; background: #edf7f3; }
.literature-status.processing { color: #245f78; background: #edf6fa; }
.literature-status.retryable,.literature-status.incomplete { color: #835713; background: #fff6e8; }
.literature-status.terminal { color: #923b32; background: #fff1ef; }

.literature-state {
  text-align: center;
}

.literature-state p {
  margin: 8px auto 14px;
  max-width: 560px;
  color: var(--paper-muted);
  line-height: 1.55;
}

.literature-state.unavailable {
  border-color: color-mix(in srgb, var(--paper-amber) 30%, var(--paper-line));
}

@media (max-width: 720px) {
  .literature-search {
    grid-template-columns: 1fr;
  }

  .literature-row {
    grid-template-columns: 1fr;
  }

  .literature-citations {
    display: flex;
    gap: 5px;
    align-items: baseline;
    text-align: left;
  }
}
</style>
