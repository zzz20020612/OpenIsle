<template><main class="paper-shell"><div class="paper-container admin-container">
  <header class="paper-workspace-header"><div><div class="paper-page-eyebrow">Knowledge Base / Administration</div><h1 class="paper-page-title">Extraction quality</h1><p class="paper-page-description">Review coverage, completeness, extraction scores, failures, and prompt versions.</p></div><button class="paper-button" @click="load">Refresh</button></header>
  <LiteratureKnowledgeNav />
  <LiteratureAdminNav />
  <p v-if="error" class="admin-notice error">{{ error }}</p>
  <section v-if="loading" class="paper-panel empty">Loading quality evidence…</section>
  <template v-else>
    <section class="summary-grid"><article class="paper-panel"><strong>{{ stats.total_papers ?? 0 }}</strong><span>Eligible papers</span></article><article class="paper-panel"><strong>{{ coverage('knowledge_cards') }}%</strong><span>Knowledge coverage</span></article><article class="paper-panel"><strong>{{ coverage('methods') }}%</strong><span>Methods coverage</span></article><article class="paper-panel"><strong>{{ stats.quality_score?.average ?? '—' }}</strong><span>Average quality</span></article></section>
    <section class="quality-grid">
      <article class="paper-panel admin-card"><h2>Extraction coverage</h2><AdminDataTable :rows="coverageRows" empty="No extraction coverage data." /></article>
      <article class="paper-panel admin-card"><h2>Field completeness</h2><AdminDataTable :rows="completenessRows" empty="No field completeness data." /></article>
      <article class="paper-panel admin-card"><h2>Quality distribution</h2><AdminDataTable :rows="distributionRows" empty="No quality distribution data." /></article>
      <article class="paper-panel admin-card"><h2>Failed tasks</h2><AdminDataTable :rows="stats.failures || []" empty="No failed extraction tasks." /></article>
    </section>
    <section class="paper-panel admin-card"><div class="section-head"><div><h2>Prompt version comparison</h2><p>Compare extraction quality across prompt versions.</p></div></div><AdminDataTable :rows="prompts.versions || []" empty="No comparable prompt versions yet." /></section>
    <section class="paper-panel admin-card"><div class="section-head"><div><h2>Low-quality and unscored papers</h2><p>Threshold {{ threshold }} · {{ low.total ?? papers.length }} records</p></div><label>Threshold<input v-model.number="threshold" type="number" min="0" max="1" step="0.05" @change="loadLow" /></label></div>
      <div v-if="!papers.length" class="empty">No low-quality papers.</div><div v-else class="table-wrap"><table><thead><tr><th>ID</th><th>Paper</th><th>Journal</th><th>Score</th><th>Prompt</th><th>Action</th></tr></thead><tbody><tr v-for="paper in papers" :key="paper.paper_id"><td>{{ paper.paper_id }}</td><td><NuxtLink :to="`/literature/${paper.paper_id}`">{{ paper.title || 'Untitled' }}</NuxtLink></td><td>{{ paper.journal || '—' }}</td><td>{{ paper.quality_score ?? 'Unscored' }}</td><td>{{ paper.prompt_version || '—' }}</td><td><button :disabled="busyId===paper.paper_id" @click="reExtract(paper.paper_id)">{{ busyId===paper.paper_id?'Submitting…':'Re-extract' }}</button></td></tr></tbody></table></div>
    </section>
  </template>
</div></main></template>
<script setup>
import '~/assets/paper-platform.css'; import { authState, loadCurrentUser } from '~/utils/auth'
definePageMeta({middleware:'auth-client'}); useHead({title:'Literature Quality - OpenIsle'})
const api=useLiteratureAdmin(),stats=ref({}),low=ref({}),prompts=ref({}),threshold=ref(.6),loading=ref(true),error=ref(''),busyId=ref(null)
const papers=computed(()=>low.value.papers||[]); const coverage=(key)=>stats.value.coverage?.[key]?.coverage ?? 0
const coverageRows=computed(()=>Object.entries(stats.value.coverage||{}).map(([type,value])=>({type,count:value?.count??value?.papers_count??0,total_points:value?.total_points??'—',coverage:`${value?.coverage??0}%`})))
const completenessRows=computed(()=>Object.entries(stats.value.completeness||{}).map(([field,value])=>({field,count:value?.count??0,rate:`${value?.rate??0}%`})))
const distributionRows=computed(()=>Object.entries(stats.value.quality_score?.distribution||{}).map(([level,count])=>({level,count})))
const ensureAdmin=async()=>{if(!authState.role)await loadCurrentUser();if(authState.role!=='ADMIN')return navigateTo('/literature/workflow');return true}
const loadLow=async()=>{low.value=await api.get('/quality/low_quality',{threshold:threshold.value,limit:100})}
const load=async()=>{loading.value=true;error.value='';try{if(!await ensureAdmin())return;[stats.value,low.value,prompts.value]=await Promise.all([api.get('/quality/stats'),api.get('/quality/low_quality',{threshold:threshold.value,limit:100}),api.get('/quality/prompt_compare')])}catch(e){error.value=e?.data?.message||e?.data?.error||e.message}finally{loading.value=false}}
const reExtract=async(id)=>{if(!window.confirm(`Re-extract the knowledge card for literature paper ${id}?`))return;busyId.value=id;try{await api.post('/quality/re_extract',{paper_id:id});await load()}catch(e){error.value=e?.data?.message||e.message}finally{busyId.value=null}}
onMounted(load)
</script>
<style scoped src="~/assets/literature-admin.css"></style>
