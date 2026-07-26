<template>
  <section v-if="section" class="block-editor">
    <header class="section-editor-header">
      <div>
        <label>Section heading</label>
        <input v-model.trim="section.heading" @input="$emit('change')" />
      </div>
      <button type="button" class="danger-button" @click="$emit('remove-section', section.key)">Remove section</button>
    </header>

    <article v-for="(block, index) in section.blocks" :key="block.key" class="block-row">
      <div class="block-row-toolbar">
        <span>{{ blockLabel(block.type) }}</span>
        <div>
          <button type="button" title="Move block up" aria-label="Move block up" :disabled="index === 0" @click="$emit('move', index, -1)"><ArrowUp :size="15" /></button>
          <button type="button" title="Move block down" aria-label="Move block down" :disabled="index === section.blocks.length - 1" @click="$emit('move', index, 1)"><ArrowDown :size="15" /></button>
          <button type="button" title="Remove block" aria-label="Remove block" @click="$emit('remove', index)"><Delete :size="15" /></button>
        </div>
      </div>

      <textarea v-if="block.type === 'PARAGRAPH'" v-model="block.text" rows="6" placeholder="Write a paragraph..." @input="$emit('change')" />
      <input v-else-if="block.type === 'SUBHEADING'" v-model="block.text" placeholder="Subheading" @input="$emit('change')" />
      <div v-else-if="block.type === 'EQUATION'" class="block-fields">
        <label>LaTeX equation<textarea v-model="block.latex" rows="3" placeholder="x_i = ..." @input="$emit('change')" /></label>
        <label class="checkbox-line"><input v-model="block.numbered" type="checkbox" @change="$emit('change')" /> Number this equation</label>
      </div>
      <div v-else-if="block.type === 'FIGURE'" class="block-fields">
        <label>Figure file<select v-model="block.fileId" @change="$emit('change')"><option :value="null">Select an uploaded figure</option><option v-for="file in figureFiles" :key="file.id" :value="file.id">{{ file.displayName }}</option></select></label>
        <label>Caption<input v-model="block.caption" placeholder="Figure caption" @input="$emit('change')" /></label>
        <label>Alternative text<input v-model="block.altText" placeholder="Describe the figure" @input="$emit('change')" /></label>
      </div>
      <div v-else-if="block.type === 'TABLE'" class="block-fields">
        <label>Caption<input v-model="block.caption" placeholder="Table caption" @input="$emit('change')" /></label>
        <label>Columns, separated by commas<input :value="(block.columns || []).join(', ')" placeholder="Variable, Value" @input="setColumns(block, $event.target.value)" /></label>
        <label>Rows, one row per line; cells separated by tabs<textarea :value="rowsText(block)" rows="4" @input="setRows(block, $event.target.value)" /></label>
      </div>
    </article>

    <div class="add-block-row">
      <button v-for="type in blockTypes" :key="type.value" type="button" @click="$emit('add', type.value)"><AddOne :size="15" /> {{ type.label }}</button>
    </div>
  </section>
  <div v-else class="empty-editor">Select a section from the outline.</div>
</template>

<script setup>
import { AddOne, ArrowDown, ArrowUp, Delete } from '@icon-park/vue-next'
import { ARTICLE_BLOCK_TYPES } from '~/config/paperArticleConfig'

const props = defineProps({ section: { type: Object, default: null }, figureFiles: { type: Array, default: () => [] } })
defineEmits(['change', 'add', 'remove', 'move', 'remove-section'])
const blockTypes = ARTICLE_BLOCK_TYPES
const blockLabel = (type) => blockTypes.find((item) => item.value === type)?.label || type
const setColumns = (block, value) => { block.columns = value.split(',').map((item) => item.trim()).filter(Boolean) }
const rowsText = (block) => (block.rows || []).map((row) => row.join('\t')).join('\n')
const setRows = (block, value) => { block.rows = value.split('\n').filter(Boolean).map((row) => row.split('\t').map((cell) => cell.trim())) }
</script>

<style scoped>
.block-editor { display: grid; gap: 16px; }
.section-editor-header { display: flex; align-items: end; justify-content: space-between; gap: 16px; padding-bottom: 14px; border-bottom: 1px solid #d7dfe2; }
.section-editor-header > div { display: grid; gap: 7px; min-width: 0; flex: 1; }
label { display: grid; gap: 6px; color: #35454f; font-size: 12px; font-weight: 750; }
input, textarea, select { width: 100%; border: 1px solid #bcc8ce; background: #fff; color: #17232c; padding: 10px 11px; font: inherit; font-size: 14px; line-height: 1.5; }
textarea { resize: vertical; min-height: 100px; }
.danger-button { min-height: 36px; border: 1px solid #d2aaa5; background: #fff; color: #9d3c32; padding: 7px 10px; font-weight: 700; cursor: pointer; }
.block-row { display: grid; gap: 10px; padding: 14px; border: 1px solid #d4dde1; background: #fff; }
.block-row-toolbar { display: flex; align-items: center; justify-content: space-between; color: #50616a; font-size: 12px; font-weight: 800; }
.block-row-toolbar > div { display: flex; gap: 5px; }
.block-row-toolbar button { width: 30px; height: 30px; display: grid; place-items: center; border: 1px solid #c8d2d7; background: #fff; color: #42545e; cursor: pointer; }
.block-row-toolbar button:disabled { opacity: .35; cursor: not-allowed; }
.block-fields { display: grid; gap: 12px; }
.checkbox-line { display: flex; align-items: center; gap: 7px; }
.checkbox-line input { width: auto; }
.add-block-row { display: flex; flex-wrap: wrap; gap: 8px; }
.add-block-row button { min-height: 36px; display: inline-flex; align-items: center; gap: 6px; border: 1px solid #aec0c8; background: #f5f8f9; color: #1f526b; padding: 7px 10px; font-weight: 700; cursor: pointer; }
.empty-editor { display: grid; place-items: center; min-height: 360px; color: #68747c; }
@media (max-width: 650px) { .section-editor-header { align-items: stretch; flex-direction: column; } }
</style>
