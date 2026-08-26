<template>
  <nav class="literature-admin-nav" aria-label="Literature administration">
    <NuxtLink v-for="item in items" :key="item.to" :to="item.to">{{ item.label }}</NuxtLink>
  </nav>
</template>

<script setup>
const items = [
  { to: '/literature/workflow', label: 'Overview' },
  { to: '/literature/workflow/process', label: 'Collect & process' },
  { to: '/literature/workflow/jobs', label: 'Jobs' },
  { to: '/literature/workflow/quality', label: 'Quality' },
  { to: '/literature/workflow/authors', label: 'Authors' },
  { to: '/literature/workflow/diagnostics', label: 'Diagnostics' },
  { to: '/literature/workflow/settings', label: 'Settings' },
]
</script>

<style scoped>
.literature-admin-nav{display:flex;overflow:auto;margin:0 0 18px;border:1px solid var(--paper-line);background:var(--paper-line);gap:1px}.literature-admin-nav a{min-width:max-content;padding:11px 14px;background:#fff;color:var(--paper-muted);font-size:12px;font-weight:800;text-decoration:none}.literature-admin-nav a.router-link-exact-active{background:var(--paper-teal);color:#fff}
</style>
