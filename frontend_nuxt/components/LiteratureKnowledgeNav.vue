<template>
  <nav class="literature-knowledge-nav" aria-label="Literature knowledge tools">
    <NuxtLink
      v-for="item in items"
      :key="item.id"
      :to="item.to"
      :class="{ active: activeItem === item.id }"
    >
      <span>{{ item.label }}</span>
      <small>{{ item.description }}</small>
    </NuxtLink>
  </nav>
</template>

<script setup>
const route = useRoute()

const items = [
  { id: 'papers', label: 'Papers', description: 'Corpus', to: '/literature' },
  { id: 'knowledge', label: 'Knowledge', description: 'Claims', to: '/literature/explore?mode=knowledge' },
  { id: 'methods', label: 'Methods', description: 'Workflows', to: '/literature/explore?mode=methods' },
  { id: 'data', label: 'Data', description: 'Metrics', to: '/literature/explore?mode=data' },
  { id: 'timeline', label: 'Timeline', description: 'Trends', to: '/literature/explore?mode=timeline' },
  { id: 'graph', label: 'Network', description: 'Relations', to: '/literature/explore?mode=graph' },
  { id: 'compare', label: 'Compare', description: 'Evidence', to: '/literature/explore?mode=compare' },
  { id: 'authors', label: 'Scholars', description: 'Profiles', to: '/literature/explore?mode=authors' },
  { id: 'institutions', label: 'Institutions', description: 'Collaboration', to: '/literature/explore?mode=institutions' },
]

const activeItem = computed(() => {
  if (route.path === '/literature') return 'papers'
  return String(route.query.mode || 'knowledge')
})
</script>

<style scoped>
.literature-knowledge-nav {
  display: grid;
  grid-template-columns: repeat(9, minmax(108px, 1fr));
  gap: 1px;
  overflow-x: auto;
  margin: 0 0 18px;
  border: 1px solid var(--paper-line);
  background: var(--paper-line);
}
.literature-knowledge-nav a {
  display: grid;
  gap: 3px;
  min-width: 108px;
  padding: 12px 13px;
  background: var(--paper-panel);
  color: var(--paper-ink);
  text-decoration: none;
}
.literature-knowledge-nav span { font-size: 12px; font-weight: 800; }
.literature-knowledge-nav small { color: var(--paper-muted); font-size: 10px; }
.literature-knowledge-nav a:hover,
.literature-knowledge-nav a.active { background: var(--paper-teal); color: #fff; }
.literature-knowledge-nav a:hover small,
.literature-knowledge-nav a.active small { color: rgba(255, 255, 255, .76); }
@media (max-width: 760px) {
  .literature-knowledge-nav { grid-template-columns: repeat(9, 120px); }
}
</style>
