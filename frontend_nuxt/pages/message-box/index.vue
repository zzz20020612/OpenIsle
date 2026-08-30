<template>
  <main class="messages-container" :class="{ float: isFloatMode }">
    <header v-if="!isFloatMode" class="page-title">
      <div><p>RESEARCH NETWORK</p><h1>Messages</h1><span>Direct conversations and team channels associated with your OpenIsle account.</span></div>
    </header>
    <div v-if="!isFloatMode" class="float-control">
      <collapse-text-input class="float-control-icon" @click="minimize" title="Minimize" />
    </div>
    <BaseTabs v-model="activeTab" :tabs="tabs">
      <div v-if="activeTab === 'messages'">
        <div v-if="loading" class="loading-message">
          <l-hatch size="28" stroke="4" speed="3.5" color="var(--primary-color)"></l-hatch>
        </div>

        <div v-else-if="error" class="error-container">
          <div class="error-text">{{ error }}</div>
        </div>

        <div v-if="!loading && !isFloatMode" class="search-container">
          <SearchPersonDropdown />
        </div>

        <div v-if="!loading && conversations.length === 0" class="empty-container">
          <BasePlaceholder v-if="conversations.length === 0" text="No conversations yet" icon="inbox" />
        </div>

        <div
          v-if="!loading"
          v-for="convo in conversations"
          :key="convo.id"
          class="conversation-item"
          @click="goToConversation(convo.id)"
        >
          <div class="conversation-avatar">
            <BaseUserAvatar
              :src="getOtherParticipant(convo)?.avatar"
              :user-id="getOtherParticipant(convo)?.id"
              :alt="getOtherParticipant(convo)?.username || 'User'"
              class="avatar-img"
              :disable-link="true"
            />
          </div>

          <div class="conversation-content">
            <div class="conversation-header">
              <div class="participant-name">
                {{ getOtherParticipant(convo)?.username || 'Unknown user' }}
              </div>
              <div class="message-time">
                {{ formatTime(convo.lastMessage?.createdAt || convo.createdAt) }}
              </div>
            </div>

            <div class="last-message-row">
              <div class="last-message">
                {{
                  convo.lastMessage
                    ? stripMarkdownLength(convo.lastMessage.content, 100)
                    : 'No messages yet'
                }}
              </div>
              <div v-if="convo.unreadCount > 0" class="unread-count-badge">
                {{ convo.unreadCount }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else>
        <div v-if="loadingChannels" class="loading-message">
          <l-hatch size="28" stroke="4" speed="3.5" color="var(--primary-color)"></l-hatch>
        </div>
        <div v-else>
          <div v-if="channels.length === 0" class="empty-container">
            <BasePlaceholder text="No channels yet" icon="inbox" />
          </div>
          <div
            v-for="ch in channels"
            :key="ch.id"
            class="conversation-item"
            @click="goToChannel(ch.id)"
          >
            <div class="conversation-avatar">
              <BaseImage
                :src="ch.avatar"
                :alt="ch.name"
                class="avatar-img"
                @error="handleAvatarError"
              />
            </div>
            <div class="conversation-content">
              <div class="conversation-header">
                <div class="participant-name">
                  {{ ch.name }}
                  <span v-if="ch.unreadCount > 0" class="unread-dot"></span>
                </div>
                <div class="message-time">
                  {{ formatTime(ch.lastMessage?.createdAt || ch.createdAt) }}
                </div>
              </div>
              <div class="last-message-row">
                <div class="last-message">
                  {{
                    ch.lastMessage
                      ? stripMarkdownLength(ch.lastMessage.content, 100)
                      : ch.description
                  }}
                </div>
                <div class="member-count">{{ ch.memberCount }} members</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </BaseTabs>
  </main>
</template>

<script setup>
import { ref, onUnmounted, watch, onActivated, computed, onDeactivated } from 'vue'
import { useRoute } from 'vue-router'
import { getToken, fetchCurrentUser } from '~/utils/auth'
import { toast } from '~/main'
import { useWebSocket } from '~/composables/useWebSocket'
import { useUnreadCount } from '~/composables/useUnreadCount'
import { useChannelsUnreadCount } from '~/composables/useChannelsUnreadCount'
import TimeManager from '~/utils/time'
import { stripMarkdownLength } from '~/utils/markdown'
import SearchPersonDropdown from '~/components/SearchPersonDropdown.vue'
import BasePlaceholder from '~/components/BasePlaceholder.vue'
import BaseTabs from '~/components/BaseTabs.vue'
import BaseUserAvatar from '~/components/BaseUserAvatar.vue'

useHead({ title: 'Messages - OpenIsle' })

const config = useRuntimeConfig()
const conversations = ref([])
const loading = ref(true)
const error = ref(null)

const route = useRoute()
const currentUser = ref(null)
const API_BASE_URL = config.public.apiBaseUrl
const { connect, subscribe, unsubscribe, isConnected } = useWebSocket()
const { fetchUnreadCount: refreshGlobalUnreadCount } = useUnreadCount()
const { fetchChannelUnread: refreshChannelUnread, setFromList: setChannelUnreadFromList } =
  useChannelsUnreadCount()

const activeTab = ref('channels')
const tabs = [
  { key: 'messages', label: 'Direct Messages' },
  { key: 'channels', label: 'Channels' },
]
const channels = ref([])
const loadingChannels = ref(false)
const isFloatMode = computed(() => route.query.float === '1')
const floatRoute = useState('messageFloatRoute')

async function fetchConversations() {
  const token = getToken()
  if (!token) {
    toast.error('Please log in first.')
    return
  }
  loading.value = true
  try {
    const response = await fetch(`${API_BASE_URL}/api/messages/conversations`, {
      method: 'GET',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    const data = await response.json()
    conversations.value = data
  } catch (e) {
    error.value = 'Unable to load conversations.'
  } finally {
    loading.value = false
  }
}

// Get the other participant in a direct conversation.
function getOtherParticipant(conversation) {
  if (!currentUser.value || !conversation.participants) return null
  return conversation.participants.find((p) => p.id !== currentUser.value.id)
}

// Format display time.
function formatTime(timeString) {
  if (!timeString) return ''
  return TimeManager.format(timeString)
}

// Handle avatar loading failures.
function handleAvatarError(event) {
  event.target.src = null
}

async function fetchChannels() {
  const token = getToken()
  if (!token) {
    toast.error('Please log in first.')
    return
  }
  loadingChannels.value = true
  try {
    const response = await fetch(`${API_BASE_URL}/api/channels`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!response.ok) throw new Error('Unable to load channels')
    const data = await response.json()
    channels.value = data
    setChannelUnreadFromList(data)
  } catch (e) {
    toast.error(e.message)
  } finally {
    loadingChannels.value = false
  }
}

watch(activeTab, (tab) => {
  if (tab === 'messages') {
    fetchConversations()
  } else {
    fetchChannels()
  }
})

async function goToChannel(id) {
  const token = getToken()
  if (!token) {
    toast.error('Please log in first.')
    return
  }
  try {
    await fetch(`${API_BASE_URL}/api/channels/${id}/join`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (isFloatMode.value) {
      navigateTo(`/message-box/${id}?float=1`)
    } else {
      navigateTo(`/message-box/${id}`)
    }
  } catch (e) {
    toast.error(e.message)
  }
}

onActivated(async () => {
  currentUser.value = await fetchCurrentUser()

  if (currentUser.value) {
    if (activeTab.value === 'messages') {
      await fetchConversations()
    } else {
      await fetchChannels()
    }
    refreshGlobalUnreadCount()
    refreshChannelUnread()
    const token = getToken()
    if (token) {
      if (isConnected.value) {
        // If already connected, resubscribe because component cleanup may have removed the subscription.
        subscribeToUserMessages()
      } else {
        // If disconnected, connect first; the watcher will subscribe after connection succeeds.
        connect(token)
      }
    }
  } else {
    loading.value = false
  }
})

const subscribeToUserMessages = () => {
  if (!currentUser.value) return
  const destination = `/topic/user/${currentUser.value.id}/messages`

  subscribe(destination, (message) => {
    if (activeTab.value === 'messages') {
      fetchConversations()
    }
    fetchChannels()
    refreshGlobalUnreadCount()
    refreshChannelUnread()
  })
}

watch(isConnected, (newValue) => {
  if (newValue) {
    subscribeToUserMessages()
  }
})

onDeactivated(() => {
  if (currentUser.value) {
    const destination = `/topic/user/${currentUser.value.id}/messages`
    unsubscribe(destination)
  }
})

function goToConversation(id) {
  if (isFloatMode.value) {
    navigateTo(`/message-box/${id}?float=1`)
  } else {
    navigateTo(`/message-box/${id}`)
  }
}

function minimize() {
  floatRoute.value = route.fullPath
  navigateTo('/')
}
</script>

<style scoped>
.messages-container {
  position: relative;
  width: min(900px, calc(100% - 40px));
  margin: 0 auto;
  padding: 44px 0 68px;
  color: #2d424c;
}
.messages-container.float { width: 100%; padding: 0; }

.float-control {
  position: absolute;
  top: 0;
  right: 0;
  text-align: right;
  padding: 12px 12px;
}

.float-control i {
  cursor: pointer;
}

:deep(.base-tabs-header) {
  display: flex;
  border-bottom: 4px solid #009edb;
  margin-bottom: 16px;
}

:deep(.base-tabs-item) {
  min-height: 42px;
  padding: 0 18px;
  cursor: pointer;
}

:deep(.base-tabs-item.selected) {
  color: #fff;
  background: #0065a8;
}

.loading-message {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 300px;
}

.search-container {
  margin-bottom: 24px;
  margin-left: 20px;
  margin-right: 20px;
}

.messages-header {
  margin-bottom: 24px;
}

.page-title {
  display: block;
  margin-bottom: 20px;
  padding: 0 0 20px;
  border-bottom: 1px solid #c7d1d5;
}
.page-title p { margin: 0 0 6px; color: #176582; font-size: 11px; font-weight: 800; letter-spacing: .1em; }
.page-title h1 { margin: 0 0 7px; font-family: Georgia, 'Times New Roman', serif; font-size: 38px; font-weight: 400; }
.page-title span { color: #607078; font-size: 14px; }

.messages-title {
  font-size: 28px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
}

.loading-container,
.error-container,
.empty-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

.loading-text,
.error-text,
.empty-text {
  font-size: 16px;
  color: #666;
}

.error-text {
  color: #e53e3e;
}

.conversations-list {
}

.conversation-item {
  display: flex;
  align-items: center;
  margin: 0;
  padding: 13px 12px;
  border-bottom: 1px solid #d6dfe2;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.conversation-item:hover {
  background: #eef4f5;
}

.conversation-avatar {
  flex-shrink: 0;
  margin-right: 12px;
}

.avatar-img {
  width: 40px;
  height: 40px;
  border-radius: 50%;
}

.avatar-img :deep(.base-user-avatar-img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.conversation-content {
  flex: 1;
  min-width: 0;
}

.conversation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.participant-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-color);
}

.member-count {
  font-size: 12px;
  color: gray;
  flex-shrink: 0;
}

.message-time {
  font-size: 12px;
  color: gray;
  flex-shrink: 0;
  margin-left: 12px;
}

.last-message-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.last-message {
  font-size: 14px;
  color: gray;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex-grow: 1;
  padding-right: 10px; /* Add some space between message and badge */
}

.unread-count-badge {
  background: #0065a8;
  color: white;
  font-size: 12px;
  font-weight: bold;
  padding: 2px 8px;
  border-radius: 0;
  line-height: 1.5;
  flex-shrink: 0;
}

.unread-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  background-color: #f56c6c;
  border-radius: 50%;
  margin-left: 4px;
}

@media (max-height: 200px) {
  .page-title {
    display: block;
  }

  :deep(.base-tabs-header),
  .loading-message,
  .error-container,
  .search-container,
  .empty-container,
  .conversation-item {
    display: none;
  }
}

@media (max-width: 768px) {
  .messages-container { width: min(100% - 28px, 900px); padding-top: 28px; }
  .conversation-item {
    margin-left: 10px;
    margin-right: 10px;
  }

  .messages-title {
    font-size: 24px;
  }

  .conversations-list {
    max-height: 500px;
  }

  .conversation-item {
    padding: 6px 8px;
  }

  .avatar-img {
    width: 40px;
    height: 40px;
  }

  .participant-name {
    font-size: 15px;
  }

  .message-time {
    font-size: 11px;
  }

  .last-message {
    font-size: 13px;
  }
}
</style>
