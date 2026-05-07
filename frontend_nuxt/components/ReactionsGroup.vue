<template>
  <div class="reactions-container">
    <div class="reactions-viewer">
      <div
        class="reactions-viewer-item-container"
        @mouseenter="cancelHide"
        @mouseleave="scheduleHide"
      >
        <template v-if="Object.keys(counts).length < 4">
          <div
            v-for="r in displayedReactions"
            :key="r.type"
            class="reactions-viewer-single-item"
            :class="{ selected: userReacted(r.type) }"
            @click="toggleReaction(r.type)"
          >
            <BaseImage :src="reactionEmojiMap[r.type]" class="reaction-emoji" alt="emoji" />
            <div>{{ counts[r.type] }}</div>
          </div>

          <ToolTip content="React" placement="bottom">
            <div class="reactions-viewer-item placeholder" @click="openPanel">
              <sly-face-whit-smile class="reactions-viewer-item-placeholder-icon" />
            </div>
          </ToolTip>
        </template>
        <template v-else-if="displayedReactions.length">
          <div
            v-for="r in displayedReactions"
            :key="r.type"
            class="reactions-viewer-item"
            @click="openPanel"
          >
            <BaseImage :src="reactionEmojiMap[r.type]" class="emoji" alt="emoji" />
          </div>
          <div class="reactions-count">{{ totalCount }}</div>
        </template>
      </div>
    </div>
    <div
      v-if="panelVisible"
      class="reactions-panel"
      ref="reactionsPanelRef"
      :style="panelInlineStyle"
      @mouseenter="cancelHide"
      @mouseleave="scheduleHide"
    >
      <div
        v-for="t in panelTypes"
        :key="t"
        class="reaction-option"
        @click="toggleReaction(t)"
        :class="{ selected: userReacted(t) }"
      >
        <BaseImage :src="reactionEmojiMap[t]" class="emoji" alt="emoji" /><span v-if="counts[t]">{{
          counts[t]
        }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { toast } from '~/main'
import { authState, getToken } from '~/utils/auth'
import { reactionEmojiMap } from '~/utils/reactions'
import { useReactionTypes } from '~/composables/useReactionTypes'

const { reactionTypes, initialize } = useReactionTypes()

const config = useRuntimeConfig()
const API_BASE_URL = config.public.apiBaseUrl
const emit = defineEmits(['update:modelValue'])
const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  contentType: { type: String, required: true },
  contentId: { type: [Number, String], required: true },
})

watch(
  () => props.modelValue,
  (v) => (reactions.value = v),
)

const reactions = ref(props.modelValue)

const counts = computed(() => {
  const c = {}
  for (const r of reactions.value) {
    c[r.type] = (c[r.type] || 0) + 1
  }
  return c
})

const totalCount = computed(() => Object.values(counts.value).reduce((a, b) => a + b, 0))
const userReacted = (type) =>
  reactions.value.some((r) => r.type === type && r.user === authState.username)

const baseReactionOrder = computed(() => {
  if (reactionTypes.value.length) return [...reactionTypes.value]

  const order = []
  const seen = new Set()
  for (const reaction of reactions.value) {
    if (!seen.has(reaction.type)) {
      seen.add(reaction.type)
      order.push(reaction.type)
    }
  }
  return order
})

const sortedReactionTypes = computed(() => {
  const baseOrder = [...baseReactionOrder.value]
  for (const type of Object.keys(counts.value)) {
    if (!baseOrder.includes(type)) baseOrder.push(type)
  }

  const withMetadata = baseOrder.map((type, index) => ({
    type,
    count: counts.value[type] || 0,
    index,
  }))

  const nonZero = withMetadata
    .filter((item) => item.count > 0)
    .sort((a, b) => {
      if (b.count !== a.count) return b.count - a.count
      return a.index - b.index
    })

  const zero = withMetadata.filter((item) => item.count === 0)

  return [...nonZero, ...zero].map((item) => item.type)
})

const displayedReactions = computed(() => {
  return sortedReactionTypes.value
    .filter((type) => counts.value[type] > 0)
    .slice(0, 3)
    .map((type) => ({ type }))
})

const panelTypes = computed(() => sortedReactionTypes.value)

const panelVisible = ref(false)
const reactionsPanelRef = ref(null)
const panelInlineStyle = ref({})
let hideTimer = null
const openPanel = () => {
  clearTimeout(hideTimer)
  panelVisible.value = true
}
const scheduleHide = () => {
  clearTimeout(hideTimer)
  hideTimer = setTimeout(() => {
    panelVisible.value = false
  }, 500)
}
const cancelHide = () => {
  clearTimeout(hideTimer)
}

const updatePanelInlineStyle = () => {
  if (!panelVisible.value) return
  const panelEl = reactionsPanelRef.value
  if (!panelEl) return
  const parentEl = panelEl.closest('.reactions-container')?.parentElement?.parentElement
  if (!parentEl) return
  const parentWidth = parentEl.clientWidth - 20
  panelInlineStyle.value = {
    width: 'max-content',
    maxWidth: `${parentWidth}px`,
  }
}

watch(panelVisible, async (visible) => {
  if (visible) {
    await nextTick()
    updatePanelInlineStyle()
  }
})

watch(panelTypes, async () => {
  if (panelVisible.value) {
    await nextTick()
    updatePanelInlineStyle()
  }
})

const toggleReaction = async (type) => {
  const token = getToken()
  if (!token) {
    toast.error('Please log in first.')
    return
  }
  const url =
    props.contentType === 'post'
      ? `${API_BASE_URL}/api/posts/${props.contentId}/reactions`
      : props.contentType === 'comment'
        ? `${API_BASE_URL}/api/comments/${props.contentId}/reactions`
        : `${API_BASE_URL}/api/messages/${props.contentId}/reactions`

  // optimistic update
  const existingIdx = reactions.value.findIndex(
    (r) => r.type === type && r.user === authState.username,
  )
  let tempReaction = null
  let removedReaction = null
  if (existingIdx > -1) {
    removedReaction = reactions.value.splice(existingIdx, 1)[0]
  } else {
    tempReaction = { type, user: authState.username }
    reactions.value.push(tempReaction)
  }
  emit('update:modelValue', reactions.value)

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ type }),
    })
    if (res.ok) {
      if (res.status === 204) {
        // removal already reflected
      } else {
        const data = await res.json()
        const idx = tempReaction ? reactions.value.indexOf(tempReaction) : -1
        if (idx > -1) {
          reactions.value.splice(idx, 1, data)
        } else if (removedReaction) {
          // server added back reaction even though we removed? restore data
          reactions.value.push(data)
        }
        if (data.reward && data.reward > 0) {
          toast.success(`Earned ${data.reward} XP.`)
        }
      }
      emit('update:modelValue', reactions.value)
    } else {
      // revert optimistic update on failure
      if (tempReaction) {
        const idx = reactions.value.indexOf(tempReaction)
        if (idx > -1) reactions.value.splice(idx, 1)
      } else if (removedReaction) {
        reactions.value.push(removedReaction)
      }
      emit('update:modelValue', reactions.value)
      toast.error('Action failed.')
    }
  } catch (e) {
    if (tempReaction) {
      const idx = reactions.value.indexOf(tempReaction)
      if (idx > -1) reactions.value.splice(idx, 1)
    } else if (removedReaction) {
      reactions.value.push(removedReaction)
    }
    emit('update:modelValue', reactions.value)
    toast.error('Action failed.')
  }
}

onMounted(async () => {
  await initialize()
  window.addEventListener('resize', updatePanelInlineStyle)
})

defineExpose({
  toggleReaction,
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updatePanelInlineStyle)
})
</script>

<style>
.reactions-container {
  position: relative;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.reactions-viewer {
  display: flex;
  flex-direction: row;
  gap: 20px;
  align-items: center;
}

.reaction-emoji {
  width: 20px;
  height: 20px;
  vertical-align: middle;
}

.reactions-viewer-item-container {
  display: flex;
  flex-direction: row;
  gap: 2px;
  align-items: center;
  cursor: pointer;
  color: #a2a2a2;
}

.reactions-viewer-item {
  font-size: 16px;
}

.reactions-viewer-item-placeholder-icon {
  opacity: 0.5;
}

.reactions-viewer-item-placeholder-text {
  font-size: 14px;
  padding-left: 5px;
}

.reactions-count {
  font-size: 16px;
  font-weight: bold;
  margin-right: 15px;
}

.reactions-panel {
  position: absolute;
  bottom: 35px;
  background-color: var(--background-color);
  border: 1px solid var(--normal-border-color);
  border-radius: 20px;
  padding: 5px 10px;
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  z-index: 10;
  gap: 5px;
  box-shadow: 0 0 10px 0 rgba(0, 0, 0, 0.1);
}

.reaction-option {
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 2px;
}

.reactions-viewer-item.placeholder,
.reactions-viewer-single-item {
  display: flex;
  cursor: pointer;
  flex-direction: row;
  padding: 2px 10px;
  gap: 5px;
  border: 1px solid var(--normal-border-color);
  border-radius: 10px;
  margin-right: 5px;
  font-size: 14px;
  color: var(--text-color);
  align-items: center;
}

.reactions-viewer-item.placeholder,
.reactions-viewer-single-item.selected {
  background-color: var(--normal-light-background-color);
}

.reaction-option.selected {
  background-color: var(--normal-light-background-color);
}

@media (max-width: 768px) {
  .make-reaction-item {
    font-size: 16px;
    padding: 3px 5px;
  }

  .reactions-viewer-item.placeholder,
  .reactions-viewer-single-item {
    padding: 4px 8px;
    gap: 3px;
    border: 1px solid var(--normal-border-color);
    border-radius: 10px;
    margin-right: 3px;
    margin-bottom: 3px;
    font-size: 12px;
    color: var(--text-color);
    align-items: center;
  }

  .reaction-emoji {
    width: 14px;
    height: 14px;
  }
}
</style>
