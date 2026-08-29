<template>
  <div v-if="floatRoute" class="message-float-window" :style="{ height: floatHeight }">
    <iframe :src="iframeSrc" frameborder="0" ref="iframeRef" @load="injectBaseTag"></iframe>

    <div class="float-actions">
      <down v-if="floatHeight !== MINI_HEIGHT" title="Minimise message window" @click="collapseToMini" />
      <up v-if="floatHeight !== DEFAULT_HEIGHT" title="Restore message window" @click="reboundToDefault" />
      <expand-up title="Open on full page" @click="expand" />
      <close-icon title="Close" @click="close" />
    </div>
  </div>
</template>

<script setup>
const floatRoute = useState('messageFloatRoute')

const DEFAULT_HEIGHT = '60vh'
const MINI_HEIGHT = '45px'
const floatHeight = ref(DEFAULT_HEIGHT)

const iframeRef = ref(null)
const iframeSrc = computed(() => {
  if (!floatRoute.value) return ''
  return floatRoute.value + (floatRoute.value.includes('?') ? '&' : '?') + 'float=1'
})

function collapseToMini() {
  floatHeight.value = MINI_HEIGHT
}

function reboundToDefault() {
  floatHeight.value = DEFAULT_HEIGHT
}

function expand() {
  if (!floatRoute.value) return
  const target = floatRoute.value
  floatRoute.value = null
  navigateTo(target)
}

function close() {
  floatRoute.value = null
}

function injectBaseTag() {
  if (!iframeRef.value) return

  const iframeDoc = iframeRef.value.contentDocument || iframeRef.value.contentWindow.document
  if (iframeDoc && !iframeDoc.querySelector('base')) {
    const base = iframeDoc.createElement('base')
    base.target = '_top'
    iframeDoc.head.appendChild(base)
  }
}

watch(
  () => floatRoute.value,
  (v) => {
    if (v) floatHeight.value = DEFAULT_HEIGHT
  },
)
</script>

<style scoped>
.message-float-window {
  position: fixed;
  bottom: 0;
  right: 0;
  width: 400px;
  max-height: 90vh;
  background-color: var(--background-color);
  border: 1px solid var(--normal-border-color);
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
  z-index: 2000;
  display: flex;
  flex-direction: column;
  transition: height 0.25s ease;
  /* 平滑过渡 */
}

.message-float-window iframe {
  width: 100%;
  flex: 1;
}

.float-actions {
  position: absolute;
  top: 4px;
  right: 8px;
  padding: 12px;
  display: flex;
  gap: 10px;
}

.float-actions i {
  cursor: pointer;
  font-size: 14px;
  opacity: 0.9;
}

.float-actions i:hover {
  opacity: 1;
}
</style>
