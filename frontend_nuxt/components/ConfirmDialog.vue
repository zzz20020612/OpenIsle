<template>
  <BasePopup :visible="visible" @close="onCancel">
    <div class="confirm-dialog" role="dialog" aria-modal="true">
      <h3 class="confirm-title">{{ title }}</h3>
      <p class="confirm-message">{{ message }}</p>
      <div class="confirm-actions">
        <button class="cancel-button" type="button" @click="onCancel">Cancel</button>
        <button class="confirm-button" type="button" @click="onConfirm">Confirm</button>
      </div>
    </div>
  </BasePopup>
</template>

<script setup lang="ts">
import BasePopup from '~/components/BasePopup.vue'
import { useConfirm } from '~/composables/useConfirm'

const { visible, title, message, onConfirm, onCancel } = useConfirm()
</script>

<style scoped>
.confirm-dialog {
  padding: 20px;
  text-align: center;
}
.confirm-title {
  margin-top: 0;
  font-size: 18px;
  font-weight: 600;
}
.confirm-message {
  margin: 16px 0 20px;
  line-height: 1.6;
  color: var(--text-secondary, #666);
}
.confirm-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
}
.confirm-button,
.cancel-button {
  min-width: 88px;
  height: 36px;
  padding: 0 14px;
  border-radius: 8px;
  cursor: pointer;
  border: 1px solid transparent;
}
.confirm-button {
  background: var(--primary-color);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}
.confirm-button:hover {
  background: var(--primary-color-hover);
}
.cancel-button {
  background: transparent;
  color: var(--primary-color);
  border-color: currentColor;
  display: flex;
  align-items: center;
  justify-content: center;
}
.cancel-button:hover {
  opacity: 0.85;
}
</style>
