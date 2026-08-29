<template>
  <div class="legacy-redirect" aria-live="polite">Redirecting to OpenIsle papers…</div>
</template>

<script setup>
definePageMeta({ middleware: () => navigateTo('/papers', { replace: true }) })
useHead({ title: 'OpenIsle Papers' })
</script>

<style scoped>
.legacy-redirect { width: min(1180px, calc(100% - 40px)); margin: 48px auto; color: #586a73; font-size: 14px; }
</style>
