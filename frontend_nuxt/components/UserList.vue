<template>
  <div class="user-list">
    <BasePlaceholder v-if="users.length === 0" text="No researchers found" icon="inbox" />
    <div v-for="u in users" :key="u.id" class="user-item">
      <BaseUserAvatar :src="u.avatar" :user-id="u.id" alt="avatar" class="user-avatar" />
      <div class="user-info">
        <div class="user-name">{{ u.username }}</div>
        <div v-if="u.introduction" class="user-intro">{{ u.introduction }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import BasePlaceholder from '~/components/BasePlaceholder.vue'
import BaseUserAvatar from '~/components/BaseUserAvatar.vue'

defineProps({
  users: { type: Array, default: () => [] },
})

const handleUserClick = (user) => {
  navigateTo(`/users/${user.id}`, { replace: true })
}
</script>

<style scoped>
.user-list {
  display: flex;
  flex-direction: column;
}
.user-item {
  padding-top: 20px;
  padding-bottom: 20px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  border-bottom: 1px solid var(--normal-border-color);
}
.user-avatar {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  flex-shrink: 0;
}

.user-avatar :deep(.base-user-avatar-img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.user-info {
  display: flex;
  flex-direction: column;
}
.user-name {
  font-weight: bold;
}
.user-intro {
  font-size: 14px;
  opacity: 0.7;
}
</style>
