<template>
  <div v-if="isVisible" :id="`change-log-${log.id}`" class="change-log-container">
    <div class="change-log-text">
      <BaseUserAvatar
        v-if="log.userAvatar"
        class="change-log-avatar"
        :src="log.userAvatar"
        :to="log.username ? `/users/${log.username}` : ''"
        alt="avatar"
        :disable-link="!log.username"
      />
      <span v-if="log.username" class="change-log-user">{{ log.username }}</span>
      <span v-if="log.type === 'CONTENT'" class="change-log-content">updated the discussion content</span>
      <span v-else-if="log.type === 'TITLE'" class="change-log-content">updated the discussion title</span>
      <template v-else-if="log.type === 'CATEGORY'">
        <div class="change-log-category-text">changed the category from</div>
        <ArticleCategory :category="log.oldCategory" />
        <div class="change-log-category-text">to</div>
        <ArticleCategory :category="log.newCategory" />
      </template>
      <template v-else-if="log.type === 'TAG'">
        <div class="change-log-category-text">changed the tags from</div>
        <ArticleTags :tags="log.oldTags" />
        <div class="change-log-category-text">to</div>
        <ArticleTags :tags="log.newTags" />
      </template>
      <span v-else-if="log.type === 'CLOSED'" class="change-log-content">
        <template v-if="log.newClosed">closed the discussion</template>
        <template v-else>reopened the discussion</template>
      </span>
      <span v-else-if="log.type === 'PINNED'" class="change-log-content">
        <template v-if="log.newPinnedAt">pinned the discussion</template>
        <template v-else>unpinned the discussion</template>
      </span>
      <span v-else-if="log.type === 'FEATURED'" class="change-log-content">
        <template v-if="log.newFeatured">featured the discussion</template>
        <template v-else>removed the discussion from featured records</template>
      </span>
      <span v-else-if="log.type === 'VISIBLE_SCOPE'" class="change-log-content">
        changed visibility from {{ formatVisibleScope(log.oldVisibleScope) }} to
        {{ formatVisibleScope(log.newVisibleScope) }}
      </span>
    </div>
    <div class="change-log-time">{{ log.time }}</div>
    <div
      v-if="log.type === 'CONTENT' || log.type === 'TITLE'"
      class="content-diff"
      v-html="diffHtml"
    ></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { html } from 'diff2html'
import { createTwoFilesPatch } from 'diff'
import 'diff2html/bundles/css/diff2html.min.css'
import BaseUserAvatar from '~/components/BaseUserAvatar.vue'
import { themeState } from '~/utils/theme'
import ArticleCategory from '~/components/ArticleCategory.vue'
import ArticleTags from '~/components/ArticleTags.vue'
const props = defineProps({
  log: Object,
  title: String,
})

const VISIBLE_SCOPE_LABELS = {
  ALL: 'public',
  ONLY_ME: 'private',
  ONLY_REGISTER: 'registered users',
}

const isVisible = computed(() => !['VOTE_RESULT', 'LOTTERY_RESULT', 'DONATE'].includes(props.log.type))

const formatVisibleScope = (scope) => {
  if (!scope) return VISIBLE_SCOPE_LABELS.ALL
  return VISIBLE_SCOPE_LABELS[scope] ?? scope
}

const diffHtml = computed(() => {
  // Track theme changes
  const isDark = import.meta.client && document.documentElement.dataset.theme === 'dark'
  themeState.mode
  const colorScheme = isDark ? 'dark' : 'light'

  if (props.log.type === 'CONTENT') {
    const oldContent = props.log.oldContent ?? ''
    const newContent = props.log.newContent ?? ''
    const diff = createTwoFilesPatch(props.title, props.title, oldContent, newContent)
    return html(diff, {
      inputFormat: 'diff',
      showFiles: false,
      matching: 'lines',
      drawFileList: false,
      colorScheme,
    })
  } else if (props.log.type === 'TITLE') {
    const oldTitle = props.log.oldTitle ?? ''
    const newTitle = props.log.newTitle ?? ''
    const diff = createTwoFilesPatch(oldTitle, newTitle, '', '')
    return html(diff, {
      inputFormat: 'diff',
      showFiles: false,
      matching: 'lines',
      drawFileList: false,
      colorScheme,
    })
  }
  return ''
})
</script>

<style scoped>
.change-log-container {
  display: flex;
  flex-direction: column;
  /* padding-top: 5px; */
  /* padding-bottom: 30px; */
  font-size: 14px;
  border-bottom: 1px solid var(--normal-border-color);
  padding-bottom: 10px;
}

.change-log-text {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.change-log-user {
  font-weight: bold;
  margin-right: 4px;
}

.change-log-user,
.change-log-content {
  opacity: 0.7;
}

.change-log-avatar {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  margin-right: 4px;
  cursor: pointer;
}

.change-log-avatar :deep(.base-user-avatar-img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.change-log-time {
  font-size: 12px;
  opacity: 0.6;
}

.content-diff {
  margin-top: 8px;
}

.change-log-category {
  display: flex;
  flex-direction: row;
  gap: 4px;
  align-items: center;
  flex-wrap: wrap;
}
</style>
