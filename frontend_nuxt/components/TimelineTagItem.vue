<template>
  <div class="timeline-tag-item">
    <div class="tags-container">
      <div class="tags-container-item">
        <div class="timeline-tag-title">Created a tag</div>
        <ArticleTags v-if="tag" :tags="[tag]" />
        <span class="timeline-tag-count" v-if="tag?.count">x{{ tag.count }}</span>
      </div>
      <div v-if="timelineDate" class="timeline-date">{{ timelineDate }}</div>
    </div>
    <div v-if="hasDescription" class="timeline-snippet">
      {{ tag?.description }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import TimeManager from '~/utils/time'

const props = defineProps({
  item: { type: Object, required: true },
})

const tag = computed(() => props.item?.tag ?? null)
const hasDescription = computed(() => !!tag.value?.description)
const timelineDate = computed(() => {
  const date = props.item?.createdAt ?? tag.value?.createdAt
  return date ? TimeManager.format(date) : ''
})
</script>

<style scoped>
.timeline-tag-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tags-container {
  display: flex;
  flex-direction: row;
  gap: 10px;
  padding-top: 5px;
  justify-content: space-between;
  align-items: center;
}

.tags-container-item {
  display: flex;
  flex-direction: row;
  gap: 5px;
  align-items: center;
}

.timeline-tag-title {
  font-size: 16px;
  font-weight: 600;
}

.timeline-tag-count {
  font-size: 12px;
}

.timeline-date {
  font-size: 12px;
  color: gray;
  margin-top: 5px;
  white-space: nowrap;
}

.timeline-snippet {
  font-size: 14px;
  color: #666;
  margin-top: 5px;
}
</style>
