<template>
  <div class="literature-navigation-shell">
    <nav class="literature-knowledge-nav" aria-label="Literature knowledge tools">
      <NuxtLink
        v-for="item in items"
        :key="item.id"
        :to="item.to"
        :class="{ active: activeItem === item.id }"
      >
        <span>{{ item.label }}</span>
      </NuxtLink>
    </nav>
    <div class="engine-health" :class="healthState" :title="healthMessage" aria-live="polite">
      <span aria-hidden="true" />
      Literature engine {{ healthLabel }}
    </div>
  </div>
</template>

<script setup>
const route = useRoute()
const config = useRuntimeConfig()
const healthState = ref('checking')
const healthMessage = ref('Checking the literature processing engine.')
let healthTimer

const items = [
  { id: 'dashboard', label: 'Dashboard', description: 'Corpus status', to: '/literature/dashboard' },
  { id: 'search', label: 'Search & KB', description: 'Papers and evidence', to: '/literature' },
  { id: 'timeline', label: 'Timeline', description: 'Publication trends', to: '/literature/timeline' },
  { id: 'graph', label: 'Network', description: 'Relations', to: '/literature/network' },
  { id: 'compare', label: 'Compare', description: 'Cross-paper metrics', to: '/literature/compare' },
  { id: 'vector', label: 'Vector DB', description: 'Embeddings', to: '/literature/vector' },
  { id: 'authors', label: 'Authors', description: 'Scholar profiles', to: '/literature/authors' },
  { id: 'institutions', label: 'Institutions', description: 'Collaboration', to: '/literature/institutions' },
  { id: 'workflow', label: 'Workflow', description: 'Processing pipeline', to: '/literature/workflow' },
  { id: 'quality', label: 'Quality', description: 'Extraction checks', to: '/literature/workflow/quality' },
  { id: 'settings', label: 'Settings', description: 'Sources and models', to: '/literature/workflow/settings' },
]

const activeItem = computed(() => {
  if (route.path === '/literature') return 'search'
  if (route.path === '/literature/dashboard') return 'dashboard'
  if (route.path === '/literature/timeline') return 'timeline'
  if (route.path === '/literature/compare') return 'compare'
  if (route.path === '/literature/vector') return 'vector'
  if (route.path === '/literature/network') return 'graph'
  if (route.path.startsWith('/literature/authors')) return 'authors'
  if (route.path === '/literature/institutions') return 'institutions'
  if (route.path === '/literature/workflow/quality') return 'quality'
  if (route.path === '/literature/workflow/settings') return 'settings'
  if (route.path.startsWith('/literature/workflow')) return 'workflow'
  return 'search'
})

const healthLabel = computed(() => ({ online: 'online', offline: 'unavailable', checking: 'checking' }[healthState.value]))
const checkHealth = async () => {
  try {
    await $fetch(`${config.public.apiBaseUrl}/api/literature/health`)
    healthState.value = 'online'
    healthMessage.value = 'The literature processing engine is responding normally.'
  } catch (cause) {
    healthState.value = 'offline'
    healthMessage.value = cause?.data?.message || cause?.data?.error || cause?.message || 'The literature processing engine is unavailable.'
  }
}

onMounted(() => {
  checkHealth()
  healthTimer = window.setInterval(checkHealth, 10000)
})
onBeforeUnmount(() => window.clearInterval(healthTimer))
</script>

<style scoped>
.literature-navigation-shell { margin: 0 0 18px; }
.literature-knowledge-nav {
  display: grid;
  grid-template-columns: repeat(11, minmax(112px, 1fr));
  gap: 1px;
  overflow-x: auto;
  margin: 0;
  border: 1px solid var(--paper-line);
  background: var(--paper-line);
}
.engine-health { display:flex; align-items:center; justify-content:flex-end; gap:7px; min-height:28px; padding:5px 10px; border:1px solid var(--paper-line); border-top:0; background:var(--paper-panel-subtle); color:var(--paper-muted); font-size:10px; font-weight:800; letter-spacing:.04em; text-transform:uppercase; }
.engine-health span { width:8px; height:8px; border-radius:50%; background:#b08a39; }
.engine-health.online span { background:#34866a; }
.engine-health.offline span { background:#a33d34; }
.literature-knowledge-nav a {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 108px;
  padding: 13px 10px;
  background: var(--paper-panel);
  color: var(--paper-ink);
  text-decoration: none;
}
.literature-knowledge-nav span { font-size: 12px; font-weight: 800; }
.literature-knowledge-nav a:hover,
.literature-knowledge-nav a.active { background: var(--paper-teal); color: #fff; }
@media (max-width: 760px) {
  .literature-knowledge-nav { grid-template-columns: repeat(11, 126px); }
}
</style>
