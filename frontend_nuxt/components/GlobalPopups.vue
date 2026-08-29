<template>
  <div>
    <NotificationSettingPopup :visible="showNotificationPopup" @close="closeNotificationPopup" />
  </div>
</template>

<script setup>
import NotificationSettingPopup from '~/components/NotificationSettingPopup.vue'
import { authState } from '~/utils/auth'

const showNotificationPopup = ref(false)

onMounted(async () => {
  await checkNotificationSetting()
})

const checkNotificationSetting = async () => {
  if (!import.meta.client) return
  if (!authState.loggedIn) return
  if (localStorage.getItem('notificationSettingPopupShown')) return
  showNotificationPopup.value = true
}
const closeNotificationPopup = () => {
  if (!import.meta.client) return
  localStorage.setItem('notificationSettingPopupShown', 'true')
  showNotificationPopup.value = false
}
</script>
