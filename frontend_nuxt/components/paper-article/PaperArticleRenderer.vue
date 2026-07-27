<template>
  <div class="article-renderer">
    <section v-for="section in orderedSections" :key="section.key" class="article-section" :class="`level-${section.level}`">
      <component :is="`h${Math.min(section.level + 1, 6)}`" :id="section.key">{{ section.heading }}</component>
      <div v-for="block in section.blocks || []" :key="block.key" class="article-block">
        <p v-if="block.type === 'PARAGRAPH'" class="article-paragraph" v-html="renderInline(block.text)" />
        <h4 v-else-if="block.type === 'SUBHEADING'">{{ block.text }}</h4>
        <PaperEquation v-else-if="block.type === 'EQUATION'" :block="block" :number="equationNumber(block)" />
        <PaperFigure v-else-if="block.type === 'FIGURE'" :block="block" :src="figureSource(block)" :label="figureLabel(block)" />
        <PaperTable v-else-if="block.type === 'TABLE'" :block="block" :label="tableLabel(block)" />
      </div>
    </section>
  </div>
</template>

<script setup>
import katex from 'katex'
import PaperEquation from './PaperEquation.vue'
import PaperFigure from './PaperFigure.vue'
import PaperTable from './PaperTable.vue'
import { renderInlineMath } from '~/utils/paperMath'

const props = defineProps({
  article: { type: Object, default: () => ({ sections: [] }) },
  figureSource: { type: Function, default: () => '' },
})

const orderedSections = computed(() => [...(props.article?.sections || [])].sort((a, b) => (a.displayOrder || 0) - (b.displayOrder || 0)))
const allBlocks = computed(() => orderedSections.value.flatMap((section) => section.blocks || []))
const equationMap = computed(() => new Map(allBlocks.value.filter((block) => block.type === 'EQUATION' && block.numbered).map((block, index) => [block.key, index + 1])))
const figureMap = computed(() => new Map(allBlocks.value.filter((block) => block.type === 'FIGURE').map((block, index) => [block.key, index + 1])))
const tableMap = computed(() => new Map(allBlocks.value.filter((block) => block.type === 'TABLE').map((block, index) => [block.key, index + 1])))

const renderInline = (value = '') =>
  renderInlineMath(value, (latex) =>
    katex.renderToString(latex, { throwOnError: true, trust: false }),
  )

const equationNumber = (block) => equationMap.value.get(block.key) || 0
const figureLabel = (block) => `Figure ${figureMap.value.get(block.key) || ''}`
const tableLabel = (block) => `Table ${tableMap.value.get(block.key) || ''}`
const figureSource = (block) => props.figureSource(block)
</script>

<style scoped>
.article-renderer { color: #23323a; }
.article-section { margin: 0 0 34px; }
.article-section h2, .article-section h3, .article-section h4 { margin: 0 0 16px; color: #17232c; line-height: 1.25; }
.article-section h2 { font-size: 25px; }
.article-section h3 { font-size: 21px; }
.article-section h4 { font-size: 18px; }
.article-paragraph { margin: 0 0 18px; font-size: 16px; line-height: 1.78; }
.article-block :deep(.katex) { font-size: 1.05em; }
@media (max-width: 650px) {
  .article-paragraph { font-size: 15px; line-height: 1.7; }
  .article-section h2 { font-size: 22px; }
  .article-section h3 { font-size: 19px; }
}
</style>
