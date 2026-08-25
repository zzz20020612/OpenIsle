<template>
  <div />
</template>

<script setup>
definePageMeta({
  middleware: (to) => navigateTo(
    { path: '/literature/workflow', query: to.query },
    { replace: true, redirectCode: 302 },
  ),
})
</script>
