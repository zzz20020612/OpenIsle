<template>
  <NuxtImg
    v-bind="passAttrs"
    :src="src"
    :alt="alt"
    loading="lazy"
    :placeholder="placeholder"
    placeholder-class="base-image-ph"
    @load="onLoad"
    @error="onError"
    :class="['base-image', passAttrs.class, { 'is-loaded': loaded }]"
  />
</template>

<script setup>
import { computed, ref } from 'vue'
import { useAttrs } from 'vue'

const props = defineProps({
  src: { type: String, default: '' },
  alt: { type: String, default: '' },
})

const attrs = useAttrs()

const passAttrs = computed(() => {
  const { placeholder, ...rest } = attrs
  return rest
})

const loaded = ref(false)
const img = useImage()

const placeholder = computed(() => {
  if (!props.src) return undefined
  return img(props.src, { w: 16, h: 16, f: 'webp', q: 20, blur: 1 })
})

function onLoad() {
  loaded.value = true
}

function onError() {
  loaded.value = false
}
</script>

<style scoped>
.base-image {
  transition:
    filter 0.35s ease,
    transform 0.35s ease,
    opacity 0.35s ease;
  opacity: 0.92;
}

.base-image-ph {
  filter: blur(20px);
  transform: scale(0.5);
}

.base-image.is-loaded {
  /* Allow filters from parent classes (e.g. grayscale for unfinished medals) */
  transform: none;
  opacity: 1;
}
</style>
