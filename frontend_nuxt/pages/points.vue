<template>
  <div class="legacy-redirect" aria-live="polite">Redirecting to your OpenIsle profile…</div>
</template>

<script setup>
import { authState } from '~/utils/auth'

definePageMeta({
  middleware: () => navigateTo(
    authState.loggedIn && (authState.username || authState.userId)
      ? `/users/${authState.username || authState.userId}`
      : '/papers',
    { replace: true },
  ),
})
useHead({ title: 'OpenIsle' })
</script>

<style scoped>
.legacy-redirect { width: min(1180px, calc(100% - 40px)); margin: 48px auto; color: #586a73; font-size: 14px; }
</style>
