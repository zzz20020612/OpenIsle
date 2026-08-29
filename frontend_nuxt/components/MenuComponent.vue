<template>
  <transition name="slide">
    <nav v-if="visible" class="menu" aria-label="Primary navigation">
      <div class="menu-content">
        <div class="menu-item-container">
          <NuxtLink
            v-for="item in primaryItems"
            :key="item.to"
            class="menu-item"
            exact-active-class="selected"
            :to="item.to"
            @click="handleItemClick"
          >
            <component :is="item.icon" class="menu-item-icon" />
            <span class="menu-item-text">{{ item.label }}</span>
            <span v-if="item.badge" class="unread-container">
              <span class="unread">{{ item.badge }}</span>
            </span>
          </NuxtLink>
        </div>

        <ClientOnly>
          <div v-if="accountItems.length" class="menu-section">
            <div class="section-label">Account</div>
            <NuxtLink
              v-for="item in accountItems"
              :key="item.to"
              class="menu-item"
              exact-active-class="selected"
              :to="item.to"
              @click="handleItemClick"
            >
              <component :is="item.icon" class="menu-item-icon" />
              <span class="menu-item-text">{{ item.label }}</span>
            </NuxtLink>
          </div>
          <template #fallback>
            <div class="menu-section">
              <div class="section-label">Account</div>
            </div>
          </template>
        </ClientOnly>

      </div>

      <ClientOnly v-if="!isMobile">
        <div class="menu-footer">
          <button class="menu-footer-btn" type="button" @click="cycleTheme" aria-label="Switch theme">
            <component :is="iconClass" class="menu-item-icon" />
          </button>
        </div>
      </ClientOnly>
    </nav>
  </transition>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { authState } from '~/utils/auth'
import {
  fetchUnreadCount as fetchNotificationUnreadCount,
  notificationState,
} from '~/utils/notification'
import { useUnreadCount } from '~/composables/useUnreadCount'
import { useChannelsUnreadCount } from '~/composables/useChannelsUnreadCount'
import { useIsMobile } from '~/utils/screen'
import { cycleTheme, ThemeMode, themeState } from '~/utils/theme'

const isMobile = useIsMobile()

const props = defineProps({
  visible: { type: Boolean, default: true },
})
const emit = defineEmits(['item-click'])

const { count: unreadMessageCount, fetchUnreadCount: fetchMessageUnreadCount } = useUnreadCount()
const { hasUnread: hasChannelUnread, fetchChannelUnread } = useChannelsUnreadCount()
const unreadNotificationCount = computed(() => notificationState.unreadCount)
const showUnreadNotificationCount = computed(() =>
  unreadNotificationCount.value > 99 ? '99+' : unreadNotificationCount.value,
)
const showUnreadMessageCount = computed(() =>
  unreadMessageCount.value > 99 ? '99+' : unreadMessageCount.value,
)

const primaryItems = computed(() => [
  { to: '/papers', label: 'Papers', icon: 'hashtag-key' },
  { to: '/literature', label: 'Knowledge Base', icon: 'code-icon' },
  { to: '/papers/submit', label: 'Submit', icon: 'edit' },
  { to: '/papers/rankings', label: 'Rankings', icon: 'chart-line' },
  { to: '/papers/review-tasks', label: 'Review Tasks', icon: 'check-correct' },
  {
    to: '/message',
    label: 'Notifications',
    icon: 'remind',
    badge: unreadNotificationCount.value > 0 ? showUnreadNotificationCount.value : '',
  },
  {
    to: '/message-box',
    label: 'Messages',
    icon: 'message-emoji',
    badge: unreadMessageCount.value > 0 ? showUnreadMessageCount.value : hasChannelUnread.value ? '!' : '',
  },
])

const accountItems = computed(() => {
  if (!authState.loggedIn) {
    return [{ to: '/login', label: 'Log in', icon: 'login' }]
  }
  const items = [
    {
      to: `/users/${authState.username || authState.userId}`,
      label: 'Profile',
      icon: 'user',
    },
    { to: '/papers/submissions', label: 'My Submissions', icon: 'file-text' },
    { to: '/settings', label: 'Settings', icon: 'setting' },
  ]
  if (authState.role === 'ADMIN') {
    items.push({ to: '/admin/papers', label: 'Paper Admin', icon: 'setting-config' })
  }
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
  if (authState.loggedIn) {
    await Promise.all([
      fetchNotificationUnreadCount(),
      fetchMessageUnreadCount(),
      fetchChannelUnread(),
    ])
  } else {
    notificationState.unreadCount = 0
  }
})

const handleItemClick = () => {
  if (window.innerWidth <= 768) emit('item-click')
}
</script>

<style scoped>
.menu {
  position: sticky;
  top: var(--header-height);
  width: 220px;
  height: calc(100vh - var(--header-height));
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  border-right: 1px solid var(--menu-border-color);
  background-color: var(--app-menu-background-color);
  backdrop-filter: var(--blur-10);
  scrollbar-width: none;
}

.menu-content {
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  padding: 10px 10px 0;
  overflow-y: auto;
  scrollbar-width: none;
}

.menu-content::-webkit-scrollbar,
.menu::-webkit-scrollbar {
  display: none;
}

.menu-item-container,
.menu-section {
  padding-bottom: 6px;
  margin-bottom: 6px;
  border-bottom: 1px solid var(--menu-border-color);
}

.section-label {
  padding: 8px 12px 5px;
  color: var(--menu-text-color);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.62;
}

.menu-item {
  display: flex;
  align-items: center;
  min-height: 34px;
  padding: 6px 12px;
  border-radius: 10px;
  color: var(--menu-text-color);
  text-decoration: none;
  transition: background-color 0.18s ease;
}

.menu-item:hover {
  background-color: var(--menu-selected-background-color-hover);
}

.menu-item.selected {
  font-weight: 800;
  background-color: var(--menu-selected-background-color);
}

.menu-item-text {
  color: var(--menu-text-color);
  font-size: 14px;
  text-decoration: none;
}

.menu-item-icon {
  margin-right: 10px;
  opacity: 0.62;
  font-weight: bold;
}

.unread-container {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  margin-left: auto;
  border-radius: 50%;
  background-color: rgb(255, 102, 102);
  text-align: center;
}

.unread {
  color: white;
  font-size: 9px;
  font-weight: bold;
}

.menu-footer {
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 6px 6px;
}

.menu-footer-btn {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 8px;
  color: var(--menu-text-color);
  background: transparent;
  cursor: pointer;
}

.menu-footer-btn:hover {
  background-color: var(--menu-selected-background-color-hover);
}

@media (max-width: 768px) {
  .menu {
    position: fixed;
    z-index: 1000;
    left: 10px;
    top: calc(var(--header-height) + 10px);
    height: auto;
    max-height: 420px;
    padding-top: 10px;
    border-right: none;
    border-radius: 20px;
    background-color: var(--background-color-blur);
    box-shadow: 0 0 10px 0 rgba(0, 0, 0, 0.1);
  }

  .menu-content {
    border-radius: 20px;
  }

  .slide-enter-active,
  .slide-leave-active {
    transition:
      transform 0.3s ease,
      opacity 0.3s ease,
      width 0.3s ease;
  }

  .slide-enter-from,
  .slide-leave-to {
    transform: translateX(-100%);
    opacity: 0;
  }

  .slide-enter-to,
  .slide-leave-from {
    transform: translateX(0);
    opacity: 1;
  }
}
</style>
