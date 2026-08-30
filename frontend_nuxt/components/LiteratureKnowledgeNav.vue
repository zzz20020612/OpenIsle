<template>
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
</template>

<script setup>
const route = useRoute()

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
</script>

<style scoped>
.literature-knowledge-nav {
  display: grid;
  grid-template-columns: repeat(11, minmax(112px, 1fr));
  gap: 1px;
  overflow-x: auto;
  margin: 0 0 18px;
  border: 1px solid var(--paper-line);
  background: var(--paper-line);
}
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
