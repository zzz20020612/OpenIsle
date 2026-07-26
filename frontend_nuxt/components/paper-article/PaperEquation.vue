<template>
  <div class="article-equation" :class="{ invalid: renderError }">
    <div v-if="renderError" class="equation-error">Equation preview unavailable: {{ renderError }}</div>
    <div v-else class="equation-render" v-html="rendered" />
    <span v-if="block.numbered" class="equation-number">({{ number }})</span>
  </div>
</template>

<script setup>
import katex from 'katex'
import 'katex/dist/katex.min.css'

const props = defineProps({
  block: { type: Object, required: true },
  number: { type: Number, default: 1 },
})

const renderError = ref('')
const rendered = computed(() => {
  renderError.value = ''
  if (!props.block?.latex?.trim()) return ''
  try {
    return katex.renderToString(props.block.latex, {
      displayMode: true,
      throwOnError: true,
      trust: false,
      strict: 'warn',
    })
  } catch (error) {
    renderError.value = error?.message || 'Check the LaTeX syntax.'
    return ''
  }
})
</script>

<style scoped>
.article-equation { position: relative; display: flex; align-items: center; justify-content: center; min-height: 58px; padding: 12px 52px; color: #17232c; }
.equation-render { max-width: 100%; overflow-x: auto; }
.equation-number { position: absolute; right: 8px; color: #65727b; font-size: 13px; }
.equation-error { color: #a33d34; font-size: 13px; }
.invalid { border: 1px solid #e6b9b3; background: #fff7f6; }
</style>
