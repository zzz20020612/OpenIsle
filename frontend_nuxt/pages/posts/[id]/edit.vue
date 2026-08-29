<template>
  <div class="new-post-page">
    <div class="new-post-form">
      <div class="edit-eyebrow">DISCUSSION EDITOR</div>
      <input class="post-title-input" v-model="title" placeholder="Discussion title" />
      <div class="post-editor-container">
        <PostEditor v-model="content" :loading="isAiLoading" :disabled="!isLogin" />
        <LoginOverlay v-if="!isLogin" />
      </div>
      <div class="post-options">
        <div class="post-options-left">
          <CategorySelect v-model="selectedCategory" />
          <TagSelect v-model="selectedTags" creatable />
          <PostVisibleScopeSelect v-model="selectedVisibleScope"/>
        </div>
        <div class="post-options-right">
          <div class="post-clear" @click="clearPost"><clear-icon /> Clear</div>
          <div class="ai-generate" @click="aiGenerate">
            <smart-optimization />
            Improve Markdown
          </div>
          <div class="post-cancel" @click="cancelEdit">Cancel</div>
          <div
            v-if="!isWaitingPosting"
            class="post-submit"
            :class="{ disabled: !isLogin }"
            @click="submitPost"
          >
            Update discussion
          </div>
          <div v-else class="post-submit-loading">
            <loading-four class="loading-icon" /> Updating…
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import PostEditor from '~/components/PostEditor.vue'
import CategorySelect from '~/components/CategorySelect.vue'
import TagSelect from '~/components/TagSelect.vue'
import { toast } from '~/main'
import { getToken, authState } from '~/utils/auth'
import LoginOverlay from '~/components/LoginOverlay.vue'
import PostVisibleScopeSelect from '~/components/PostVisibleScopeSelect.vue'
const config = useRuntimeConfig()
const API_BASE_URL = config.public.apiBaseUrl

const title = ref('')
const content = ref('')
const selectedCategory = ref('')
const selectedTags = ref([])
const selectedVisibleScope = ref('ALL')
const isWaitingPosting = ref(false)
const isAiLoading = ref(false)
const isLogin = computed(() => authState.loggedIn)

const route = useRoute()
const postId = route.params.id

const loadPost = async () => {
  try {
    const token = getToken()
    const res = await fetch(`${API_BASE_URL}/api/posts/${postId}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (res.ok) {
      const data = await res.json()
      title.value = data.title || ''
      content.value = data.content || ''
      selectedCategory.value = data.category.id || ''
      selectedTags.value = (data.tags || []).map((t) => t.id)
      selectedVisibleScope.value = data.visibleScope
    }
  } catch (e) {
    toast.error('The discussion could not be loaded.')
  }
}

onMounted(loadPost)

const clearPost = () => {
  title.value = ''
  content.value = ''
  selectedCategory.value = ''
  selectedTags.value = []
}

const ensureTags = async (token) => {
  for (let i = 0; i < selectedTags.value.length; i++) {
    const t = selectedTags.value[i]
    if (typeof t === 'string' && t.startsWith('__new__:')) {
      const name = t.slice(8)
      const res = await fetch(`${API_BASE_URL}/api/tags`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name, description: '' }),
      })
      if (res.ok) {
        const data = await res.json()
        selectedTags.value[i] = data.id
        // update local TagSelect options handled by component
      } else {
        let data
        try {
          data = await res.json()
        } catch (e) {
          data = null
        }
        toast.error((data && data.error) || 'The new tag could not be created.')
        throw new Error('create tag failed')
      }
    }
  }
}

const aiGenerate = async () => {
  if (!content.value.trim()) {
    toast.error('Add content before using Markdown formatting.')
    return
  }
  isAiLoading.value = true
  try {
    toast.info('Improving Markdown formatting…')
    const token = getToken()
    const res = await fetch(`${API_BASE_URL}/api/ai/format`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ text: content.value }),
    })
    if (res.ok) {
      const data = await res.json()
      content.value = data.content || ''
    } else if (res.status === 429) {
      toast.error('Your daily AI formatting allowance has been used.')
    } else {
      toast.error('AI formatting could not be completed.')
    }
  } catch (e) {
    toast.error('AI formatting could not be completed.')
  } finally {
    isAiLoading.value = false
  }
}

const submitPost = async () => {
  if (!title.value.trim()) {
    toast.error('Discussion title is required.')
    return
  }
  if (!content.value.trim()) {
    toast.error('Discussion content is required.')
    return
  }
  if (!selectedCategory.value) {
    toast.error('Select a category.')
    return
  }
  if (selectedTags.value.length === 0) {
    toast.error('Select at least one tag.')
    return
  }
  try {
    const token = getToken()
    await ensureTags(token)
    isWaitingPosting.value = true
    const res = await fetch(`${API_BASE_URL}/api/posts/${postId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        title: title.value,
        content: content.value,
        categoryId: selectedCategory.value,
        tagIds: selectedTags.value,
        postVisibleScopeType:selectedVisibleScope.value
      }),
    })
    const data = await res.json()
    if (res.ok) {
      toast.success('Discussion updated.')
      window.location.href = `/posts/${postId}`
    } else {
      toast.error(data.error || 'The discussion could not be updated.')
    }
  } catch (e) {
    toast.error('The discussion could not be updated.')
  } finally {
    isWaitingPosting.value = false
  }
}
const cancelEdit = () => {
  navigateTo(`/posts/${postId}`, { replace: true })
}
</script>

<style scoped>
.new-post-page {
  display: flex;
  justify-content: center;
  min-height: 650px;
  padding: 46px 20px 72px;
  overflow-y: auto;
}

.new-post-form {
  width: min(980px, 100%);
}
.edit-eyebrow { color: #176582; font-size: 11px; font-weight: 800; letter-spacing: .1em; }

.post-title-input {
  border: none;
  outline: none;
  box-sizing: border-box;
  padding: 10px 0 18px;
  border-bottom: 1px solid #bfcbd0;
  background-color: transparent;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 40px;
  width: 100%;
  font-weight: 400;
  color: #2b414b;
}

.post-cancel {
  color: #0065a8;
  cursor: pointer;
}

.post-cancel:hover {
  text-decoration: underline;
}

.ai-generate {
  color: var(--primary-color);
  cursor: pointer;
}

.ai-generate:hover {
  text-decoration: underline;
}

.post-clear {
  color: var(--primary-color);
  cursor: pointer;
  opacity: 0.7;
}

.post-editor-container {
  position: relative;
  margin-top: 22px;
  border: 1px solid #c3cfd3;
  border-top: 4px solid #009edb;
}

.post-submit {
  background: #0065a8;
  color: #fff;
  padding: 10px 20px;
  border-radius: 0;
  width: fit-content;
  cursor: pointer;
}

.post-submit.disabled {
  background-color: var(--primary-color-disabled);
  cursor: not-allowed;
}

.post-submit:hover {
  background-color: var(--primary-color-hover);
}
.post-submit.disabled:hover {
  background-color: var(--primary-color-disabled);
}

.post-submit-loading {
  color: white;
  background-color: var(--primary-color-disabled);
  padding: 10px 20px;
  border-radius: 0;
  width: fit-content;
  cursor: not-allowed;
}

.post-options-left {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.post-options-right {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 30px;
  row-gap: 10px;
  flex-wrap: wrap;
}

.post-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  margin-top: 20px;
  padding-bottom: 50px;
}

@media (max-width: 768px) {
  .new-post-page {
    width: calc(100vw - 20px);
    padding-right: 10px;
    padding-left: 10px;
    overflow-x: hidden;
  }

  .post-title-input {
    font-size: 24px;
    padding-top: 10px;
    padding-bottom: 10px;
  }

  .post-options {
    margin-top: 10px;
  }
}
</style>
