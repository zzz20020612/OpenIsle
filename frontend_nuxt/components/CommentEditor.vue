<template>
  <div class="comment-editor-container">
    <div class="comment-editor-wrapper">
      <div :id="editorId" ref="vditorElement"></div>
      <LoginOverlay v-if="showLoginOverlay" />
    </div>
    <div class="comment-bottom-container">
      <div class="comment-submit" :class="{ disabled: isDisabled }" @click="submit">
        <template v-if="!loading">
          Publish comment
          <span class="shortcut-icon" v-if="!isMobile">{{ isMac ? 'Cmd' : 'Ctrl' }} + Enter</span>
        </template>
        <template v-else> <loading-four class="loading-icon" /> Publishing... </template>
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
import '~/assets/global.css'
import LoginOverlay from '~/components/LoginOverlay.vue'
import { useIsMobile } from '~/utils/screen'

export default {
  name: 'CommentEditor',
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
    showLoginOverlay: {
      type: Boolean,
      default: false,
    },
    parentUserName: {
      type: String,
      default: '',
    },
  },
  components: { LoginOverlay },
  setup(props, { emit }) {
    const isMobile = useIsMobile()
    const vditorInstance = ref(null)
    const text = ref('')
    const editorId = ref(props.editorId)
    if (!editorId.value) {
      editorId.value = 'editor-' + useId()
    }

    const isMac = ref(false)

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
      console.debug('CommentEditor submit', value)
      emit('submit', props.parentUserName, value, () => {
        if (!vditorInstance.value) return
        vditorInstance.value.setValue('')
        text.value = ''
      })
    }

    onMounted(() => {
      if (navigator.userAgentData) {
        isMac.value = navigator.userAgentData.platform === 'macOS'
      } else {
        isMac.value = /Mac|iPhone|iPad|iPod/.test(navigator.userAgent)
      }

      vditorInstance.value = createVditor(editorId.value, {
        placeholder: 'Write a thoughtful comment...',
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
      // Enable keyboard submission on desktop.
      if (!isMobile.value) {
        // Submit with Ctrl+Enter or Cmd+Enter.
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
.comment-editor-container {
  margin-top: 20px;
  margin-bottom: 50px;
}

.comment-bottom-container {
  display: flex;
  flex-direction: row;
  justify-content: flex-end;
  padding-top: 10px;
}

.comment-submit {
  background-color: var(--primary-color);
  color: #fff;
  padding: 10px 20px;
  border-radius: 10px;
  font-size: 14px;
  cursor: pointer;
}

.comment-submit.disabled {
  background-color: var(--primary-color-disabled);
  opacity: 0.5;
  cursor: not-allowed;
}

.comment-submit.disabled:hover {
  background-color: var(--primary-color-disabled);
}

.comment-submit:hover {
  background-color: var(--primary-color-hover);
}
/** Comment submit shortcut badge. */
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
