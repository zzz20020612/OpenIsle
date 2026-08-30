<template>
  <main class="paper-shell"><div class="paper-container dashboard-container">
    <header class="paper-workspace-header"><div><div class="paper-page-eyebrow">Knowledge Base / Dashboard</div><h1 class="paper-page-title">Literature dashboard</h1><p class="paper-page-description">The original corpus coverage and processing summary, presented inside OpenIsle.</p></div><button class="paper-button" :disabled="pending" @click="load">Refresh</button></header>
    <LiteratureKnowledgeNav />
    <p v-if="error" class="dashboard-error">{{ error }}</p>
    <section class="dashboard-stats">
      <article v-for="item in statItems" :key="item.label"><strong>{{ format(item.value) }}</strong><span>{{ item.label }}</span></article>
    </section>
    <section class="paper-panel jobs-panel"><div class="section-heading"><div><h2>Parse jobs</h2><p>The same stage and status counts shown by the original system.</p></div></div>
      <table v-if="jobs.length"><thead><tr><th>Stage</th><th>Status</th><th>Count</th></tr></thead><tbody><tr v-for="(job,index) in jobs" :key="`${job.stage}-${job.status}-${index}`"><td>{{ job.stage || '—' }}</td><td>{{ job.status || '—' }}</td><td>{{ format(job.c) }}</td></tr></tbody></table>
      <div v-else class="empty">{{ pending ? 'Loading statistics…' : 'No parse jobs are recorded.' }}</div>
    </section>
  </div></main>
</template>

<script setup>
import '~/assets/paper-platform.css'
import LiteratureKnowledgeNav from '~/components/LiteratureKnowledgeNav.vue'
const config=useRuntimeConfig(); const stats=ref({}); const pending=ref(false); const error=ref('')
useHead({title:'Literature Dashboard - OpenIsle'})
const statItems=computed(()=>[
  ['Total papers','total_papers'],['Valid papers','valid_papers'],['Indexed papers','indexed_papers'],['Coverage','coverage'],['Sections','sections'],['Figures','figures'],['Data points','data_points'],['Valid data points','data_points_valid'],
].map(([label,key])=>({label,value:key==='coverage'?`${stats.value[key]||0}%`:stats.value[key]||0})))
const jobs=computed(()=>Array.isArray(stats.value.parse_jobs)?stats.value.parse_jobs:[])
const format=value=>typeof value==='number'?value.toLocaleString():value
const load=async()=>{pending.value=true;error.value='';try{stats.value=await $fetch(`${config.public.apiBaseUrl}/api/literature/explore/stats`)}catch(cause){error.value=cause?.data?.message||cause?.message||'Unable to load literature statistics.'}finally{pending.value=false}}
onMounted(load)
</script>

<style scoped>
.dashboard-container{max-width:1180px}.dashboard-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;margin-bottom:16px;border:1px solid var(--paper-line);background:var(--paper-line)}.dashboard-stats article{display:grid;gap:5px;padding:18px;background:#fff}.dashboard-stats strong{font-family:Georgia,serif;font-size:26px;font-weight:500}.dashboard-stats span{color:var(--paper-muted);font-size:10px;font-weight:800;letter-spacing:.06em;text-transform:uppercase}.section-heading{padding:16px 18px;border-bottom:1px solid var(--paper-line)}.section-heading h2{margin:0;font:500 21px Georgia,serif}.section-heading p{margin:5px 0 0;color:var(--paper-muted);font-size:12px}.jobs-panel table{width:100%;border-collapse:collapse}.jobs-panel th,.jobs-panel td{padding:12px 18px;border-bottom:1px solid var(--paper-line);text-align:left;font-size:12px}.jobs-panel th{color:var(--paper-muted);font-size:10px;text-transform:uppercase}.empty{padding:45px;text-align:center;color:var(--paper-muted)}.dashboard-error{padding:11px 14px;background:#fff4f2;color:#8b3028}@media(max-width:760px){.dashboard-stats{grid-template-columns:repeat(2,1fr)}}
</style>
