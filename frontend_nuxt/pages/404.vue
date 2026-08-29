<template>
  <main class="not-found" aria-labelledby="not-found-title">
    <p class="error-code">404</p>
    <h1 id="not-found-title">Research record not found</h1>
    <p>The page may have moved, been withdrawn, or may require a different access link.</p>
    <div class="not-found-actions">
      <NuxtLink to="/papers">Browse papers</NuxtLink>
      <NuxtLink to="/literature">Search the knowledge base</NuxtLink>
    </div>
  </main>
</template>

<script setup>
useHead({ title: 'Page Not Found - OpenIsle' })
</script>

<style scoped>
.not-found { width: min(760px, calc(100% - 40px)); min-height: 520px; display: flex; flex-direction: column; justify-content: center; margin: 0 auto; padding: 40px 0 70px; color: #2c424d; }
.error-code { margin: 0 0 8px; color: #1687a7; font-size: 13px; font-weight: 800; letter-spacing: .16em; }
h1 { margin: 0; font-family: Georgia, 'Times New Roman', serif; font-size: clamp(38px, 6vw, 58px); font-weight: 400; line-height: 1.08; }
.not-found > p:not(.error-code) { max-width: 620px; margin: 20px 0 0; color: #586a73; font-size: 16px; line-height: 1.7; }
.not-found-actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 30px; padding-top: 22px; border-top: 1px solid #c8d3d7; }
.not-found-actions a { padding: 11px 15px; border: 1px solid #0065a8; color: #0065a8; font-size: 13px; font-weight: 750; text-decoration: none; }
.not-found-actions a:first-child { color: #fff; background: #0065a8; }
</style>
