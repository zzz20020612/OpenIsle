<template>
  <section v-if="hasValue" class="knowledge-field">
    <h3>{{ label }}</h3>
    <ul v-if="Array.isArray(value)">
      <li v-for="(item, index) in value" :key="index">{{ formatItem(item) }}</li>
    </ul>
    <p v-else>{{ formatItem(value) }}</p>
  </section>
</template>

<script setup>
const props = defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number, Array, Object], default: null },
})

const hasValue = computed(() => {
  if (Array.isArray(props.value)) return props.value.length > 0
  return props.value !== null && props.value !== undefined && props.value !== ''
})

function formatItem(value) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'object') {
    return value.text || value.claim || value.description || JSON.stringify(value)
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
.knowledge-field ul {
  margin: 0;
  color: var(--paper-ink);
  font-family: var(--paper-font-title);
  font-size: 16px;
  line-height: 1.7;
  white-space: pre-line;
}

.knowledge-field ul {
  display: grid;
  gap: 6px;
  padding-left: 20px;
}
</style>
