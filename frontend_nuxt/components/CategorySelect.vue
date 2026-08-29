<template>
  <Dropdown
    v-model="selected"
    :fetch-options="fetchCategories"
    placeholder="Select a category"
    :initial-options="providedOptions"
  >
    <template #option="{ option }">
      <div class="option-container">
        <div class="option-main">
          <template v-if="option.icon">
            <BaseImage
              v-if="isImageIcon(option.icon)"
              :src="option.icon"
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
  </Dropdown>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import Dropdown from '~/components/Dropdown.vue'
const config = useRuntimeConfig()
const API_BASE_URL = config.public.apiBaseUrl

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue'])

const providedOptions = ref(Array.isArray(props.options) ? [...props.options] : [])
watch(
  () => props.options,
  (val) => {
    providedOptions.value = Array.isArray(val) ? [...val] : []
  },
)

const fetchCategories = async () => {
  const res = await fetch(`${API_BASE_URL}/api/categories`)
  if (!res.ok) return []
  const data = await res.json()
  return [{ id: '', name: 'No category' }, ...data]
}

const isImageIcon = (icon) => {
  if (!icon) return false
  return /^https?:\/\//.test(icon) || icon.startsWith('/')
}

const selected = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
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
</style>
