<template>
  <main class="paper-shell"><div class="paper-container admin-container">
    <header class="paper-workspace-header"><div><div class="paper-page-eyebrow">Knowledge Base / Settings</div><h1 class="paper-page-title">Literature system settings</h1><p class="paper-page-description">The original literature-system preferences and workflow configuration, arranged in the OpenIsle interface.</p></div></header>
    <LiteratureKnowledgeNav />
    <LiteratureAdminNav />
    <div class="settings-layout">
      <aside class="paper-panel settings-nav">
        <strong>Interface preferences</strong>
        <button v-for="item in preferenceTabs" :key="item.id" :class="{active:tab===item.id}" @click="tab=item.id">{{ item.label }}</button>
        <strong>System configuration</strong>
        <button :class="{active:tab==='workflow'}" @click="tab='workflow'">Workflow configuration</button>
        <button :class="{active:tab==='about'}" @click="tab='about'">About</button>
      </aside>

      <section class="settings-content">
        <p v-if="message" class="admin-notice" :class="{error}">{{ message }}</p>

        <form v-if="tab==='view'" class="paper-panel admin-card" @submit.prevent="savePreferences">
          <h2>View preferences</h2><p>Default landing page, paper tab, and relationship-network view.</p>
          <div class="admin-form"><label>Default page<select v-model="prefs.default_view"><option value="dashboard">Dashboard</option><option value="search">Search</option><option value="knowledgebase">Knowledge base</option><option value="timeline">Timeline</option><option value="network">Network</option></select></label><label>Paper detail default tab<select v-model="prefs.paper_default_tab"><option value="knowledge">Knowledge</option><option value="summary">Summary</option><option value="methods">Methods</option><option value="data">Data points</option><option value="citations">Citations</option></select></label><label>Network layout<select v-model="prefs.network_layout"><option value="force">Force directed</option><option value="circle">Circle</option><option value="hierarchical">Hierarchical</option></select></label><label>Network node size<select v-model="prefs.network_node_size"><option value="small">Small</option><option value="normal">Normal</option><option value="large">Large</option></select></label><label class="check"><input v-model="prefs.knowledge_compact" type="checkbox" /> Compact knowledge cards</label></div><SavePreferenceButtons />
        </form>

        <form v-else-if="tab==='search'" class="paper-panel admin-card" @submit.prevent="savePreferences">
          <h2>Search preferences</h2><p>Original default retrieval mode, page size, hybrid weights, and highlighting.</p>
          <div class="admin-form"><label>Default mode<select v-model="prefs.search_default_mode"><option value="keyword">Keyword</option><option value="semantic">Semantic</option><option value="hybrid">Hybrid</option></select></label><label>Results per page<input v-model.number="prefs.search_results_per_page" type="number" min="5" max="100" step="5" /></label><label>Full-text weight<input v-model.number="prefs.fts_weight" type="number" min="0" max="1" step="0.1" /></label><label>Vector weight<input :value="(1-Number(prefs.fts_weight||0)).toFixed(1)" disabled /></label><label class="check"><input v-model="prefs.highlight_keywords" type="checkbox" /> Highlight search terms</label></div><SavePreferenceButtons />
        </form>

        <form v-else-if="tab==='display'" class="paper-panel admin-card" @submit.prevent="savePreferences">
          <h2>Data display</h2><p>Original list pagination, density, animation, and empty-state options.</p>
          <div class="admin-form"><label>Default page size<input v-model.number="prefs.page_size" type="number" min="5" max="100" step="5" /></label><label>List density<select v-model="prefs.density"><option value="compact">Compact</option><option value="comfortable">Comfortable</option><option value="loose">Loose</option></select></label><label class="check"><input v-model="prefs.show_empty_state" type="checkbox" /> Show empty-state guidance</label><label class="check"><input v-model="prefs.enable_animations" type="checkbox" /> Enable interaction animations</label></div><SavePreferenceButtons />
        </form>

        <form v-else-if="tab==='notification'" class="paper-panel admin-card" @submit.prevent="savePreferences">
          <h2>Notifications and prompts</h2><p>Control the original toast display duration.</p><div class="admin-form"><label>Toast duration (seconds)<input v-model.number="prefs.show_toast_duration" type="number" min="1" max="30" /></label></div><SavePreferenceButtons />
        </form>

        <form v-else-if="tab==='advanced'" class="paper-panel admin-card" @submit.prevent="savePreferences">
          <h2>Advanced</h2><p>Original destructive-action confirmation and dashboard refresh controls.</p><div class="admin-form"><label class="check"><input v-model="prefs.confirm_destructive" type="checkbox" /> Confirm destructive actions</label><label class="check"><input v-model="prefs.auto_refresh_dashboard" type="checkbox" /> Automatically refresh dashboard</label><label>Refresh interval (seconds)<input v-model.number="prefs.dashboard_refresh_interval" type="number" min="5" max="600" step="5" /></label></div><SavePreferenceButtons show-reset @reset="resetPreferences" />
        </form>

        <section v-else-if="tab==='about'" class="paper-panel admin-card"><h2>About</h2><dl class="about"><div><dt>System</dt><dd>Literature System</dd></div><div><dt>Original version</dt><dd>v1.0.0</dd></div><div><dt>Original frontend</dt><dd>JavaScript + Chart.js + vis-network</dd></div><div><dt>Processing engine</dt><dd>Koa 2.x + SQLite + sqlite-vec</dd></div><div><dt>Preference storage</dt><dd><code>{{ storageKey }}</code> in this browser</dd></div><div><dt>Workflow settings</dt><dd>Stored by the original processing engine; credentials remain masked.</dd></div></dl></section>

        <template v-else>
          <section v-if="!isAdmin" class="paper-panel admin-card"><h2>Workflow configuration</h2><p>Administrator access is required to view or change service credentials and processing priorities.</p></section>
          <section v-else-if="loading" class="paper-panel empty">Loading settings…</section>
          <form v-else @submit.prevent="saveWorkflow">
            <section v-for="group in groups" :key="group.title" class="paper-panel admin-card"><h2>{{ group.title }}</h2><p>{{ group.description }}</p><div class="admin-form"><label v-for="field in group.fields" :key="field.key">{{ field.label }}<input v-if="field.type!=='select'" v-model="workflow[field.key]" :type="field.type||'text'" :step="field.step" :min="field.min" :max="field.max" :placeholder="field.secret&&configured(field.key)?'Configured — leave blank to keep current value':''"/><select v-else v-model="workflow[field.key]"><option v-for="option in field.options" :key="option" :value="option">{{ option }}</option></select><small v-if="field.secret">{{ configured(field.key)?'Credential is configured.':'Credential is not configured.' }}</small><button v-if="field.test" type="button" class="connection-test" :disabled="testing===field.test" @click="testConnection(field.test)">{{ testing===field.test?'Testing…':'Test connection' }}</button><small v-if="field.test&&testResults[field.test]" :class="testResults[field.test].success||testResults[field.test].ok?'test-ok':'test-bad'">{{ connectionMessage(testResults[field.test]) }}</small></label></div></section><button class="admin-action" :disabled="saving">{{ saving?'Saving…':'Save workflow settings' }}</button>
          </form>
        </template>
      </section>
    </div>
  </div></main>
</template>

<script setup>
import '~/assets/paper-platform.css'
import { authState, loadCurrentUser } from '~/utils/auth'
useHead({ title: 'Literature Settings - OpenIsle' })
const api=useLiteratureAdmin(),route=useRoute(),router=useRouter(),storageKey='litre_sys_ui_prefs_v1'
const preferenceTabs=[{id:'view',label:'View preferences'},{id:'search',label:'Search preferences'},{id:'display',label:'Data display'},{id:'notification',label:'Notifications'},{id:'advanced',label:'Advanced'}]
const defaults={default_view:'dashboard',paper_default_tab:'knowledge',knowledge_compact:false,network_layout:'force',network_node_size:'normal',search_default_mode:'keyword',search_results_per_page:20,fts_weight:.4,vector_weight:.6,highlight_keywords:true,page_size:20,show_empty_state:true,enable_animations:true,density:'comfortable',show_toast_duration:3,confirm_destructive:true,auto_refresh_dashboard:false,dashboard_refresh_interval:30}
const prefs=reactive({...defaults}),tab=ref(String(route.query.cat||'view')),isAdmin=ref(false),workflow=reactive({}),original=ref({}),loading=ref(false),saving=ref(false),testing=ref(''),testResults=reactive({}),message=ref(''),error=ref(false)
const groups=[{title:'Collection sources',description:'Default providers used for online metadata collection.',fields:[{key:'collect_sources',label:'Sources (comma separated)'}]},{title:'PDF retrieval priority',description:'Lower values run first; use 0 to disable a strategy.',fields:[{key:'pdf_strategy_crossref_text_mining',label:'Crossref text mining',type:'number',min:0,max:9},{key:'pdf_strategy_crossref_pdf',label:'Crossref PDF',type:'number',min:0,max:9},{key:'pdf_strategy_oa_url',label:'Open-access URL',type:'number',min:0,max:9},{key:'pdf_strategy_doi_redirect',label:'DOI redirect',type:'number',min:0,max:9},{key:'pdf_strategy_unpaywall',label:'Unpaywall',type:'number',min:0,max:9}]},{title:'PDF parser priority',description:'The original parser fallback order; lower values run first and 0 disables an engine.',fields:[{key:'pdf_parser_mineru_api',label:'MinerU API',type:'number',min:0,max:9},{key:'pdf_parser_pymupdf',label:'PyMuPDF',type:'number',min:0,max:9},{key:'pdf_parser_marker_gpu',label:'Marker GPU',type:'number',min:0,max:9},{key:'pdf_parser_marker_cpu',label:'Marker CPU',type:'number',min:0,max:9},{key:'mineru_api_key',label:'MinerU API key',type:'password',secret:true,test:'mineru'}]},{title:'LLM extraction',description:'Original OpenAI-compatible endpoint and knowledge-extraction parameters.',fields:[{key:'llm_base_url',label:'Base URL'},{key:'llm_model',label:'Model'},{key:'llm_max_tokens',label:'Maximum tokens',type:'number',min:1},{key:'llm_temperature',label:'Temperature',type:'number',step:'0.1',min:0,max:2},{key:'llm_request_timeout',label:'Timeout seconds',type:'number',min:1},{key:'llm_max_retries',label:'Maximum retries',type:'number',min:0},{key:'llm_api_key',label:'API key',type:'password',secret:true,test:'llm'}]},{title:'Semantic search',description:'Original embedding endpoint and vector dimensions.',fields:[{key:'embedding_base_url',label:'Base URL'},{key:'embedding_model',label:'Model'},{key:'embedding_dim',label:'Dimensions',type:'number'},{key:'embedding_batch_size',label:'Batch size',type:'number'},{key:'embedding_api_key',label:'API key',type:'password',secret:true,test:'embedding'}]},{title:'Provider credentials',description:'Original optional credentials for higher limits or licensed sources.',fields:[{key:'semantic_scholar_api_key',label:'Semantic Scholar API key',type:'password',secret:true},{key:'wos_api_key',label:'Web of Science API key',type:'password',secret:true,test:'wos'},{key:'scopus_api_keys',label:'Scopus API keys',type:'password',secret:true,test:'scopus'}]}]
const secretKeys=new Set(groups.flatMap(group=>group.fields.filter(field=>field.secret).map(field=>field.key)))
const configured=key=>Boolean(original.value[`${key}_configured`]||original.value[key])
const readPreferences=()=>{try{Object.assign(prefs,defaults,JSON.parse(localStorage.getItem(storageKey)||'{}'))}catch{Object.assign(prefs,defaults)}}
const savePreferences=()=>{prefs.vector_weight=1-Number(prefs.fts_weight||0);localStorage.setItem(storageKey,JSON.stringify(prefs));error.value=false;message.value='Preferences saved in this browser.'}
const resetPreferences=()=>{if(!window.confirm('Restore all interface preferences to their original defaults?'))return;Object.assign(prefs,defaults);savePreferences()}
const loadWorkflow=async()=>{if(!isAdmin.value)return;loading.value=true;try{const data=await api.get('/workflow/settings');original.value=data;Object.entries(data).forEach(([key,value])=>{if(!secretKeys.has(key))workflow[key]=Array.isArray(value)?value.join(', '):value});secretKeys.forEach(key=>workflow[key]='')}catch(cause){error.value=true;message.value=cause?.data?.message||cause.message}finally{loading.value=false}}
const saveWorkflow=async()=>{saving.value=true;error.value=false;message.value='';try{const body={};groups.flatMap(group=>group.fields).forEach(field=>{let value=workflow[field.key];if(field.secret&&!value)return;if(field.key==='collect_sources')value=String(value||'').split(',').map(item=>item.trim()).filter(Boolean);body[field.key]=value});await api.post('/workflow/settings',body);message.value='Workflow settings saved.';await loadWorkflow()}catch(cause){error.value=true;message.value=cause?.data?.message||cause.message}finally{saving.value=false}}
const testConnection=async service=>{testing.value=service;delete testResults[service];const body={service};if(service==='llm')Object.assign(body,{api_key:workflow.llm_api_key||'',base_url:workflow.llm_base_url||'',model:workflow.llm_model||''});else if(service==='embedding')Object.assign(body,{api_key:workflow.embedding_api_key||'',base_url:workflow.embedding_base_url||'',model:workflow.embedding_model||''});else if(service==='mineru')body.api_key=workflow.mineru_api_key||'';else if(service==='wos')body.api_key=workflow.wos_api_key||'';else if(service==='scopus')body.api_key=workflow.scopus_api_keys||'';try{testResults[service]=await api.post('/test/connection',body)}catch(cause){testResults[service]={success:false,message:cause?.data?.message||cause.message}}finally{testing.value=''}}
const connectionMessage=result=>result?.message||result?.error||(result?.success||result?.ok?'Connection successful.':'Connection failed.')
watch(tab,value=>router.replace({query:{...route.query,cat:value}}))
onMounted(async()=>{readPreferences();if(!authState.role)await loadCurrentUser();isAdmin.value=authState.role==='ADMIN';await loadWorkflow()})
</script>

<style scoped src="~/assets/literature-admin.css"></style>
<style scoped>
.settings-layout{display:grid;grid-template-columns:230px minmax(0,1fr);gap:16px}.settings-nav{align-self:start;display:flex;flex-direction:column;padding:10px}.settings-nav strong{padding:12px 10px 7px;color:var(--paper-soft);font-size:10px;text-transform:uppercase;letter-spacing:.08em}.settings-nav button{border:0;border-left:3px solid transparent;background:transparent;padding:10px;text-align:left;color:var(--paper-ink);cursor:pointer}.settings-nav button:hover,.settings-nav button.active{border-left-color:var(--paper-teal);background:#edf5f7;color:var(--paper-teal);font-weight:800}.settings-content{min-width:0}.check{display:flex!important;align-items:center;gap:8px}.check input{width:auto!important}.connection-test{align-self:start;border:1px solid var(--paper-line);background:#fff;padding:6px 9px;color:var(--paper-teal);cursor:pointer}.test-ok{color:#236b52!important}.test-bad{color:#a33d34!important}.about{margin:0}.about div{display:grid;grid-template-columns:170px 1fr;border-top:1px solid var(--paper-line);padding:10px 0}.about dt{color:var(--paper-soft);font-size:11px}.about dd{margin:0}@media(max-width:760px){.settings-layout{grid-template-columns:1fr}.settings-nav{display:grid;grid-template-columns:repeat(2,1fr)}}
</style>
