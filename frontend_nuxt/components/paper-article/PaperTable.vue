<template>
  <figure class="article-table">
    <figcaption><strong>{{ label }}. </strong>{{ block.caption }}</figcaption>
    <div class="table-scroll">
      <table>
        <thead><tr><th v-for="(column, index) in block.columns || []" :key="`${column}-${index}`">{{ column }}</th></tr></thead>
        <tbody>
          <tr v-for="(row, rowIndex) in block.rows || []" :key="rowIndex">
            <td v-for="(cell, cellIndex) in row" :key="`${rowIndex}-${cellIndex}`">{{ cell }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <small v-if="block.notes">{{ block.notes }}</small>
  </figure>
</template>

<script setup>
defineProps({
  block: { type: Object, required: true },
  label: { type: String, default: 'Table' },
})
</script>

<style scoped>
.article-table { margin: 28px 0; }
.article-table figcaption { margin-bottom: 10px; color: #35454f; font-size: 14px; line-height: 1.5; }
.table-scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { padding: 9px 12px; border-bottom: 1px solid #cbd5da; text-align: left; white-space: nowrap; }
th { border-top: 2px solid #52636d; color: #17232c; font-weight: 750; }
.article-table small { display: block; margin-top: 8px; color: #68747c; }
</style>
