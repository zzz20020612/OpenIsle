<template>
  <BasePopup :visible="visible" @close="close">
    <div class="notification-popup">
      <div class="notification-popup-title">Notification settings are available</div>
      <div class="notification-popup-text">You can adjust notification types in Notifications -> Settings.</div>
      <div class="notification-popup-actions">
        <div class="notification-popup-close" @click="close">Dismiss</div>
        <div class="notification-popup-button" @click="gotoSetting">Open settings</div>
      </div>
    </div>
  </BasePopup>
</template>

<script setup>
import BasePopup from '~/components/BasePopup.vue'

defineProps({
  visible: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const gotoSetting = () => {
  emit('close')
  navigateTo('/message?tab=control', { replace: true })
}
const close = () => emit('close')
</script>

<style scoped>
.notification-popup {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 10px;
  min-width: 200px;
}

.notification-popup-title {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 10px;
}

.notification-popup-actions {
  margin-top: 10px;
  display: flex;
  flex-direction: row;
  gap: 20px;
}

.notification-popup-button {
  background-color: var(--primary-color);
  color: #fff;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
}

.notification-popup-button:hover {
  background-color: var(--primary-color-hover);
}

.notification-popup-close {
  cursor: pointer;
  color: var(--primary-color);
  display: flex;
  align-items: center;
}

.notification-popup-close:hover {
  text-decoration: underline;
}
</style>
