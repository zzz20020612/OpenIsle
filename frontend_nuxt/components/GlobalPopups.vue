<template>
  <div>
    <NotificationSettingPopup :visible="showNotificationPopup" @close="closeNotificationPopup" />
    <MessagePopup :visible="showMessagePopup" @close="closeMessagePopup" />
    <MedalPopup :visible="showMedalPopup" :medals="newMedals" @close="closeMedalPopup" />
  </div>
</template>

<script setup>
import MedalPopup from '~/components/MedalPopup.vue'
import NotificationSettingPopup from '~/components/NotificationSettingPopup.vue'
import MessagePopup from '~/components/MessagePopup.vue'
import { authState } from '~/utils/auth'

const showNotificationPopup = ref(false)
const showMessagePopup = ref(false)
const showMedalPopup = ref(false)
const newMedals = ref([])

onMounted(async () => {
  await checkMessageFeature()
  if (showMessagePopup.value) return

  await checkNotificationSetting()
  if (showNotificationPopup.value) return

  await checkNewMedals()
})

const checkMessageFeature = async () => {
  if (!import.meta.client) return
  if (!authState.loggedIn) return
  if (localStorage.getItem('messageFeaturePopupShown')) return
  showMessagePopup.value = true
}
const closeMessagePopup = () => {
  if (!import.meta.client) return
  localStorage.setItem('messageFeaturePopupShown', 'true')
  showMessagePopup.value = false
}

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
const checkNewMedals = async () => {
  if (!import.meta.client) return
  if (!authState.loggedIn || !authState.userId) return
  try {
    const res = await fetch(`${API_BASE_URL}/api/medals?userId=${authState.userId}`)
    if (res.ok) {
      const medals = await res.json()
      const seen = JSON.parse(localStorage.getItem('seenMedals') || '[]')
      const m = medals.filter((i) => i.completed && !seen.includes(i.type))
      if (m.length > 0) {
        newMedals.value = m
        showMedalPopup.value = true
      }
    }
  } catch (e) {
    // ignore errors
  }
}
const closeMedalPopup = () => {
  if (!import.meta.client) return
  const seen = new Set(JSON.parse(localStorage.getItem('seenMedals') || '[]'))
  newMedals.value.forEach((m) => seen.add(m.type))
  localStorage.setItem('seenMedals', JSON.stringify([...seen]))
  showMedalPopup.value = false
}
</script>
