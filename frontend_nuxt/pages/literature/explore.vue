<template>
  <main class="paper-shell"><div class="paper-container explorer-container">
    <header class="paper-workspace-header"><div><div class="paper-page-eyebrow">Knowledge Base / Research tools</div><h1 class="paper-page-title">{{ current.title }}</h1><p class="paper-page-description">{{ current.description }}</p></div><NuxtLink class="paper-button" to="/literature/workflow">Processing administration</NuxtLink></header>
    <LiteratureKnowledgeNav />
    <nav class="explorer-tabs" aria-label="Search modes"><button v-for="item in searchModes" :key="item.id" :class="{ active: mode === item.id }" @click="selectMode(item.id)">{{ item.label }}</button></nav>
    <form class="paper-panel query-panel" @submit.prevent="search">
      <label v-if="current.needsQuery">Query<input v-model="query" :placeholder="current.placeholder" /></label>
      <label v-if="current.metric">Metric name<input v-model="metric" placeholder="e.g. accuracy" /></label>
      <label>From year<input v-model="yearFrom" placeholder="2015" /></label><label>To year<input v-model="yearTo" placeholder="2026" /></label>
      <button class="paper-button primary" :disabled="pending">{{ pending ? 'Loading...' : 'Explore' }}</button>
    </form>
    <p v-if="notice" class="notice">{{ notice }}</p><p v-if="error" class="notice error">{{ error }}</p>
    <section class="paper-panel result-panel"><div class="result-heading"><strong>{{ current.label }}</strong><span>{{ resultSummary }}</span></div>
      <div v-if="pending" class="empty">Loading knowledge...</div><div v-else-if="!items.length" class="empty"><strong>No matching records.</strong><span>{{ emptyExplanation }}</span></div>

      <div v-else-if="mode === 'timeline'" class="timeline-view">
        <article v-for="item in items" :key="item.year" class="timeline-row">
          <div class="timeline-year">{{ item.year }}</div>
          <div class="timeline-measure"><div class="timeline-bar"><span :style="{ width: timelineWidth(item) }" /></div><p>{{ countLabel(item.paper_count, 'paper') }} · {{ countLabel(item.data_point_count, 'extracted data point') }}</p></div>
          <strong>{{ item.parse_done_count || 0 }}</strong><small>parsed sections</small>
        </article>
      </div>

      <div v-else-if="mode === 'compare'" class="comparison-view">
        <article v-for="(item,index) in items" :key="`${item.paper_id}-${index}`" class="comparison-row">
          <div><NuxtLink :to="`/literature/${item.paper_id}`">{{ item.title || `Literature record ${item.paper_id}` }}</NuxtLink><p>{{ item.context || item.journal || 'Context unavailable' }}</p></div>
          <div class="comparison-measure"><strong>{{ item.metric_value }}<small>{{ item.unit || '' }}</small></strong><div class="comparison-bar"><span :style="{ width: comparisonWidth(item) }" /></div></div>
        </article>
      </div>

      <div v-else-if="mode === 'graph' || mode === 'institutions'" class="network-view">
        <div class="network-summary"><div><strong>{{ networkPaperCount }}</strong><span>papers in view</span></div><div><strong>{{ networkEntityCount }}</strong><span>linked entities</span></div><div><strong>{{ networkEdges.length }}</strong><span>relationships shown</span></div></div>
        <svg v-if="networkNodes.length" class="network-canvas" viewBox="0 0 800 480" role="img" :aria-label="`${current.title}: ${networkNodes.length} entities and ${networkEdges.length} relationships`">
          <text class="network-column-label" x="28" y="28">MATCHING PAPERS</text>
          <text class="network-column-label" x="530" y="28">CONNECTED ENTITIES</text>
          <line v-for="(edge,index) in networkEdges" :key="`${edge.source}-${edge.target}-${index}`" :x1="nodeX(edge.source)" :y1="nodeY(edge.source)" :x2="nodeX(edge.target)" :y2="nodeY(edge.target)" />
          <g v-for="node in networkNodes" :key="node.id" :transform="`translate(${nodeX(node.id)} ${nodeY(node.id)})`">
            <circle :class="`node-${node.type || 'entity'}`" :r="node.type === 'paper' ? 12 : 8" />
            <text :x="node.type === 'paper' ? -18 : 16" y="4" :text-anchor="node.type === 'paper' ? 'end' : 'start'">{{ compactLabel(node.label || node.name) }}</text>
            <title>{{ node.label || node.name }}</title>
          </g>
        </svg>
        <div class="network-legend"><span><i class="paper" />Paper</span><span><i class="author" />Author</span><span><i class="keyword" />Extracted data</span><small>The diagram prioritizes query-matching papers and their nearest recorded relationships.</small></div>
        <div class="network-records"><article v-for="node in networkNodes" :key="`record-${node.id}`"><NuxtLink v-if="node.paper_id" :to="`/literature/${node.paper_id}`">{{ node.label }}</NuxtLink><strong v-else>{{ node.label || node.name }}</strong><span>{{ humanize(node.type || 'entity') }}</span></article></div>
      </div>

      <div v-else-if="mode === 'authors'" class="scholar-grid">
        <article v-for="item in items" :key="item.id"><div class="scholar-monogram">{{ monogram(item.full_name) }}</div><div><h2>{{ item.full_name }}</h2><p>{{ item.current_affiliation || item.affiliation || 'Affiliation unavailable' }}</p><dl><div><dt>Papers</dt><dd>{{ item.paper_count || item.total_publications || 0 }}</dd></div><div><dt>h-index</dt><dd>{{ item.h_index || 0 }}</dd></div><div><dt>ORCID</dt><dd>{{ item.orcid || '—' }}</dd></div></dl></div></article>
      </div>

      <div v-else class="result-list"><article v-for="(item,index) in items" :key="item.id || item.paper_id || index"><NuxtLink v-if="item.paper_id || (mode === 'papers' && item.id)" :to="`/literature/${item.paper_id || item.id}`"><h2>{{ title(item,index) }}</h2></NuxtLink><h2 v-else>{{ title(item,index) }}</h2><p>{{ summary(item) }}</p><dl><template v-for="([key,value]) in fields(item)" :key="key"><dt>{{ humanize(key) }}</dt><dd>{{ display(value) }}</dd></template></dl></article></div>
    </section>
  </div></main>
</template>

<script setup>
import '~/assets/paper-platform.css'
import LiteratureKnowledgeNav from '~/components/LiteratureKnowledgeNav.vue'
const config = useRuntimeConfig()
const route = useRoute()
const router = useRouter()
useHead({ title: 'Explore Literature Knowledge - OpenIsle' })
const modes = [
  { id:'papers',label:'Keyword',title:'Search the literature corpus',description:'Find records by title, abstract, author, journal, DOI, or keyword.',path:'/search',needsQuery:true,placeholder:'Title, abstract, author, or keyword' },
  { id:'semantic',label:'Semantic',title:'Semantic literature search',description:'Find conceptually related records even when they use different terminology.',path:'/hybrid/search',needsQuery:true,placeholder:'Describe the concept you need' },
  { id:'vector',label:'Vector',title:'Vector similarity search',description:'Search the indexed corpus by embedding similarity.',path:'/vector/search',needsQuery:true,placeholder:'Describe the research concept' },
  { id:'knowledge',label:'Knowledge',title:'Extracted knowledge and findings',description:'Search claims, findings, research questions, and structured knowledge extracted from full text.',path:'/knowledge/list',needsQuery:true,placeholder:'Claim, finding, or question' },
  { id:'methods',label:'Methods',title:'Research methods and workflows',description:'Inspect experimental designs, analytical procedures, models, and methodological steps.',path:'/methods/list',needsQuery:true,placeholder:'Method or analytical approach' },
  { id:'data',label:'Data points',title:'Extracted metrics and reported results',description:'Search quantitative observations together with units, contexts, and source papers.',path:'/data_points/list',needsQuery:true,placeholder:'Metric or measured quantity' },
  { id:'authors',label:'Authors',title:'Scholar directory and profiles',description:'Find scholars, affiliations, publication records, and collaboration information.',path:'/authors/list',needsQuery:true,placeholder:'Author name' },
  { id:'institutions',label:'Institutions',title:'Institutional collaboration',description:'Explore organizations and the collaboration links derived from the literature corpus.',path:'/institution/network',needsQuery:true,placeholder:'Institution or affiliation' },
  { id:'graph',label:'Relationships',title:'Literature relationship network',description:'Explore connections among papers, authors, keywords, citations, and extracted evidence.',path:'/graph',needsQuery:true,placeholder:'Topic for relationship graph' },
  { id:'timeline',label:'Timeline',title:'Research timeline and trends',description:'Review how publication activity, evidence, and research topics change over time.',path:'/timeline',needsQuery:false },
  { id:'compare',label:'Metric comparison',title:'Cross-paper metric comparison',description:'Compare a reported metric across papers, years, methods, and study contexts.',path:'/compare/metric',needsQuery:false,metric:true },
]
const validModes = new Set(modes.map(item => item.id))
const initialMode = validModes.has(String(route.query.mode || '')) ? String(route.query.mode) : 'knowledge'
const mode=ref(initialMode),query=ref(String(route.query.q || '')),metric=ref(''),yearFrom=ref(''),yearTo=ref(''),pending=ref(false),error=ref(''),notice=ref(''),payload=ref(null)
const current=computed(()=>modes.find(item=>item.id===mode.value)||modes[0])
const searchModes = computed(() => ['papers', 'semantic', 'vector'].includes(mode.value)
  ? modes.filter(item => ['papers', 'semantic', 'vector'].includes(item.id))
  : [current.value])
const items=computed(()=>{const value=payload.value;if(!value)return[];for(const key of ['results','hits','papers','items','knowledge','methods','data_points','authors','nodes','years','timeline','comparisons'])if(Array.isArray(value[key]))return value[key];return Array.isArray(value)?value:[]})
const resultCount=computed(()=>payload.value?.total ?? payload.value?.count ?? items.value.length)
const resultSummary=computed(()=>mode.value==='graph'?`${networkNodes.value.length} visible entities · ${Number(payload.value?.total_nodes||items.value.length).toLocaleString()} in corpus`:`${resultCount.value} results`)
const emptyExplanation=computed(()=>mode.value==='institutions'?'No institution relationships have been extracted from the current corpus. Complete author affiliations and rerun extraction to populate this view.':mode.value==='compare'&&!metric.value.trim()?'Enter a metric name such as accuracy, RMSE, or response time to compare evidence across papers.':'Try a broader query or remove the year filters.')
const timelineMaximum=computed(()=>Math.max(1,...items.value.map(item=>Number(item.paper_count||0))))
const timelineWidth=item=>`${Math.max(4,Number(item.paper_count||0)/timelineMaximum.value*100)}%`
const comparisonMaximum=computed(()=>Math.max(1,...items.value.map(item=>Math.abs(Number.parseFloat(item.metric_value)||0))))
const comparisonWidth=item=>`${Math.max(3,Math.abs(Number.parseFloat(item.metric_value)||0)/comparisonMaximum.value*100)}%`
const rawNetworkNodes=computed(()=>Array.isArray(payload.value?.nodes)?payload.value.nodes:[])
const rawNetworkEdges=computed(()=>Array.isArray(payload.value?.edges)?payload.value.edges:[])
const networkDegree=computed(()=>{const value=new Map();rawNetworkEdges.value.forEach(edge=>{value.set(String(edge.source),(value.get(String(edge.source))||0)+1);value.set(String(edge.target),(value.get(String(edge.target))||0)+1)});return value})
const networkNodes=computed(()=>{
  const nodes=rawNetworkNodes.value
  if(!nodes.length)return[]
  const byId=new Map(nodes.map(node=>[String(node.id),node]))
  const words=query.value.trim().toLowerCase().split(/\s+/).filter(Boolean)
  const papers=nodes.filter(node=>node.type==='paper')
  let seeds=papers.filter(node=>words.length&&words.every(word=>String(node.label||node.name||'').toLowerCase().includes(word)))
  if(!seeds.length)seeds=papers
  seeds=[...seeds].sort((a,b)=>(networkDegree.value.get(String(b.id))||0)-(networkDegree.value.get(String(a.id))||0)).slice(0,7)
  if(!seeds.length)seeds=[...nodes].sort((a,b)=>(networkDegree.value.get(String(b.id))||0)-(networkDegree.value.get(String(a.id))||0)).slice(0,7)
  const selected=new Map(seeds.map(node=>[String(node.id),node]))
  seeds.forEach(seed=>{
    const neighbours=rawNetworkEdges.value
      .filter(edge=>String(edge.source)===String(seed.id)||String(edge.target)===String(seed.id))
      .map(edge=>byId.get(String(String(edge.source)===String(seed.id)?edge.target:edge.source)))
      .filter(Boolean)
      .sort((a,b)=>(a.type==='data_point'?-1:0)-(b.type==='data_point'?-1:0))
      .slice(0,2)
    neighbours.forEach(node=>selected.set(String(node.id),node))
  })
  return Array.from(selected.values()).slice(0,24)
})
const networkNodeIds=computed(()=>new Set(networkNodes.value.map(node=>String(node.id))))
const networkEdges=computed(()=>rawNetworkEdges.value.filter(edge=>networkNodeIds.value.has(String(edge.source))&&networkNodeIds.value.has(String(edge.target))).slice(0,60))
const networkPaperNodes=computed(()=>networkNodes.value.filter(node=>node.type==='paper'))
const networkEntityNodes=computed(()=>networkNodes.value.filter(node=>node.type!=='paper'))
const networkPaperCount=computed(()=>networkPaperNodes.value.length)
const networkEntityCount=computed(()=>networkEntityNodes.value.length)
const nodeGroup=id=>networkPaperNodes.value.some(node=>String(node.id)===String(id))?networkPaperNodes.value:networkEntityNodes.value
const nodeIndex=id=>Math.max(0,nodeGroup(id).findIndex(node=>String(node.id)===String(id)))
const nodeX=id=>nodeGroup(id)===networkPaperNodes.value?300:500
const nodeY=id=>{const group=nodeGroup(id);return 52+nodeIndex(id)*(390/Math.max(1,group.length-1))}
const compactLabel=value=>{const clean=String(value||'Entity').replace(/\s+/g,' ');return clean.slice(0,38)+(clean.length>38?'…':'')}
const monogram=value=>String(value||'?').trim().split(/\s+/).slice(0,2).map(part=>part[0]?.toUpperCase()).join('')||'?'
const selectMode=async(value)=>{mode.value=value;payload.value=null;error.value='';notice.value='';await router.replace({query:{...route.query,mode:value}});await search()}
const search=async()=>{pending.value=true;error.value='';notice.value='';try{const params=new URLSearchParams();if(query.value.trim())params.set('q',query.value.trim());if(metric.value.trim())params.set('metric_name',metric.value.trim());if(yearFrom.value)params.set('year_from',yearFrom.value);if(yearTo.value)params.set('year_to',yearTo.value);params.set(current.value.id==='semantic'?'top_k':'limit','30');const path=current.value.id==='papers'&&!query.value.trim()?'/papers/list':current.value.path;const result=await $fetch(`${config.public.apiBaseUrl}/api/literature/explore${path}?${params}`);payload.value=result;if(result?.available===false)notice.value=result.message}catch(cause){error.value=cause?.data?.message||cause?.data?.error||cause?.message||'Unable to load this literature view.'}finally{pending.value=false}}
const title=(item,index)=>item.title||item.paper_title||item.full_name||item.name||(item.year ? `Research activity in ${item.year}` : `Result ${index+1}`)
const countLabel=(value,singular,plural=`${singular}s`)=>`${Number(value || 0).toLocaleString()} ${Number(value || 0) === 1 ? singular : plural}`
const summary=(item)=>item.abstract||item.summary||item.claim||item.description||item.research_question||item.method_name||item.metric_name||item.text||(item.year ? `${countLabel(item.paper_count, 'paper')} · ${countLabel(item.data_point_count, 'extracted data point')}` : '')
const fields=(item)=>Object.entries(item).filter(([key,value])=>value!=null&&!['abstract','summary','claim','description','research_question','text','title','paper_title'].includes(key)&&typeof value!=='object').slice(0,8)
const humanize=(value)=>value.replaceAll('_',' ').replace(/^./,c=>c.toUpperCase())
const display=(value)=>String(value).length>180?`${String(value).slice(0,180)}…`:String(value)
watch(() => route.query.mode, value => {
  const next = String(value || '')
  if (validModes.has(next) && next !== mode.value) {
    mode.value = next
    payload.value = null
    search()
  }
})
onMounted(search)
</script>

<style scoped>
.explorer-container{max-width:1180px}.explorer-tabs{display:flex;gap:1px;overflow:auto;margin-bottom:12px;border:1px solid var(--paper-line);background:var(--paper-line)}.explorer-tabs button{flex:1;min-width:105px;border:0;padding:12px;background:var(--paper-panel);color:var(--paper-muted);font-weight:750;cursor:pointer}.explorer-tabs button.active{background:var(--paper-teal);color:#fff}.query-panel{display:flex;align-items:end;gap:10px;padding:14px;margin-bottom:12px}.query-panel label{display:grid;gap:5px;flex:1;color:var(--paper-muted);font-size:12px;font-weight:700}.query-panel input{min-height:40px;border:1px solid var(--paper-line);padding:8px 10px}.result-panel{overflow:hidden}.result-heading{display:flex;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--paper-line)}.result-heading span{color:var(--paper-muted);font-size:12px}.result-list article{padding:18px;border-bottom:1px solid var(--paper-line)}.result-list h2{margin:0 0 7px;font-family:Georgia,serif;font-size:19px;font-weight:500}.result-list a{color:var(--paper-ink);text-decoration:none}.result-list p{color:var(--paper-muted);line-height:1.55}.result-list dl{display:flex;flex-wrap:wrap;gap:5px 16px;margin:8px 0 0;font-size:11px}.result-list dt{font-weight:800}.result-list dd{margin:0;color:var(--paper-muted)}.empty{display:grid;gap:7px;padding:50px;text-align:center;color:var(--paper-muted)}.empty strong{color:var(--paper-ink);font-family:Georgia,serif;font-size:20px;font-weight:500}.notice{padding:10px 14px;background:#fff6e8;color:#835713}.notice.error{background:#fff7f6;color:#923b32}
.timeline-view{padding:8px 18px 22px}.timeline-row{display:grid;grid-template-columns:72px minmax(0,1fr) 58px 88px;gap:15px;align-items:center;padding:15px 0;border-bottom:1px solid var(--paper-line)}.timeline-year{font-family:Georgia,serif;font-size:24px;color:var(--paper-ink)}.timeline-measure{display:grid;gap:6px}.timeline-measure p{margin:0;color:var(--paper-muted);font-size:12px}.timeline-bar,.comparison-bar{height:8px;background:#e7edef}.timeline-bar span,.comparison-bar span{display:block;height:100%;background:linear-gradient(90deg,var(--paper-teal),#009edb)}.timeline-row>strong{font-size:19px;text-align:right}.timeline-row>small{color:var(--paper-muted)}
.comparison-view{padding:4px 18px 22px}.comparison-row{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(250px,1fr);gap:28px;align-items:center;padding:16px 0;border-bottom:1px solid var(--paper-line)}.comparison-row a{color:var(--paper-ink);font-family:Georgia,serif;font-size:17px;text-decoration:none}.comparison-row p{margin:6px 0 0;color:var(--paper-muted);font-size:12px}.comparison-measure{display:grid;gap:8px}.comparison-measure strong{font-size:18px}.comparison-measure small{margin-left:5px;color:var(--paper-muted);font-size:11px}
.network-view{padding:18px}.network-summary{display:grid;grid-template-columns:repeat(3,1fr);margin-bottom:16px;border:1px solid var(--paper-line)}.network-summary div{display:grid;gap:3px;padding:14px;border-right:1px solid var(--paper-line)}.network-summary div:last-child{border-right:0}.network-summary strong{font-family:Georgia,serif;font-size:24px;font-weight:500}.network-summary span{color:var(--paper-muted);font-size:11px;text-transform:uppercase;letter-spacing:.06em}.network-canvas{display:block;width:100%;max-height:560px;border:1px solid var(--paper-line);background:#fbfcfc}.network-canvas line{stroke:#9eb2ba;stroke-width:1.25;opacity:.72}.network-canvas circle{fill:#78909a;stroke:#fff;stroke-width:2}.network-canvas .node-paper{fill:#0065a8}.network-canvas .node-author{fill:#009edb}.network-canvas .node-data_point,.network-canvas .node-keyword{fill:#00a88f}.network-canvas text{fill:var(--paper-ink);font-size:10px}.network-canvas .network-column-label{fill:var(--paper-muted);font-size:9px;font-weight:800;letter-spacing:.09em}.network-legend{display:flex;align-items:center;gap:18px;padding:12px 0;color:var(--paper-muted);font-size:11px}.network-legend span{display:flex;align-items:center;gap:6px;white-space:nowrap}.network-legend small{margin-left:auto;color:var(--paper-muted);font-size:10px;text-align:right}.network-legend i{width:9px;height:9px;border-radius:50%;background:#78909a}.network-legend i.paper{background:#0065a8}.network-legend i.author{background:#009edb}.network-legend i.keyword{background:#00a88f}.network-records{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1px;background:var(--paper-line);border:1px solid var(--paper-line)}.network-records article{display:flex;justify-content:space-between;gap:14px;padding:10px 12px;background:#fff;font-size:12px}.network-records a,.network-records strong{overflow:hidden;color:var(--paper-ink);font-weight:650;text-overflow:ellipsis;white-space:nowrap;text-decoration:none}.network-records span{color:var(--paper-muted);font-size:10px;text-transform:uppercase}
.scholar-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1px;background:var(--paper-line)}.scholar-grid>article{display:grid;grid-template-columns:54px minmax(0,1fr);gap:14px;padding:18px;background:#fff}.scholar-monogram{display:grid;place-items:center;width:50px;height:50px;border-radius:50%;background:#e7f2f5;color:#176582;font-family:Georgia,serif;font-size:18px}.scholar-grid h2{margin:0;font-family:Georgia,serif;font-size:18px;font-weight:500}.scholar-grid p{min-height:32px;margin:5px 0 10px;color:var(--paper-muted);font-size:12px}.scholar-grid dl{display:flex;gap:18px;margin:0}.scholar-grid dl div{display:grid;gap:2px}.scholar-grid dt{color:var(--paper-muted);font-size:9px;text-transform:uppercase}.scholar-grid dd{margin:0;font-size:12px;font-weight:700}
@media(max-width:760px){.query-panel{align-items:stretch;flex-direction:column}.timeline-row{grid-template-columns:58px minmax(0,1fr)}.timeline-row>small{display:none}.comparison-row{grid-template-columns:1fr}.network-summary{grid-template-columns:1fr}.network-summary div{border-right:0;border-bottom:1px solid var(--paper-line)}.network-legend{align-items:flex-start;flex-wrap:wrap}.network-legend small{width:100%;margin-left:0;text-align:left}.network-records,.scholar-grid{grid-template-columns:1fr}}
</style>
