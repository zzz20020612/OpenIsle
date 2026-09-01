<template>
  <section v-if="hasValue" class="knowledge-field">
    <h3>{{ label }}</h3>
    <ul v-if="Array.isArray(normalizedValue)">
      <li v-for="(item, index) in normalizedValue" :key="index">{{ formatItem(item) }}</li>
    </ul>
    <dl v-else-if="isStructuredObject" class="knowledge-object">
      <div v-for="([key, item]) in objectEntries" :key="key">
        <dt>{{ formatLabel(key) }}</dt>
        <dd>{{ formatItem(item) }}</dd>
      </div>
    </dl>
    <p v-else>{{ formatItem(normalizedValue) }}</p>
  </section>
</template>

<script setup>
const props = defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number, Array, Object], default: null },
})

const normalizedValue = computed(() => {
  if (typeof props.value !== 'string') return props.value
  const text = props.value.trim()
  if (!text || !['{', '['].includes(text[0])) return props.value
  try { return JSON.parse(text) } catch { return props.value }
})
const hasValue = computed(() => {
  if (Array.isArray(normalizedValue.value)) return normalizedValue.value.length > 0
  if (normalizedValue.value && typeof normalizedValue.value === 'object') return Object.keys(normalizedValue.value).length > 0
  return normalizedValue.value !== null && normalizedValue.value !== undefined && normalizedValue.value !== ''
})
const isStructuredObject = computed(() => normalizedValue.value && typeof normalizedValue.value === 'object' && !Array.isArray(normalizedValue.value))
const objectEntries = computed(() => isStructuredObject.value ? Object.entries(normalizedValue.value) : [])

function formatLabel(value) {
  return String(value).replaceAll('_', ' ').replace(/^./, (letter) => letter.toUpperCase())
}

function formatItem(value) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'object') {
    return value.text || value.claim || value.description || Object.entries(value).map(([key, item]) => `${formatLabel(key)}: ${formatItem(item)}`).join(' · ')
  }
  return String(value)
}
</script>

<style scoped>
.knowledge-field {
  padding: 14px 0;
  border-top: 1px solid var(--paper-line);
}

.knowledge-field:first-of-type {
  border-top: 0;
  padding-top: 0;
}

.knowledge-field:last-child {
  padding-bottom: 0;
}

.knowledge-field h3 {
  margin: 0 0 7px;
  color: var(--paper-soft);
  font-size: 11px;
  font-weight: 780;
  letter-spacing: 0.045em;
  text-transform: uppercase;
}

.knowledge-field p,
.knowledge-field ul,
.knowledge-object {
  margin: 0;
  color: var(--paper-ink);
  font-family: var(--paper-font-title);
  font-size: 16px;
  line-height: 1.7;
  white-space: pre-line;
}

.knowledge-object {
  display: grid;
  gap: 8px;
}

.knowledge-object div {
  display: grid;
  grid-template-columns: minmax(130px, .35fr) 1fr;
  gap: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--paper-line);
}

.knowledge-object dt {
  color: var(--paper-soft);
  font-family: var(--paper-font-ui);
  font-size: 11px;
  font-weight: 750;
  text-transform: uppercase;
}

.knowledge-object dd { margin: 0; }

.knowledge-field ul {
  display: grid;
  gap: 6px;
  padding-left: 20px;
}
</style>
