<template>
  <main class="paper-shell">
    <div class="paper-container network-container">
      <header class="paper-workspace-header">
        <div>
          <div class="paper-page-eyebrow">Knowledge Base / Relationship network</div>
          <h1 class="paper-page-title">Citation and relationship network</h1>
          <p class="paper-page-description">
            Explore papers, authors, keywords, and extracted data with the original literature system's interactive graph engine.
          </p>
        </div>
        <button class="paper-button" :disabled="loading" @click="loadGraph(true)">Rebuild layout</button>
      </header>

      <LiteratureKnowledgeNav />

      <div class="network-workspace">
        <aside class="paper-panel network-sidebar" aria-label="Network filters">
          <section>
            <h2>Node types</h2>
            <label v-for="item in nodeTypeOptions" :key="item.id"><input v-model="entityTypes[item.id]" type="checkbox" /> {{ item.label }}</label>
          </section>

          <section>
            <h2>Year range</h2>
            <div class="network-pair"><input v-model="yearFrom" type="number" placeholder="From" /><span>–</span><input v-model="yearTo" type="number" placeholder="To" /></div>
          </section>

          <section>
            <h2>Citations and nodes</h2>
            <label class="network-field">Minimum citations<input v-model.number="minCitations" type="number" min="0" /></label>
            <label class="network-field">Maximum nodes<input v-model.number="maxNodes" type="number" min="20" max="500" /></label>
          </section>

          <section>
            <h2>Display options</h2>
            <label><input v-model="citationOnly" type="checkbox" /> Citation links only</label>
            <label><input v-model="showLabels" type="checkbox" /> Show node labels</label>
          </section>

          <section>
            <h2>Locate node</h2>
            <div class="network-locate"><input v-model="nodeSearch" placeholder="Title, DOI, or author" @keydown.enter.prevent="locateNode" /><button @click="locateNode">Locate</button></div>
            <p>Press Enter to focus the first matching node and its two-hop neighbourhood.</p>
          </section>

          <section>
            <h2>Graph health</h2>
            <button class="diagnostic-status" :class="{ issue: diagnostics.issue_count > 0 }" :disabled="diagnostics.unavailable" @click="locateFirstIssue">
              {{ diagnosticLabel }}
            </button>
            <p v-if="diagnostics.unavailable">Diagnostics require an administrator session.</p>
            <p v-else-if="diagnosticSummary">{{ diagnosticSummary }}</p>
          </section>

          <button class="paper-button primary network-refresh" :disabled="loading" @click="loadGraph(true)">{{ loading ? 'Building graph…' : 'Refresh network' }}</button>
        </aside>

        <section class="paper-panel network-stage">
          <div class="network-stage-header">
            <div><strong>{{ visibleNodes.toLocaleString() }} nodes</strong><span>{{ visibleEdges.toLocaleString() }} relationships</span></div>
            <small>Click to focus · double-click to open · drag to pan · scroll to zoom</small>
          </div>
          <div v-if="error" class="network-error">{{ error }}</div>
          <div ref="graphElement" class="legacy-graph-container"><div class="network-loading">{{ loading ? 'Building graph…' : 'No graph data.' }}</div></div>
        </section>
      </div>
    </div>
  </main>
</template>

<script setup>
import '~/assets/paper-platform.css'
import LiteratureKnowledgeNav from '~/components/LiteratureKnowledgeNav.vue'

const config = useRuntimeConfig()
const router = useRouter()
useHead({ title: 'Literature Network - OpenIsle' })

const graphElement = ref(null)
const loading = ref(false)
const error = ref('')
const yearFrom = ref('')
const yearTo = ref('')
const minCitations = ref(0)
const maxNodes = ref(80)
const showLabels = ref(true)
const citationOnly = ref(false)
const nodeSearch = ref('')
const entityTypes = reactive({ paper: true, author: true, keyword: true, data_point: true })
const graphData = ref({ nodes: [], edges: [] })
const diagnostics = ref({ issue_count: 0, issues: [], unavailable: true })

const nodeTypeOptions = [
  { id: 'paper', label: 'Papers' },
  { id: 'author', label: 'Authors' },
  { id: 'keyword', label: 'Keywords' },
  { id: 'data_point', label: 'Data points' },
]

const visibleNodes = computed(() => graphData.value.nodes.length)
const visibleEdges = computed(() => graphData.value.edges.length)
const diagnosticLabel = computed(() => diagnostics.value.unavailable ? 'Diagnostics unavailable' : diagnostics.value.issue_count ? `${diagnostics.value.issue_count} issues detected` : 'Graph healthy')
const diagnosticSummary = computed(() => Object.entries(diagnostics.value.issue_stats || {}).map(([key, value]) => `${humanize(key)}: ${value}`).join(' · '))

const translations = {
  'graph.paper': 'Paper', 'graph.author': 'Author', 'graph.keyword': 'Keyword', 'graph.data_point': 'Data point', 'graph.institution': 'Institution',
  'graph.no_nodes': 'No nodes match the current filters.', 'tooltip.type': 'Type', 'tooltip.year': 'Year', 'tooltip.citations': 'Citations', 'tooltip.connections': 'Connections', 'tooltip.occurrences': 'Occurrences', 'tooltip.paper_count': 'Paper count', 'tooltip.click_focus': 'Click to focus; double-click to open',
  'graph.controls.title': 'Graph controls', 'graph.controls.toggle': 'Toggle graph controls', 'graph.controls.relayout': 'Rebuild layout', 'graph.controls.reset': 'Reset view', 'graph.controls.show_all_labels': 'Show all labels', 'graph.controls.smart_labels': 'Use smart labels',
  'graph.legend.upstream': 'Upstream', 'graph.legend.downstream': 'Downstream', 'graph.legend.two_hop': 'Two-hop neighbour',
}

const ensureGraphRenderer = async () => {
  if (window.OpenIsleLiteratureCharts?.forceGraph) return window.OpenIsleLiteratureCharts
  window.Utils = window.Utils || {
    truncate: (value, length) => String(value || '').length > length ? `${String(value || '').slice(0, length)}…` : String(value || ''),
    escapeHtml: (value) => String(value || '').replace(/[&<>'"]/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[character]),
  }
  window.I18n = window.I18n || { t: (key) => translations[key] || key }
  await new Promise((resolve, reject) => {
    const existing = document.querySelector('script[data-literature-graph-engine]')
    if (existing) {
      existing.addEventListener('load', resolve, { once: true })
      existing.addEventListener('error', reject, { once: true })
      return
    }
    const script = document.createElement('script')
    script.src = '/literature-engine/charts.js'
    script.dataset.literatureGraphEngine = 'true'
    script.onload = resolve
    script.onerror = reject
    document.head.appendChild(script)
  })
  return window.OpenIsleLiteratureCharts
}

const activeTypeList = () => Object.entries(entityTypes).filter(([, enabled]) => enabled).map(([type]) => type)
const queryString = () => {
  const params = new URLSearchParams({ entity_types: activeTypeList().join(','), min_citations: String(Math.max(0, Number(minCitations.value) || 0)), max_nodes: String(Math.min(500, Math.max(20, Number(maxNodes.value) || 80))) })
  if (yearFrom.value) params.set('year_from', yearFrom.value)
  if (yearTo.value) params.set('year_to', yearTo.value)
  return params
}

const fetchDiagnostics = async (params) => {
  try {
    diagnostics.value = await $fetch(`${config.public.apiBaseUrl}/api/literature/admin/graph/diagnostics?${params}`)
  } catch {
    diagnostics.value = { issue_count: 0, issues: [], unavailable: true }
  }
}

const renderGraph = async (relayout = false) => {
  if (!graphElement.value) return
  const renderer = await ensureGraphRenderer()
  renderer.forceGraph(graphElement.value, graphData.value.nodes, graphData.value.edges, {
    show_labels: showLabels.value,
    relayout,
    citation_only: citationOnly.value,
    problemNodeIds: new Set((diagnostics.value.issues || []).flatMap((issue) => issue.node_ids || (issue.node_id ? [issue.node_id] : []))),
    onNodeClick: (node) => {
      if (node.type === 'paper' && node.paper_id) router.push(`/literature/${node.paper_id}`)
      else if (node.type === 'author' && node.author_id) router.push(`/literature/authors/${node.author_id}`)
      else if (node.type === 'author') router.push({ path: '/literature/authors', query: { q: node.label || '' } })
    },
  })
}

const loadGraph = async (relayout = false) => {
  if (loading.value) return
  loading.value = true
  error.value = ''
  if (graphElement.value) graphElement.value.innerHTML = '<div class="network-loading">Building graph…</div>'
  try {
    const params = queryString()
    const response = await $fetch(`${config.public.apiBaseUrl}/api/literature/explore/graph?${params}`)
    let nodes = Array.isArray(response?.nodes) ? response.nodes : []
    let edges = Array.isArray(response?.edges) ? response.edges : []
    const activeTypes = new Set(activeTypeList())
    nodes = nodes.filter((node) => activeTypes.has(node.type))
    if (citationOnly.value) nodes = nodes.filter((node) => node.type === 'paper')
    const nodeIds = new Set(nodes.map((node) => node.id))
    edges = edges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target) && (!citationOnly.value || edge.type === 'cites'))
    graphData.value = { nodes, edges }
    await fetchDiagnostics(params)
    await renderGraph(relayout)
  } catch (cause) {
    error.value = cause?.data?.message || cause?.message || 'Unable to build the relationship network.'
    if (graphElement.value) graphElement.value.innerHTML = ''
  } finally {
    loading.value = false
  }
}

const locateNode = () => {
  const keyword = nodeSearch.value.trim().toLowerCase()
  if (!keyword || !graphElement.value) return
  const node = graphData.value.nodes.find((item) => String(item.label || '').toLowerCase().includes(keyword) || String(item.doi || '').toLowerCase().includes(keyword))
  if (!node) {
    error.value = 'No matching node was found in the current graph.'
    return
  }
  error.value = ''
  graphElement.value.dispatchEvent(new CustomEvent('graph:focus', { detail: { nodeId: node.id, hopDepth: 2 } }))
}

const locateFirstIssue = () => {
  const issue = (diagnostics.value.issues || []).find((item) => item.node_id || item.node_ids?.length)
  const nodeId = issue?.node_id || issue?.node_ids?.[0]
  if (nodeId && graphElement.value) graphElement.value.dispatchEvent(new CustomEvent('graph:focus', { detail: { nodeId, hopDepth: 1 } }))
}

const humanize = (value) => String(value || '').replaceAll('_', ' ').replace(/^./, (letter) => letter.toUpperCase())

onMounted(() => loadGraph())
</script>

<style scoped>
.network-container{max-width:1320px}.network-workspace{display:grid;grid-template-columns:250px minmax(0,1fr);gap:16px}.network-sidebar{display:flex;flex-direction:column;gap:18px;padding:16px}.network-sidebar section{display:grid;gap:8px;padding-bottom:14px;border-bottom:1px solid var(--paper-line)}.network-sidebar h2{margin:0;color:var(--paper-ink);font-size:12px;text-transform:uppercase;letter-spacing:.06em}.network-sidebar label{display:flex;align-items:center;gap:8px;color:var(--paper-muted);font-size:12px}.network-sidebar input[type=checkbox]{accent-color:var(--paper-teal)}.network-pair{display:grid;grid-template-columns:1fr auto 1fr;gap:5px;align-items:center}.network-sidebar input[type=number],.network-sidebar input[type=text]{width:100%;min-width:0;border:1px solid var(--paper-line);background:#fff;padding:8px;color:var(--paper-ink);font:inherit}.network-field{display:grid!important;grid-template-columns:1fr 72px;gap:8px}.network-locate{display:grid;grid-template-columns:minmax(0,1fr) auto}.network-locate button{border:0;background:var(--paper-teal);color:#fff;font-weight:750}.network-sidebar p{margin:0;color:var(--paper-muted);font-size:10px;line-height:1.4}.diagnostic-status{justify-self:start;border:0;background:none;padding:0;color:#087a56;font-weight:750;text-align:left}.diagnostic-status.issue{color:#a83b32}.diagnostic-status:disabled{color:var(--paper-muted)}.network-refresh{margin-top:auto}.network-stage{overflow:hidden}.network-stage-header{display:flex;justify-content:space-between;gap:15px;padding:13px 16px;border-bottom:1px solid var(--paper-line)}.network-stage-header div{display:flex;gap:16px}.network-stage-header span,.network-stage-header small{color:var(--paper-muted);font-size:11px}.network-error{padding:10px 14px;background:#fff4f2;color:#8b3028;font-size:12px}.legacy-graph-container{position:relative;width:100%;height:680px;overflow:hidden;background:#fff}.network-loading{display:grid;place-items:center;height:100%;color:var(--paper-muted);font-size:13px}.legacy-graph-container :deep(svg){display:block;width:100%;height:100%}.legacy-graph-container :deep(.graph-node){cursor:pointer}.legacy-graph-container :deep(.graph-node circle){stroke:#fff;stroke-width:2px}.legacy-graph-container :deep(.graph-node:hover circle){stroke:var(--paper-ink)}.legacy-graph-container :deep(.graph-tooltip){position:absolute;z-index:50;display:none;max-width:270px;padding:8px 10px;background:rgba(22,35,44,.94);color:#fff;font-size:12px;line-height:1.4;pointer-events:none}.legacy-graph-container :deep(.graph-legend){position:absolute;bottom:14px;left:14px;z-index:10;display:flex;max-height:42%;overflow:auto;flex-direction:column;gap:6px;padding:10px 12px;border:1px solid var(--paper-line);background:rgba(255,255,255,.94);color:var(--paper-muted);font-size:11px}.legacy-graph-container :deep(.graph-legend-item){display:flex;align-items:center;gap:8px}.legacy-graph-container :deep(.graph-legend-dot){width:9px;height:9px;border-radius:50%}.legacy-graph-container :deep(.graph-controls){position:absolute;top:10px;right:10px;z-index:10;display:flex;flex-direction:column;align-items:flex-end;gap:6px}.legacy-graph-container :deep(.graph-controls-toggle),.legacy-graph-container :deep(.graph-controls-panel button){border:1px solid var(--paper-line);background:#fff;color:var(--paper-ink);padding:7px 9px;cursor:pointer}.legacy-graph-container :deep(.graph-controls-panel){display:flex;min-width:120px;flex-direction:column;gap:6px;padding:8px;border:1px solid var(--paper-line);background:rgba(255,255,255,.96)}.legacy-graph-container :deep(.graph-focus-badge){position:absolute;right:14px;bottom:14px;z-index:10;max-width:50%;overflow:hidden;padding:6px 12px;background:var(--paper-teal);color:#fff;font-size:11px;text-overflow:ellipsis;white-space:nowrap;cursor:pointer}@media(max-width:900px){.network-workspace{grid-template-columns:1fr}.network-sidebar{display:grid;grid-template-columns:repeat(2,1fr)}.network-refresh{margin-top:0}.legacy-graph-container{height:560px}}@media(max-width:600px){.network-sidebar{grid-template-columns:1fr}.network-stage-header{align-items:flex-start;flex-direction:column}.legacy-graph-container{height:500px}}
</style>
