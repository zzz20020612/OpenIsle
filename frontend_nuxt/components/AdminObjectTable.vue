<template><div v-if="!entries.length" class="empty">No data.</div><table v-else><tbody><tr v-for="([key,value]) in entries" :key="key"><th>{{ label(key) }}</th><td>{{ display(value) }}</td></tr></tbody></table></template>
<script setup>
const props=defineProps({value:{type:Object,default:()=>({})}});const entries=computed(()=>Object.entries(props.value||{}));const label=(v)=>String(v).replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());const display=(value)=>{if(value==null)return'—';if(Array.isArray(value))return value.length?value.map((item,index)=>`${index+1}. ${display(item)}`).join(' | '):'—';if(typeof value==='object')return Object.entries(value).map(([key,item])=>`${label(key)}: ${display(item)}`).join(' · ');return String(value)}
</script>
