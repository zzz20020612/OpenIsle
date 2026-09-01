<template><div class="preference-actions"><button v-if="showReset" type="button" class="paper-button" @click="$emit('reset')">Restore defaults</button><button type="submit" class="paper-button primary">Save preferences</button></div></template>
<script setup>defineProps({showReset:Boolean});defineEmits(['reset'])</script>
<style scoped>.preference-actions{display:flex;gap:8px;margin-top:16px}</style>
