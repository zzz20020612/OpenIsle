<template>
  <main class="paper-shell"><div class="paper-container explorer-container">
    <header class="paper-workspace-header"><div><div class="paper-page-eyebrow">Knowledge Base / Explore</div><h1 class="paper-page-title">Explore literature knowledge</h1><p class="paper-page-description">Search papers, extracted claims, methods, data points, authors, relationships, and trends.</p></div><NuxtLink class="paper-button" to="/literature">Back to papers</NuxtLink></header>
    <nav class="explorer-tabs"><button v-for="item in modes" :key="item.id" :class="{ active: mode === item.id }" @click="selectMode(item.id)">{{ item.label }}</button></nav>
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
const config = useRuntimeConfig()
useHead({ title: 'Explore Literature Knowledge - OpenIsle' })
const modes = [
  { id:'papers',label:'Papers',path:'/search',needsQuery:true,placeholder:'Title, abstract, author, or keyword' },
  { id:'semantic',label:'Semantic',path:'/hybrid/search',needsQuery:true,placeholder:'Describe the concept you need' },
  { id:'knowledge',label:'Knowledge',path:'/knowledge/list',needsQuery:true,placeholder:'Claim, finding, or question' },
  { id:'methods',label:'Methods',path:'/methods/list',needsQuery:true,placeholder:'Method or analytical approach' },
  { id:'data',label:'Data points',path:'/data_points/list',needsQuery:true,placeholder:'Metric or measured quantity' },
  { id:'authors',label:'Authors',path:'/authors/list',needsQuery:true,placeholder:'Author name' },
  { id:'graph',label:'Relationships',path:'/graph',needsQuery:true,placeholder:'Topic for relationship graph' },
  { id:'timeline',label:'Timeline',path:'/timeline',needsQuery:false },
  { id:'compare',label:'Metric comparison',path:'/compare/metric',needsQuery:false,metric:true },
]
const mode=ref('papers'),query=ref(''),metric=ref(''),yearFrom=ref(''),yearTo=ref(''),pending=ref(false),error=ref(''),notice=ref(''),payload=ref(null)
const current=computed(()=>modes.find(item=>item.id===mode.value)||modes[0])
const items=computed(()=>{const value=payload.value;if(!value)return[];for(const key of ['results','hits','papers','items','knowledge','methods','data_points','authors','nodes','timeline','comparisons'])if(Array.isArray(value[key]))return value[key];return Array.isArray(value)?value:[]})
const resultCount=computed(()=>payload.value?.total ?? payload.value?.count ?? items.value.length)
const selectMode=(value)=>{mode.value=value;payload.value=null;error.value='';notice.value=''}
const search=async()=>{pending.value=true;error.value='';notice.value='';try{const params=new URLSearchParams();if(query.value.trim())params.set('q',query.value.trim());if(metric.value.trim())params.set('metric_name',metric.value.trim());if(yearFrom.value)params.set('year_from',yearFrom.value);if(yearTo.value)params.set('year_to',yearTo.value);params.set(current.value.id==='semantic'?'top_k':'limit','30');const path=current.value.id==='papers'&&!query.value.trim()?'/papers/list':current.value.path;const result=await $fetch(`${config.public.apiBaseUrl}/api/literature/explore${path}?${params}`);payload.value=result;if(result?.available===false)notice.value=result.message}catch(cause){error.value=cause?.data?.message||cause?.data?.error||cause?.message||'Unable to load this literature view.'}finally{pending.value=false}}
const title=(item,index)=>item.title||item.paper_title||item.full_name||item.name||`Result ${index+1}`
const summary=(item)=>item.abstract||item.summary||item.claim||item.description||item.research_question||item.method_name||item.metric_name||item.text||''
const fields=(item)=>Object.entries(item).filter(([key,value])=>value!=null&&!['abstract','summary','claim','description','research_question','text','title','paper_title'].includes(key)&&typeof value!=='object').slice(0,8)
const humanize=(value)=>value.replaceAll('_',' ').replace(/^./,c=>c.toUpperCase())
const display=(value)=>String(value).length>180?`${String(value).slice(0,180)}…`:String(value)
onMounted(search)
</script>

<style scoped>
.explorer-container{max-width:1180px}.explorer-tabs{display:flex;gap:1px;overflow:auto;margin-bottom:12px;border:1px solid var(--paper-line);background:var(--paper-line)}.explorer-tabs button{flex:1;min-width:105px;border:0;padding:12px;background:var(--paper-panel);color:var(--paper-muted);font-weight:750;cursor:pointer}.explorer-tabs button.active{background:var(--paper-teal);color:#fff}.query-panel{display:flex;align-items:end;gap:10px;padding:14px;margin-bottom:12px}.query-panel label{display:grid;gap:5px;flex:1;color:var(--paper-muted);font-size:12px;font-weight:700}.query-panel input{min-height:40px;border:1px solid var(--paper-line);padding:8px 10px}.result-panel{overflow:hidden}.result-heading{display:flex;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--paper-line)}.result-heading span{color:var(--paper-muted);font-size:12px}.result-list article{padding:18px;border-bottom:1px solid var(--paper-line)}.result-list h2{margin:0 0 7px;font-family:Georgia,serif;font-size:19px;font-weight:500}.result-list a{color:var(--paper-ink);text-decoration:none}.result-list p{color:var(--paper-muted);line-height:1.55}.result-list dl{display:flex;flex-wrap:wrap;gap:5px 16px;margin:8px 0 0;font-size:11px}.result-list dt{font-weight:800}.result-list dd{margin:0;color:var(--paper-muted)}.empty{padding:50px;text-align:center;color:var(--paper-muted)}.notice{padding:10px 14px;background:#fff6e8;color:#835713}.notice.error{background:#fff7f6;color:#923b32}@media(max-width:760px){.query-panel{align-items:stretch;flex-direction:column}}
</style>
