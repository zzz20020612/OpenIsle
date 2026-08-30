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
    <section class="paper-panel result-panel"><div class="result-heading"><strong>{{ current.label }}</strong><span>{{ resultCount }} results</span></div>
      <div v-if="pending" class="empty">Loading knowledge...</div><div v-else-if="!items.length" class="empty">No matching records.</div>
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
const mode=ref(initialMode),query=ref(''),metric=ref(''),yearFrom=ref(''),yearTo=ref(''),pending=ref(false),error=ref(''),notice=ref(''),payload=ref(null)
const current=computed(()=>modes.find(item=>item.id===mode.value)||modes[0])
const searchModes = computed(() => ['papers', 'semantic', 'vector'].includes(mode.value)
  ? modes.filter(item => ['papers', 'semantic', 'vector'].includes(item.id))
  : [current.value])
const items=computed(()=>{const value=payload.value;if(!value)return[];for(const key of ['results','hits','papers','items','knowledge','methods','data_points','authors','nodes','years','timeline','comparisons'])if(Array.isArray(value[key]))return value[key];return Array.isArray(value)?value:[]})
const resultCount=computed(()=>payload.value?.total ?? payload.value?.count ?? items.value.length)
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
.explorer-container{max-width:1180px}.explorer-tabs{display:flex;gap:1px;overflow:auto;margin-bottom:12px;border:1px solid var(--paper-line);background:var(--paper-line)}.explorer-tabs button{flex:1;min-width:105px;border:0;padding:12px;background:var(--paper-panel);color:var(--paper-muted);font-weight:750;cursor:pointer}.explorer-tabs button.active{background:var(--paper-teal);color:#fff}.query-panel{display:flex;align-items:end;gap:10px;padding:14px;margin-bottom:12px}.query-panel label{display:grid;gap:5px;flex:1;color:var(--paper-muted);font-size:12px;font-weight:700}.query-panel input{min-height:40px;border:1px solid var(--paper-line);padding:8px 10px}.result-panel{overflow:hidden}.result-heading{display:flex;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--paper-line)}.result-heading span{color:var(--paper-muted);font-size:12px}.result-list article{padding:18px;border-bottom:1px solid var(--paper-line)}.result-list h2{margin:0 0 7px;font-family:Georgia,serif;font-size:19px;font-weight:500}.result-list a{color:var(--paper-ink);text-decoration:none}.result-list p{color:var(--paper-muted);line-height:1.55}.result-list dl{display:flex;flex-wrap:wrap;gap:5px 16px;margin:8px 0 0;font-size:11px}.result-list dt{font-weight:800}.result-list dd{margin:0;color:var(--paper-muted)}.empty{padding:50px;text-align:center;color:var(--paper-muted)}.notice{padding:10px 14px;background:#fff6e8;color:#835713}.notice.error{background:#fff7f6;color:#923b32}@media(max-width:760px){.query-panel{align-items:stretch;flex-direction:column}}
</style>
