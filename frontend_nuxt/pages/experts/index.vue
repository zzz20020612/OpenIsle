<template>
  <div class="legacy-redirect" aria-live="polite">Redirecting to the scholar directory…</div>
</template>

<script setup>
definePageMeta({
  middleware: () => navigateTo(
    { path: '/literature/explore', query: { mode: 'authors' } },
    { replace: true, redirectCode: 302 },
  ),
})
useHead({ title: 'Scholar Directory - OpenIsle' })
</script>

<style scoped>
.legacy-redirect {
  width: min(1180px, calc(100% - 40px));
  margin: 48px auto;
  color: #586a73;
  font-size: 14px;
}
</style>
