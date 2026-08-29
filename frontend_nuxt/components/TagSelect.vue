<template>
  <Dropdown
    ref="dropdownRef"
    v-model="selected"
    :fetch-options="fetchTags"
    multiple
    placeholder="Select tags"
    remote
    :initial-options="mergedOptions"
  >
    <template #option="{ option }">
      <div class="option-container">
        <div class="option-main">
          <template v-if="option.smallIcon || option.icon">
            <BaseImage
              v-if="isImageIcon(option.smallIcon || option.icon)"
              :src="option.smallIcon || option.icon"
              class="option-icon"
              :alt="option.name"
            />
            <component v-else :is="option.smallIcon || option.icon" class="option-icon" />
          </template>
          <span>{{ option.name }}</span>
          <span class="option-count" v-if="option.count > 0"> x {{ option.count }}</span>
        </div>
        <div v-if="option.description" class="option-desc">{{ option.description }}</div>
      </div>
    </template>
    <template #footer>
      <div v-if="hasMoreRemoteTags" class="dropdown-footer">
        <a
          href="#"
          class="dropdown-more"
          :class="{ disabled: loadMoreRequested }"
          @click.prevent="loadMoreRemoteTags"
        >
          {{ loadMoreRequested ? 'Loading…' : 'Load more' }}
        </a>
      </div>
    </template>
  </Dropdown>
</template>

<script setup>
import { computed, reactive, ref, watch, nextTick } from 'vue'
import { toast } from '~/main'
import Dropdown from '~/components/Dropdown.vue'
const config = useRuntimeConfig()
const API_BASE_URL = config.public.apiBaseUrl

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  creatable: { type: Boolean, default: false },
  options: { type: Array, default: () => [] },
})

const dropdownRef = ref(null)
const localTags = ref([])
const providedTags = ref(Array.isArray(props.options) ? [...props.options] : [])

const TAG_PAGE_SIZE = 10
const remoteState = reactive({
  keyword: '',
  nextPage: 0,
  hasMore: true,
  options: [],
})
const loadMoreRequested = ref(false)

watch(
  () => props.options,
  (val) => {
    providedTags.value = Array.isArray(val) ? [...val] : []
  },
)

const mergedOptions = computed(() => {
  const arr = [...providedTags.value, ...localTags.value, ...remoteState.options]
  return arr.filter((v, i, a) => a.findIndex((t) => t.id === v.id) === i)
})

const isImageIcon = (icon) => {
  if (!icon) return false
  return /^https?:\/\//.test(icon) || icon.startsWith('/')
}

const buildTagsUrl = (kw = '', page = 0) => {
  const base = API_BASE_URL || (import.meta.client ? window.location.origin : '')
  const url = new URL('/api/tags', base)

  if (kw) url.searchParams.set('keyword', kw)
  url.searchParams.set('page', String(page))
  url.searchParams.set('pageSize', String(TAG_PAGE_SIZE))

  return url.toString()
}

const fetchRemoteTags = async (kw = '', page = 0) => {
  const url = buildTagsUrl(kw, page)
  try {
    const res = await fetch(url)
    if (res.ok) {
      const data = await res.json()
      return Array.isArray(data) ? data : []
    }
    throw new Error('failed to fetch tags')
  } catch (e) {
    console.error('Failed to fetch tags', e)
    toast.error('Tags could not be loaded.')
    throw e
  }
}

const combineOptions = (remoteOptions = []) => {
  const options = [...providedTags.value, ...localTags.value, ...remoteOptions]
  return Array.from(new Map(options.map((t) => [t.id, t])).values())
}

const fetchTags = async (kw = '') => {
  const defaultOption = { id: 0, name: 'No tags' }

  if (kw !== remoteState.keyword) {
    remoteState.keyword = kw
    remoteState.nextPage = 0
    remoteState.options = []
    remoteState.hasMore = true
  }

  const shouldFetch = remoteState.options.length === 0 || loadMoreRequested.value
  if (shouldFetch) {
    const pageToFetch = loadMoreRequested.value ? remoteState.nextPage : 0
    try {
      const data = await fetchRemoteTags(remoteState.keyword, pageToFetch)
      if (pageToFetch === 0) {
        remoteState.options = data
      } else {
        const existing = Array.isArray(remoteState.options) ? remoteState.options : []
        const merged = [...existing, ...data]
        remoteState.options = Array.from(new Map(merged.map((t) => [t.id, t])).values())
      }
      remoteState.hasMore = data.length === TAG_PAGE_SIZE
      remoteState.nextPage = pageToFetch + 1
    } catch (e) {
      return [defaultOption, ...combineOptions(remoteState.options)]
    } finally {
      loadMoreRequested.value = false
    }
  }

  let options = combineOptions(remoteState.options)

  if (props.creatable && kw && !options.some((t) => t.name.toLowerCase() === kw.toLowerCase())) {
    options.push({ id: `__create__:${kw}`, name: `Create “${kw}”` })
  }

  return [defaultOption, ...options]
}

const hasMoreRemoteTags = computed(() => remoteState.hasMore)

const loadMoreRemoteTags = async () => {
  if (!remoteState.hasMore || loadMoreRequested.value) return
  loadMoreRequested.value = true
  try {
    await dropdownRef.value?.reload()
    await nextTick()
    dropdownRef.value?.scrollToBottom?.()
  } catch (e) {
    console.error('Failed to load more tags', e)
    loadMoreRequested.value = false
  }
}

const selected = computed({
  get: () => props.modelValue,
  set: (v) => {
    if (Array.isArray(v)) {
      if (v.includes(0)) {
        emit('update:modelValue', [])
        return
      }
      if (v.length > 2) {
        toast.error('Select no more than two tags.')
        return
      }
      v = v.map((id) => {
        if (typeof id === 'string' && id.startsWith('__create__:')) {
          const name = id.slice(11)
          const newId = `__new__:${name}`
          if (!localTags.value.find((t) => t.id === newId)) {
            localTags.value.push({ id: newId, name })
          }
          return newId
        }
        return id
      })
    }
    emit('update:modelValue', v)
  },
})
</script>

<style scoped>
.option-container {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.option-main {
  display: flex;
  align-items: center;
  gap: 5px;
}

.option-desc {
  font-size: 12px;
  color: #666;
}

.option-count {
  font-weight: bold;
  opacity: 0.4;
}

.dropdown-footer {
  padding: 8px 20px;
  text-align: center;
  border-top: 1px solid var(--normal-border-color);
}

.dropdown-more {
  color: var(--primary-color);
  text-decoration: none;
  cursor: pointer;
}

.dropdown-more.disabled {
  pointer-events: none;
  opacity: 0.6;
}
</style>
