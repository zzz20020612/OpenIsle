<template>
  <header class="header">
    <div class="header-content">
      <div class="header-content-left">
        <div v-if="showMenuBtn" class="menu-btn-wrapper">
          <button class="menu-btn" ref="menuBtn" type="button" @click="$emit('toggle-menu')">
            <ToolTip content="Toggle navigation" placement="bottom">
              <application-menu class="micon" />
            </ToolTip>
          </button>
          <span
            v-if="isMobile && (unreadMessageCount > 0 || hasChannelUnread)"
            class="menu-unread-dot"
          ></span>
        </div>

        <NuxtLink class="logo-container" to="/" @click="refreshData">
          <BaseImage
            alt="OpenIsle"
            src="https://openisle-1307107697.cos.ap-guangzhou.myqcloud.com/assert/image.png"
            width="42"
            height="42"
          />
          <div class="logo-copy">
            <span class="logo-text">OpenIsle</span>
            <span class="logo-subtitle">Research Evaluation</span>
          </div>
        </NuxtLink>
      </div>

      <ClientOnly>
        <div class="header-content-right">
          <SearchDropdown
            ref="searchDropdown"
            v-if="!isMobile || showSearch"
            @close="closeSearch"
          />

          <ToolTip v-if="isMobile" content="Search" placement="bottom">
            <button class="header-icon-item" type="button" @click="search">
              <search-icon class="header-icon" />
              <span class="header-label">Search</span>
            </button>
          </ToolTip>

          <ToolTip v-if="isMobile" content="Switch theme" placement="bottom">
            <button class="header-icon-item" type="button" @click="cycleTheme">
              <component :is="iconClass" class="header-icon" />
              <span class="header-label">Theme</span>
            </button>
          </ToolTip>

          <ToolTip v-if="!isMobile" content="Copy invite link" placement="bottom">
            <button class="header-icon-item" type="button" @click="copyInviteLink">
              <template v-if="!isCopying">
                <copy-link class="header-icon" />
                <span class="header-label">Invite</span>
              </template>
              <loading v-else />
            </button>
          </ToolTip>

          <ToolTip v-if="!isMobile" content="Online users" placement="bottom">
            <div class="header-icon-item passive">
              <peoples-two class="header-icon" />
              <span class="header-label">Online</span>
              <span class="header-badge">{{ onlineCount }}</span>
            </div>
          </ToolTip>

          <ToolTip content="Copy RSS link" placement="bottom">
            <button class="header-icon-item" type="button" @click="copyRssLink">
              <rss class="header-icon" />
              <span class="header-label">RSS</span>
            </button>
          </ToolTip>

          <ToolTip v-if="!isMobile && isLogin" content="Submit a paper" placement="bottom">
            <button class="header-submit-button" type="button" @click="goToSubmitPaper">
              <edit class="header-icon" />
              <span>Submit</span>
            </button>
          </ToolTip>

          <ToolTip v-if="isLogin" content="Messages and channels" placement="bottom">
            <button class="header-icon-item" type="button" @click="goToMessages">
              <message-emoji class="header-icon" />
              <span class="header-label">Messages</span>
              <span v-if="unreadMessageCount > 0" class="unread-badge">
                {{ unreadMessageCount }}
              </span>
              <span v-else-if="hasChannelUnread" class="unread-dot"></span>
            </button>
          </ToolTip>

          <DropdownMenu v-if="isLogin" ref="userMenu" :items="headerMenuItems">
            <template #trigger>
              <button class="avatar-container" type="button">
                <BaseUserAvatar
                  class="avatar-img"
                  :user-id="authState.userId"
                  :src="authState.avatar"
                  :disable-link="true"
                  :width="32"
                />
                <down />
              </button>
            </template>
          </DropdownMenu>

          <div v-if="!isLogin" class="auth-btns">
            <button class="header-content-item-secondary" type="button" @click="goToLogin">
              Log in
            </button>
            <button class="header-content-item-main" type="button" @click="goToSignup">
              Sign up
            </button>
          </div>
        </div>
      </ClientOnly>
    </div>
  </header>
</template>

<script setup>
import { ClientOnly } from '#components'
import { computed, nextTick, onMounted, ref } from 'vue'
import DropdownMenu from '~/components/DropdownMenu.vue'
import ToolTip from '~/components/ToolTip.vue'
import SearchDropdown from '~/components/SearchDropdown.vue'
import BaseUserAvatar from '~/components/BaseUserAvatar.vue'
import { authState, clearToken, getToken } from '~/utils/auth'
import { useUnreadCount } from '~/composables/useUnreadCount'
import { useChannelsUnreadCount } from '~/composables/useChannelsUnreadCount'
import { useIsMobile } from '~/utils/screen'
import { themeState, cycleTheme, ThemeMode } from '~/utils/theme'
import { toast } from '~/main'

const config = useRuntimeConfig()
const API_BASE_URL = config.public.apiBaseUrl
const WEBSITE_BASE_URL = config.public.websiteBaseUrl

defineProps({
  showMenuBtn: {
    type: Boolean,
    default: true,
  },
})

const isLogin = computed(() => authState.loggedIn)
const isMobile = useIsMobile()
const { count: unreadMessageCount, fetchUnreadCount } = useUnreadCount()
const { hasUnread: hasChannelUnread, fetchChannelUnread } = useChannelsUnreadCount()
const showSearch = ref(false)
const searchDropdown = ref(null)
const isCopying = ref(false)
const onlineCount = ref(0)

async function sendPing() {
  try {
    let userId = authState.userId
    if (userId) {
      localStorage.removeItem('guestId')
    } else {
      let savedId = localStorage.getItem('guestId')
      if (!savedId) {
        savedId = `guest-${crypto.randomUUID()}`
        localStorage.setItem('guestId', savedId)
      }
      userId = savedId
    }
    await fetch(`${API_BASE_URL}/api/online/heartbeat?userId=${userId}`, { method: 'POST' })
  } catch (error) {
    console.error('Online heartbeat failed', error)
  }
}

async function fetchCount() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/online/count`, { method: 'GET' })
    onlineCount.value = await res.json()
  } catch (error) {
    console.error('Failed to fetch online count', error)
  }
}

const search = () => {
  showSearch.value = true
  nextTick(() => {
    searchDropdown.value?.toggle?.()
  })
}

const closeSearch = () => {
  nextTick(() => {
    showSearch.value = false
  })
}

const goToLogin = () => {
  navigateTo('/login', { replace: true })
}

const goToSignup = () => {
  navigateTo('/signup', { replace: true })
}

const goToSettings = () => {
  navigateTo('/settings', { replace: true })
}

const goToAdminPapers = () => {
  navigateTo('/admin/papers', { replace: false })
}

const goToProfile = () => {
  const id = authState.username || authState.id
  if (id) {
    navigateTo(`/users/${id}`, { replace: true })
  }
}

const goToLogout = () => {
  clearToken()
  navigateTo('/login', { replace: true })
}

const goToSubmitPaper = () => {
  navigateTo({
    path: '/papers/submit',
    query: { entry: Date.now().toString() },
  }, { replace: false })
}

const goToMessages = () => {
  navigateTo('/message-box')
}

const refreshData = () => {
  window.dispatchEvent(new Event('refresh-home'))
}

const copyInviteLink = async () => {
  isCopying.value = true
  const token = getToken()
  if (!token) {
    toast.error('Please log in first.')
    isCopying.value = false
    return
  }
  try {
    const res = await fetch(`${API_BASE_URL}/api/invite/generate`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      toast.error(data.error || 'Failed to generate invite link.')
      return
    }
    const data = await res.json()
    const inviteLink = data.token ? `${WEBSITE_BASE_URL}/signup?invite_token=${data.token}` : ''
    await navigator.clipboard.writeText(inviteLink)
    toast.success('Invite link copied.')
  } catch (error) {
    toast.error('Failed to generate invite link.')
  } finally {
    isCopying.value = false
  }
}

const copyRssLink = async () => {
  await navigator.clipboard.writeText(`${API_BASE_URL}/api/rss`)
  toast.success('RSS link copied.')
}

const headerMenuItems = computed(() => {
  const items = [
    { text: 'Settings', onClick: goToSettings },
    { text: 'Profile', onClick: goToProfile },
  ]
  if (authState.role === 'ADMIN') {
    items.push({ text: 'Paper Admin', onClick: goToAdminPapers })
  }
  items.push({ text: 'Log out', onClick: goToLogout })
  return items
})

const iconClass = computed(() => {
  switch (themeState.mode) {
    case ThemeMode.DARK:
      return 'Moon'
    case ThemeMode.LIGHT:
      return 'SunOne'
    default:
      return 'ComputerOne'
  }
})

onMounted(async () => {
  const updateUnread = async () => {
    if (authState.loggedIn) {
      fetchUnreadCount()
      fetchChannelUnread()
    } else {
      fetchChannelUnread()
    }
  }

  await updateUnread()
  sendPing()
  fetchCount()
  setInterval(sendPing, 120000)
  setInterval(fetchCount, 60000)
})
</script>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: center;
  height: var(--header-height);
  background: color-mix(in srgb, var(--background-color) 86%, transparent);
  backdrop-filter: var(--blur-10);
  color: var(--header-text-color);
  border-bottom: 1px solid var(--header-border-color);
}

.header-content {
  display: flex;
  align-items: center;
  width: 100%;
  height: 100%;
  max-width: var(--page-max-width);
  padding: 0 18px;
}

.header-content-left,
.header-content-right,
.auth-btns {
  display: flex;
  align-items: center;
}

.header-content-right {
  margin-left: auto;
  gap: 18px;
}

.auth-btns {
  gap: 10px;
}

.logo-container {
  display: flex;
  align-items: center;
  gap: 9px;
  color: inherit;
  text-decoration: none;
}

.logo-copy {
  display: grid;
  gap: 1px;
}

.logo-text {
  color: var(--header-text-color);
  font-size: 17px;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.logo-subtitle {
  color: var(--menu-text-color);
  font-size: 10px;
  font-weight: 650;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.menu-btn,
.header-icon-item,
.avatar-container,
.header-content-item-main,
.header-content-item-secondary,
.header-submit-button {
  border: 0;
  font: inherit;
  cursor: pointer;
}

.menu-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  margin-right: 8px;
  border-radius: 12px;
  color: var(--menu-text-color);
  background: transparent;
}

.menu-btn:hover,
.header-icon-item:hover,
.avatar-container:hover {
  background: var(--secondary-color-hover);
}

.menu-btn-wrapper {
  position: relative;
  display: inline-flex;
}

.micon {
  font-size: 23px;
}

.menu-unread-dot,
.unread-dot {
  position: absolute;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #b74135;
}

.menu-unread-dot {
  top: 4px;
  right: 10px;
}

.unread-dot {
  top: 4px;
  right: 4px;
}

.header-icon-item {
  position: relative;
  display: inline-flex;
  min-width: 42px;
  min-height: 42px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  border-radius: 12px;
  color: var(--menu-text-color);
  background: transparent;
  transition:
    background 0.18s ease,
    color 0.18s ease,
    transform 0.15s ease;
}

.header-icon-item:not(.passive):active {
  transform: translateY(1px);
}

.header-icon-item.passive {
  cursor: default;
}

.header-icon,
.theme-icon {
  font-size: 19px;
  line-height: 1;
}

.header-label {
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
}

.header-submit-button {
  display: inline-flex;
  min-height: 40px;
  align-items: center;
  gap: 7px;
  padding: 0 14px;
  border: 1px solid color-mix(in srgb, var(--primary-color) 24%, transparent);
  border-radius: 999px;
  color: #fff;
  background: var(--primary-color);
  font-size: 13px;
  font-weight: 780;
}

.header-submit-button:hover {
  background: var(--primary-color-hover);
}

.header-badge,
.unread-badge {
  position: absolute;
  top: -3px;
  right: -5px;
  display: inline-flex;
  min-width: 17px;
  min-height: 17px;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
  border-radius: 999px;
  color: #fff;
  background: #b74135;
  font-size: 10px;
  font-weight: 800;
  line-height: 1;
}

.header-badge {
  color: var(--primary-color);
  background: transparent;
}

.avatar-container {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 4px 6px;
  border-radius: 999px;
  color: var(--menu-text-color);
  background: transparent;
}

.avatar-img {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: lightgray;
  object-fit: cover;
}

.header-content-item-main,
.header-content-item-secondary {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 760;
}

.header-content-item-main {
  color: #fff;
  background: var(--primary-color);
}

.header-content-item-main:hover {
  background: var(--primary-color-hover);
}

.header-content-item-secondary {
  color: var(--primary-color);
  background: transparent;
}

.header-content-item-secondary:hover {
  background: var(--secondary-color-hover);
}

@media (max-width: 768px) {
  .logo-subtitle,
  .header-content-item-secondary,
  .header-label,
  .header-badge {
    display: none;
  }

  .header-content {
    padding: 0 12px;
  }

  .header-content-right {
    gap: 8px;
  }
}
</style>
