<template>
  <div class="message-editor-container">
    <div class="message-editor-wrapper">
      <div :id="editorId" ref="vditorElement"></div>
    </div>
    <div class="message-bottom-container">
      <div class="message-submit" :class="{ disabled: isDisabled }" @click="submit">
        <template v-if="!loading">
          Send
          <span class="shortcut-icon" v-if="!isMobile"> {{ isMac ? '⌘' : 'Ctrl' }} ⏎ </span>
        </template>
        <template v-else> <loading-four class="loading-icon" /> Sending... </template>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, onMounted, onUnmounted, ref, useId, watch } from 'vue'
import { clearVditorStorage } from '~/utils/clearVditorStorage'
import { themeState } from '~/utils/theme'
import {
  createVditor,
  getEditorTheme as getEditorThemeUtil,
  getPreviewTheme as getPreviewThemeUtil,
} from '~/utils/vditor'
import { useIsMobile } from '~/utils/screen'
import { isMac } from '~/utils/device'
import '~/assets/global.css'

export default {
  name: 'MessageEditor',
  emits: ['submit'],
  props: {
    editorId: {
      type: String,
      default: '',
    },
    loading: {
      type: Boolean,
      default: false,
    },
    disabled: {
      type: Boolean,
      default: false,
    },
  },
  setup(props, { emit }) {
    const vditorInstance = ref(null)
    const text = ref('')
    const editorId = ref(props.editorId)
    const isMobile = useIsMobile()
    if (!editorId.value) {
      editorId.value = 'editor-' + useId()
    }
    const getEditorTheme = getEditorThemeUtil
    const getPreviewTheme = getPreviewThemeUtil
    const applyTheme = () => {
      if (vditorInstance.value) {
        vditorInstance.value.setTheme(getEditorTheme(), getPreviewTheme())
      }
    }

    const isDisabled = computed(() => props.loading || props.disabled || !text.value.trim())

    const submit = () => {
      if (!vditorInstance.value || isDisabled.value) return
      const value = vditorInstance.value.getValue()
      emit('submit', value, () => {
        if (!vditorInstance.value) return
        vditorInstance.value.setValue('')
        text.value = ''
      })
    }

    onMounted(() => {
      vditorInstance.value = createVditor(editorId.value, {
        placeholder: 'Write a message...',
        preview: {
          actions: [],
          markdown: { toc: false },
        },
        input(value) {
          text.value = value
        },
        after() {
          if (props.loading || props.disabled) {
            vditorInstance.value.disabled()
          }
          applyTheme()
        },
      })

      // 不是手机的情况下不添加快捷键
      if (!isMobile.value) {
        // 添加快捷键监听 (Ctrl+Enter 或 Cmd+Enter)
        const handleKeydown = (e) => {
          if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault()
            submit()
          }
        }

        const el = document.getElementById(editorId.value)
        if (el) {
          el.addEventListener('keydown', handleKeydown)
        }

        onUnmounted(() => {
          if (el) {
            el.removeEventListener('keydown', handleKeydown)
          }
        })
      }
    })

    onUnmounted(() => {
      clearVditorStorage()
    })

    watch(
      () => props.loading,
      (val) => {
        if (!vditorInstance.value) return
        if (val) {
          vditorInstance.value.disabled()
        } else if (!props.disabled) {
          vditorInstance.value.enable()
        }
      },
    )

    watch(
      () => props.disabled,
      (val) => {
        if (!vditorInstance.value) return
        if (val) {
          vditorInstance.value.disabled()
        } else if (!props.loading) {
          vditorInstance.value.enable()
        }
      },
    )

    watch(
      () => themeState.mode,
      () => {
        applyTheme()
      },
    )

    return { submit, isDisabled, editorId, isMac, isMobile }
  },
}
</script>

<style scoped>
.message-editor-container {
  border: 1px solid var(--border-color);
  border-radius: 8px;
}
.message-bottom-container {
  display: flex;
  flex-direction: row;
  justify-content: flex-end;
  margin-top: 10px;
  margin-bottom: 10px;
  background-color: var(--bg-color-soft);
  border-top: 1px solid var(--border-color);
  border-bottom-left-radius: 8px;
  border-bottom-right-radius: 8px;
}

.message-submit {
  background-color: var(--primary-color);
  color: #fff;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.message-submit.disabled {
  background-color: var(--primary-color-disabled);
  opacity: 0.6;
  cursor: not-allowed;
}

.message-submit:not(.disabled):hover {
  background-color: var(--primary-color-hover);
}

/** 评论按钮快捷键样式 */
.shortcut-icon {
  padding: 2px 6px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.2;
  background-color: rgba(0, 0, 0, 0.25);
}
.comment-submit.disabled .shortcut-icon {
  background-color: rgba(0, 0, 0, 0);
}
</style>
