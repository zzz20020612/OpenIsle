<template>
  <main class="paper-shell">
    <div class="paper-container admin-container">
      <header class="paper-workspace-header"><div><div class="paper-page-eyebrow">Knowledge Base / Administration</div><h1 class="paper-page-title">Engine restoration status</h1><p class="paper-page-description">Distinguish installed source code from capabilities that are configured and actually runnable.</p></div><button class="paper-button" :disabled="busy" @click="runAll">Test all connections</button></header>
      <LiteratureKnowledgeNav />
      <LiteratureAdminNav />
      <p v-if="error" class="admin-notice error">{{ error }}</p>
      <section class="paper-panel restoration-summary" :class="capabilities?.runtime_ready ? 'ready' : 'incomplete'"><div><span class="paper-mini-label">Teammate engine</span><h2>{{ !capabilities ? 'Checking engine…' : capabilities.runtime_ready ? 'Core literature workflow ready' : 'Core workflow incomplete' }}</h2><p v-if="capabilities?.missing_required?.length">Required local dependencies missing: {{ capabilities.missing_required.join(', ') }}</p><p v-else-if="capabilities">Collection, PDF processing, LLM extraction, keyword search, graph, author, institution, workflow and quality modules have their required local runtime.</p><p v-if="capabilities?.missing_full_restore?.length">Optional or external enhancements unavailable: {{ capabilities.missing_full_restore.join(', ') }}</p><p v-if="capabilities?.original_source_limitations?.length">Original source limitations: {{ capabilities.original_source_limitations.join(', ') }}</p></div><button class="admin-action" :disabled="loadingCapabilities" @click="loadCapabilities">{{ loadingCapabilities ? 'Checking…' : 'Refresh audit' }}</button></section>
      <section v-if="capabilities" class="capability-groups">
        <article class="paper-panel capability-group"><h2>PDF parsers</h2><dl><div v-for="(item, name) in capabilities.parsers" :key="name"><dt>{{ name }}</dt><dd :class="item.implemented && item.configured ? 'ok' : 'bad'">{{ capabilityLabel(item) }} · priority {{ item.priority || 'off' }}</dd></div></dl></article>
        <article class="paper-panel capability-group"><h2>Models</h2><dl><div v-for="(item, name) in capabilities.models" :key="name"><dt>{{ name }}</dt><dd :class="item.configured ? 'ok' : 'bad'">{{ item.configured ? item.model : 'Key not configured' }}</dd></div></dl></article>
        <article class="paper-panel capability-group"><h2>Runtime dependencies</h2><dl><div v-for="(available, name) in capabilities.dependencies" :key="name"><dt>{{ name }}</dt><dd :class="available ? 'ok' : 'bad'">{{ available ? 'Installed' : 'Missing' }}</dd></div></dl></article>
        <article class="paper-panel capability-group source-capabilities"><h2>Metadata and PDF sources</h2><dl><div v-for="(item, name) in capabilities.sources" :key="name"><dt>{{ name }}</dt><dd :class="item.configured || item.anonymous_fallback ? 'ok' : 'bad'">{{ sourceLabel(item) }}</dd></div></dl></article>
      </section>
      <section class="service-grid"><article v-for="service in services" :key="service.id" class="paper-panel service-card"><div class="service-heading"><h2>{{ service.label }}</h2><span :class="result(service.id)?.ok === true || result(service.id)?.success === true ? 'ok' : result(service.id) ? 'bad' : ''">{{ status(service.id) }}</span></div><p>{{ service.description }}</p><button class="admin-action" :disabled="testing === service.id" @click="test(service.id)">{{ testing === service.id ? 'Testing…' : 'Test connection' }}</button><pre v-if="result(service.id)">{{ pretty(result(service.id)) }}</pre></article></section>
      <section class="paper-panel admin-card"><h2>Knowledge graph diagnostics</h2><button class="admin-action" @click="graphCheck">Run graph diagnostics</button><AdminObjectTable :value="graph" /></section>
    </div>
  </main>
</template>

<script setup>
import '~/assets/paper-platform.css'
import { authState, loadCurrentUser } from '~/utils/auth'

definePageMeta({ middleware: 'auth-client' })
useHead({ title: 'Literature Engine Restoration - OpenIsle' })

const config = useRuntimeConfig()
const api = useLiteratureAdmin()
const testing = ref('')
const busy = ref(false)
const loadingCapabilities = ref(false)
const results = ref({})
const capabilities = ref(null)
const graph = ref({})
const error = ref('')
const services = [
  { id: 'llm', label: 'LLM extraction', description: 'Knowledge-card, method, and data-point extraction.' },
  { id: 'embedding', label: 'Embedding', description: 'Vector and hybrid semantic search.' },
  { id: 'mineru', label: 'MinerU parser', description: 'High-fidelity structured PDF parsing.' },
  { id: 'wos', label: 'Web of Science', description: 'Licensed metadata source; optional API key.' },
  { id: 'scopus', label: 'Scopus', description: 'Licensed metadata source; optional API key.' },
]

const ensure = async () => {
  if (!authState.role) await loadCurrentUser()
  if (authState.role !== 'ADMIN') {
    await navigateTo('/literature/workflow')
    return false
  }
  await loadCapabilities()
  return true
}
const result = id => results.value[id]
const status = id => !result(id) ? 'Not tested' : result(id).ok === false || result(id).success === false ? 'Unavailable' : 'Available'
const pretty = value => JSON.stringify(value, null, 2)
const capabilityLabel = item => !item.implemented ? 'Not implemented in original source' : item.configured ? 'Available' : 'Waiting for configuration'
const sourceLabel = item => item.configured ? 'Available' : item.anonymous_fallback ? 'Anonymous fallback' : item.requires_key ? 'API key required' : 'Unavailable'
const loadCapabilities = async () => {
  loadingCapabilities.value = true
  error.value = ''
  try { capabilities.value = await $fetch(`${config.public.apiBaseUrl}/api/literature/capabilities`) }
  catch (requestError) { error.value = requestError?.data?.message || requestError.message }
  finally { loadingCapabilities.value = false }
}
const test = async id => {
  testing.value = id
  error.value = ''
  try { results.value[id] = await api.post('/test/connection', { service: id }) }
  catch (requestError) { results.value[id] = { ok: false, error: requestError?.data?.message || requestError.message } }
  finally { testing.value = '' }
}
const runAll = async () => { busy.value = true; for (const service of services) await test(service.id); await loadCapabilities(); busy.value = false }
const graphCheck = async () => { try { graph.value = await $fetch(`${config.public.apiBaseUrl}/api/literature/explore/graph/diagnostics`) } catch (requestError) { error.value = requestError?.data?.message || requestError.message } }
onMounted(ensure)
</script>

<style scoped src="~/assets/literature-admin.css"></style>
<style scoped>
.restoration-summary{display:flex;align-items:center;justify-content:space-between;gap:24px;margin-bottom:16px;border-left:4px solid #a33d34}.restoration-summary.ready{border-left-color:#236b52}.restoration-summary h2{margin:5px 0}.restoration-summary p{margin:0;color:var(--paper-muted);font-size:12px}.capability-groups{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-bottom:16px}.source-capabilities{grid-column:1/-1}.source-capabilities dl{grid-template-columns:repeat(3,minmax(0,1fr))}.capability-group h2{margin-top:0}.capability-group dl{display:grid;gap:8px;margin:0}.capability-group dl div{display:flex;justify-content:space-between;gap:12px;border-top:1px solid var(--paper-line);padding-top:8px;font-size:11px}.capability-group dd{margin:0;text-align:right}.ok{color:#236b52}.bad{color:#a33d34}.service-heading{display:flex;justify-content:space-between;gap:12px}.service-heading span{color:var(--paper-muted);font-size:11px;font-weight:800;text-transform:uppercase}.service-card pre{max-height:150px;overflow:auto;padding:10px;background:#f3f6f8;font-size:10px;white-space:pre-wrap}@media(max-width:900px){.capability-groups{grid-template-columns:1fr}.source-capabilities{grid-column:auto}.source-capabilities dl{grid-template-columns:1fr}.restoration-summary{align-items:flex-start;flex-direction:column}}
</style>
