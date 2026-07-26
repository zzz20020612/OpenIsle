<template>
  <aside class="article-outline" aria-label="Article outline">
    <div class="outline-header">
      <div><strong>Article outline</strong><span>{{ sections.length }} sections</span></div>
      <button type="button" class="outline-icon" title="Add section" aria-label="Add section" @click="$emit('add')"><AddOne :size="17" /></button>
    </div>
    <nav>
      <button
        v-for="section in sections"
        :key="section.key"
        type="button"
        class="outline-item"
        :class="{ active: section.key === selectedKey }"
        :style="{ paddingLeft: `${12 + Math.max(section.level - 1, 0) * 14}px` }"
        @click="$emit('select', section.key)"
      >
        <span>{{ section.heading || 'Untitled section' }}</span>
        <small>{{ section.blocks?.length || 0 }}</small>
      </button>
    </nav>
  </aside>
</template>

<script setup>
import { AddOne } from '@icon-park/vue-next'
defineProps({ sections: { type: Array, default: () => [] }, selectedKey: { type: String, default: '' } })
defineEmits(['select', 'add'])
</script>

<style scoped>
.article-outline { min-width: 0; border-right: 1px solid #d5dde1; background: #f4f6f6; }
.outline-header { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 16px 12px; border-bottom: 1px solid #d5dde1; }
.outline-header > div { display: grid; gap: 3px; }
.outline-header span { color: #68747c; font-size: 12px; }
.outline-icon { width: 34px; height: 34px; display: grid; place-items: center; border: 1px solid #bcc8ce; background: #fff; color: #1f5b78; cursor: pointer; }
.outline-item { width: 100%; display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 42px; padding-top: 8px; padding-bottom: 8px; border: 0; border-bottom: 1px solid #e2e7e9; background: transparent; color: #33444e; text-align: left; cursor: pointer; }
.outline-item small { color: #7b878e; font-size: 11px; }
.outline-item.active { border-left: 3px solid #1f617f; background: #e4eef1; color: #153f52; font-weight: 750; }
</style>
