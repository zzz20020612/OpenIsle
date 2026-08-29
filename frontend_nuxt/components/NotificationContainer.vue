<template>
  <div class="notif-content-container">
    <div class="notif-content-container-item">
      <slot />
    </div>
    <slot name="actions">
      <div v-if="!item.read" class="mark-read-button" @click="markRead(item.id)">
        {{ isMobile ? 'OK' : 'Mark as read' }}
      </div>
      <div v-else class="has-read-button">Read</div>
    </slot>
  </div>
</template>

<script>
import { useIsMobile } from '~/utils/screen'
export default {
  name: 'NotificationContainer',
  props: {
    item: { type: Object, required: true },
    markRead: { type: Function, required: true },
  },
  setup() {
    const isMobile = useIsMobile()
    return {
      isMobile,
    }
  },
}
</script>

<style scoped>
.notif-content-container {
  color: rgb(140, 140, 140);
  font-weight: normal;
  font-size: 14px;
  opacity: 0.8;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mark-read-button {
  color: var(--primary-color);
  font-size: 12px;
  cursor: pointer;
  margin-left: 10px;
  white-space: nowrap;
}

.mark-read-button:hover {
  text-decoration: underline;
}

.has-read-button {
  font-size: 12px;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .has-read-button {
    display: none;
  }
}
</style>
