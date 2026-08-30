<template>
  <main class="paper-shell">
    <div class="paper-container vector-container">
      <header class="paper-workspace-header">
        <div>
          <div class="paper-page-eyebrow">Knowledge Base / Vector database</div>
          <h1 class="paper-page-title">Vector database</h1>
          <p class="paper-page-description">
            Inspect embedding coverage, sample indexed chunks, and run the original semantic or hybrid retrieval workflow.
          </p>
        </div>
        <NuxtLink class="paper-button" to="/literature/workflow/settings">Embedding settings</NuxtLink>
      </header>

      <LiteratureKnowledgeNav />

      <section class="vector-stats" aria-label="Vector database statistics">
        <article><strong>{{ formatNumber(stats.total_embeddings) }}</strong><span>Total embeddings</span></article>
        <article><strong>{{ formatNumber(stats.papers_with_embeddings) }}</strong><span>Indexed papers</span></article>
        <article><strong>{{ formatNumber(stats.dimension) }}</strong><span>Vector dimensions</span></article>
        <article><strong>{{ stats.sqlite_vec_available ? 'Available' : 'NumPy fallback' }}</strong><span>sqlite-vec</span></article>
      </section>

      <section class="paper-panel vector-search-panel">
        <div class="vector-section-heading">
          <div>
            <h2>Semantic retrieval</h2>
            <p>Matches the original system's vector and hybrid search modes.</p>
          </div>
        </div>
        <form class="vector-search-form" @submit.prevent="runSearch">
          <label class="vector-query">Query
            <input v-model="query" placeholder="e.g. livestock grazing" />
          </label>
          <label>Mode
            <select v-model="searchMode">
              <option value="vector">Vector only</option>
              <option value="hybrid">Hybrid search</option>
            </select>
          </label>
          <label>Chunk type
            <select v-model="chunkType">
              <option value="">All types</option>
              <option value="section">Section</option>
              <option value="claim">Claim</option>
              <option value="method">Method</option>
              <option value="data_point">Data point</option>
              <option value="abstract">Abstract</option>
            </select>
          </label>
          <label>Top K
            <input v-model.number="topK" type="number" min="1" max="50" />
          </label>
          <button class="paper-button primary" :disabled="searching || !query.trim()">
            {{ searching ? 'Searching…' : 'Search' }}
          </button>
        </form>

        <p v-if="searchMessage" class="vector-notice" :class="{ error: searchFailed }">{{ searchMessage }}</p>

        <div v-if="results.length" class="vector-results">
          <div class="vector-result-heading"><strong>{{ results.length }} results</strong><span>{{ searchMode === 'hybrid' ? 'Paper-level ranking' : 'Chunk-level similarity' }}</span></div>
          <NuxtLink
            v-for="(result, index) in results"
            :key="`${result.paper_id || result.id}-${result.chunk_id || index}`"
            class="vector-result-row"
            :to="`/literature/${result.paper_id || result.id}`"
          >
            <span class="vector-rank">{{ index + 1 }}</span>
            <div>
              <strong>{{ result.title || result.text || `Literature record ${result.paper_id || result.id}` }}</strong>
              <p>{{ result.abstract || result.text || 'No preview text available.' }}</p>
            </div>
            <dl>
              <div v-if="result.chunk_type"><dt>Type</dt><dd>{{ humanize(result.chunk_type) }}</dd></div>
              <div><dt>{{ searchMode === 'hybrid' ? 'Hybrid score' : 'Similarity' }}</dt><dd>{{ formatScore(searchMode === 'hybrid' ? result.hybrid_score : result.similarity) }}</dd></div>
            </dl>
          </NuxtLink>
        </div>
      </section>

      <div class="vector-lower-grid">
        <section class="paper-panel vector-distribution">
          <div class="vector-section-heading"><div><h2>Chunk type distribution</h2><p>Embedding records grouped by source chunk.</p></div></div>
          <div v-if="stats.by_chunk_type?.length" class="distribution-list">
            <div v-for="item in stats.by_chunk_type" :key="item.chunk_type">
              <div><strong>{{ humanize(item.chunk_type) }}</strong><span>{{ formatNumber(item.c) }}</span></div>
              <div class="distribution-track"><span :style="{ width: distributionWidth(item.c) }" /></div>
            </div>
          </div>
          <div v-else class="vector-empty">No embedding chunks have been indexed.</div>
        </section>

        <section class="paper-panel vector-samples">
          <div class="vector-section-heading"><div><h2>Vector chunk samples</h2><p>The same sample records exposed by the original vector database page.</p></div></div>
          <div v-if="stats.samples?.length" class="sample-list">
            <NuxtLink v-for="sample in stats.samples" :key="`${sample.paper_id}-${sample.chunk_type}-${sample.chunk_id}`" :to="`/literature/${sample.paper_id}`">
              <div><strong>Paper {{ sample.paper_id }}</strong><span>{{ humanize(sample.chunk_type) }} · {{ sample.chunk_id }}</span></div>
              <p>{{ sample.text }}</p>
            </NuxtLink>
          </div>
          <div v-else class="vector-empty">No vector samples are available.</div>
        </section>
      </div>
    </div>
  </main>
</template>

<script setup>
import '~/assets/paper-platform.css'
import LiteratureKnowledgeNav from '~/components/LiteratureKnowledgeNav.vue'

const config = useRuntimeConfig()
const route = useRoute()
useHead({ title: 'Vector Database - OpenIsle' })

const stats = ref({ total_embeddings: 0, papers_with_embeddings: 0, dimension: 0, sqlite_vec_available: false, by_chunk_type: [], samples: [] })
const query = ref(String(route.query.q || ''))
const searchMode = ref(route.query.mode === 'hybrid' ? 'hybrid' : 'vector')
const chunkType = ref('')
const topK = ref(5)
const searching = ref(false)
const searchMessage = ref('')
const searchFailed = ref(false)
const results = ref([])

const endpoint = (path) => `${config.public.apiBaseUrl}/api/literature/explore${path}`

const loadStats = async () => {
  try {
    stats.value = await $fetch(endpoint('/vector/stats?top_k=5'))
  } catch (error) {
    searchFailed.value = true
    searchMessage.value = error?.data?.message || error?.message || 'Unable to load vector database statistics.'
  }
}

const runSearch = async () => {
  if (!query.value.trim() || searching.value) return
  searching.value = true
  searchMessage.value = ''
  searchFailed.value = false
  results.value = []
  try {
    const params = new URLSearchParams({ q: query.value.trim(), top_k: String(Math.min(50, Math.max(1, Number(topK.value) || 5))) })
    if (chunkType.value) params.set('chunk_type', chunkType.value)
    const path = searchMode.value === 'hybrid' ? '/hybrid/search' : '/vector/search'
    const response = await $fetch(`${endpoint(path)}?${params}`)
    results.value = Array.isArray(response?.results) ? response.results : []
    if (response?.available === false) {
      searchFailed.value = true
      searchMessage.value = response.message || 'Vector retrieval is not configured.'
    } else if (!results.value.length) {
      searchMessage.value = 'No similar vectors were found.'
    }
  } catch (error) {
    searchFailed.value = true
    searchMessage.value = error?.data?.message || error?.message || 'Vector search failed.'
  } finally {
    searching.value = false
  }
}

const formatNumber = (value) => Number(value || 0).toLocaleString()
const formatScore = (value) => Number.isFinite(Number(value)) ? Number(value).toFixed(3) : '—'
const humanize = (value) => String(value || 'Unknown').replaceAll('_', ' ').replace(/^./, (letter) => letter.toUpperCase())
const distributionMaximum = computed(() => Math.max(1, ...(stats.value.by_chunk_type || []).map((item) => Number(item.c || 0))))
const distributionWidth = (value) => `${Math.max(3, Number(value || 0) / distributionMaximum.value * 100)}%`

onMounted(async () => { await loadStats(); if (query.value.trim()) await runSearch() })
</script>

<style scoped>
.vector-container{max-width:1180px}.vector-stats{display:grid;grid-template-columns:repeat(4,1fr);margin-bottom:16px;border:1px solid var(--paper-line);background:var(--paper-line);gap:1px}.vector-stats article{display:grid;gap:5px;padding:18px;background:#fff}.vector-stats strong{font-family:Georgia,serif;font-size:25px;font-weight:500}.vector-stats span{color:var(--paper-muted);font-size:10px;font-weight:750;letter-spacing:.07em;text-transform:uppercase}.vector-search-panel{padding:0;margin-bottom:16px}.vector-section-heading{display:flex;justify-content:space-between;padding:16px 18px;border-bottom:1px solid var(--paper-line)}.vector-section-heading h2{margin:0;font-family:Georgia,serif;font-size:21px;font-weight:500}.vector-section-heading p{margin:4px 0 0;color:var(--paper-muted);font-size:12px}.vector-search-form{display:grid;grid-template-columns:minmax(260px,2fr) repeat(3,minmax(110px,1fr)) auto;gap:10px;align-items:end;padding:16px 18px}.vector-search-form label{display:grid;gap:5px;color:var(--paper-muted);font-size:11px;font-weight:750}.vector-search-form input,.vector-search-form select{min-height:40px;border:1px solid var(--paper-line);background:#fff;padding:8px 10px;color:var(--paper-ink);font:inherit}.vector-notice{margin:0 18px 16px;padding:10px 12px;border-left:3px solid #e3a008;background:#fff8e6;color:#71510b;font-size:12px}.vector-notice.error{border-color:#c5483c;background:#fff4f2;color:#8b3028}.vector-result-heading{display:flex;justify-content:space-between;padding:11px 18px;border-top:1px solid var(--paper-line);border-bottom:1px solid var(--paper-line);font-size:11px}.vector-result-heading span{color:var(--paper-muted)}.vector-result-row{display:grid;grid-template-columns:34px minmax(0,1fr) 150px;gap:14px;align-items:center;padding:14px 18px;border-bottom:1px solid var(--paper-line);color:var(--paper-ink);text-decoration:none}.vector-result-row:hover{background:#f5f9fa}.vector-rank{display:grid;place-items:center;width:28px;height:28px;border:1px solid var(--paper-line);font-weight:800}.vector-result-row strong{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.vector-result-row p{display:-webkit-box;overflow:hidden;margin:4px 0 0;color:var(--paper-muted);font-size:12px;line-height:1.45;-webkit-box-orient:vertical;-webkit-line-clamp:2}.vector-result-row dl{display:flex;justify-content:flex-end;gap:16px;margin:0}.vector-result-row dl div{display:grid;gap:2px}.vector-result-row dt{color:var(--paper-muted);font-size:9px;text-transform:uppercase}.vector-result-row dd{margin:0;font-weight:700}.vector-lower-grid{display:grid;grid-template-columns:.8fr 1.2fr;gap:16px}.vector-lower-grid>section{overflow:hidden}.distribution-list{display:grid;gap:14px;padding:18px}.distribution-list>div>div:first-child{display:flex;justify-content:space-between;font-size:12px}.distribution-track{height:7px;margin-top:6px;background:#e8eef0}.distribution-track span{display:block;height:100%;background:var(--paper-teal)}.sample-list a{display:block;padding:13px 18px;border-bottom:1px solid var(--paper-line);color:var(--paper-ink);text-decoration:none}.sample-list a:hover{background:#f5f9fa}.sample-list div{display:flex;justify-content:space-between;gap:10px}.sample-list span{color:var(--paper-muted);font-size:10px}.sample-list p{display:-webkit-box;overflow:hidden;margin:6px 0 0;color:var(--paper-muted);font-size:12px;line-height:1.45;-webkit-box-orient:vertical;-webkit-line-clamp:2}.vector-empty{padding:40px 18px;color:var(--paper-muted);text-align:center;font-size:12px}@media(max-width:900px){.vector-stats{grid-template-columns:repeat(2,1fr)}.vector-search-form{grid-template-columns:1fr 1fr}.vector-query{grid-column:1/-1}.vector-lower-grid{grid-template-columns:1fr}}@media(max-width:600px){.vector-stats,.vector-search-form{grid-template-columns:1fr}.vector-query{grid-column:auto}.vector-result-row{grid-template-columns:30px minmax(0,1fr)}.vector-result-row dl{display:none}}
</style>
