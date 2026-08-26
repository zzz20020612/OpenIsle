<template><div v-if="!entries.length" class="empty">No data.</div><table v-else><tbody><tr v-for="([key,value]) in entries" :key="key"><th>{{ label(key) }}</th><td>{{ display(value) }}</td></tr></tbody></table></template>
<script setup>
const props=defineProps({value:{type:Object,default:()=>({})}});const entries=computed(()=>Object.entries(props.value||{}));const label=(v)=>v.replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());const display=(v)=>v==null?'—':typeof v==='object'?Object.entries(v).map(([k,x])=>`${label(k)}: ${x}`).join(' · '):String(v)
</script>
