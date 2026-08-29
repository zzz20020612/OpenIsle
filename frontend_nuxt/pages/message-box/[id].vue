<template>
  <div class="chat-container" :class="{ float: isFloatMode }">
    <vue-easy-lightbox
      :visible="lightboxVisible"
      :index="lightboxIndex"
      :imgs="lightboxImgs"
      @hide="lightboxVisible = false"
    />
    <div v-if="!loading" class="chat-header">
      <div class="header-main">
        <div class="back-button" @click="goBack">
          <arrow-left />
        </div>
        <h2 class="participant-name">
          {{ isChannel ? conversationName : otherParticipant?.username }}
        </h2>
      </div>
      <div v-if="!isFloatMode" class="float-control">
        <collapse-text-input class="float-control-icon" @click="minimize" title="Minimize" />
      </div>
    </div>

    <div class="messages-list" ref="messagesListEl">
      <div v-if="loading" class="loading-container">
        <l-hatch size="28" stroke="4" speed="3.5" color="var(--primary-color)"></l-hatch>
      </div>
      <div v-else-if="error" class="error-container">{{ error }}</div>
      <template v-else>
        <div class="load-more-container" v-if="hasMoreMessages">
          <div @click="loadMoreMessages" :disabled="loadingMore" class="load-more-button">
            {{ loadingMore ? 'Loading...' : 'Load more messages' }}
          </div>
        </div>
        <BaseTimeline :items="messages">
          <template #item="{ item }">
            <div class="message-header">
              <div class="user-name">
                {{ item.sender.username }}
              </div>
              <div class="message-timestamp">
                {{ TimeManager.format(item.createdAt) }}
              </div>
            </div>
            <div v-if="item.replyTo" class="reply-preview info-content-text">
              <div class="reply-header">
                <next class="reply-icon" />
                <BaseUserAvatar
                  class="reply-avatar"
                  :src="item.replyTo.sender.avatar"
                  :user-id="item.replyTo.sender.id"
                  :alt="item.replyTo.sender.username"
                />
                <div class="reply-author">{{ item.replyTo.sender.username }}:</div>
              </div>
              <div class="reply-content" v-html="renderMarkdown(item.replyTo.content)"></div>
            </div>
            <div class="message-content">
              <div
                class="info-content-text"
                v-html="renderMarkdown(item.content)"
                @click="handleContentClick"
              ></div>
            </div>
            <div class="message-reaction-row">
              <ReactionsGroup
                :ref="(el) => setMessageReactionRef(item.id, el)"
                :model-value="item.reactions"
                content-type="message"
                :content-id="item.id"
                @update:modelValue="(v) => (item.reactions = v)"
              />
              <div class="message-reaction-actions">
                <div
                  class="reaction-action like-action"
                  :class="{ selected: isMessageLiked(item) }"
                  @click="toggleMessageLike(item)"
                >
                  <like v-if="!isMessageLiked(item)" />
                  <like v-else theme="filled" />
                  <span v-if="getMessageLikeCount(item)" class="reaction-count">{{
                    getMessageLikeCount(item)
                  }}</span>
                </div>
                <div @click="setReply(item)" class="reaction-action reply-btn">
                  <next /> Write a reply...
                </div>
              </div>
            </div>
          </template>
        </BaseTimeline>
        <div class="empty-container">
          <BasePlaceholder
            v-if="messages.length === 0"
            text="No messages yet. Send the first one."
            icon="inbox"
          />
        </div>
      </template>
    </div>

    <div class="message-input-area">
      <div
        v-if="newMessagesCount > 0 && !isUserNearBottom"
        class="new-message-container"
        @click="handleScrollToBottom"
      >
        <double-down />
        <div class="new-message-count">{{ newMessagesCount }} new messages</div>
      </div>

      <div v-if="replyTo" class="active-reply">
        Replying to {{ replyTo.sender.username }}:
        {{ stripMarkdownLength(replyTo.content, 50) }}
        <close-icon class="close-reply" @click="replyTo = null" />
      </div>

      <MessageEditor :loading="sending" @submit="sendMessage" />
    </div>
  </div>
</template>

<script setup>
import {
  ref,
  onMounted,
  onUnmounted,
  nextTick,
  computed,
  watch,
  onActivated,
  onDeactivated,
} from 'vue'
import { useRoute } from 'vue-router'
import { getToken, fetchCurrentUser } from '~/utils/auth'
import { toast } from '~/main'
import { renderMarkdown, stripMarkdownLength, handleMarkdownClick } from '~/utils/markdown'
import MessageEditor from '~/components/MessageEditor.vue'
import ReactionsGroup from '~/components/ReactionsGroup.vue'
import { useWebSocket } from '~/composables/useWebSocket'
import { useUnreadCount } from '~/composables/useUnreadCount'
import { useChannelsUnreadCount } from '~/composables/useChannelsUnreadCount'
import TimeManager from '~/utils/time'
import BaseTimeline from '~/components/BaseTimeline.vue'
import BasePlaceholder from '~/components/BasePlaceholder.vue'
import VueEasyLightbox from 'vue-easy-lightbox'
import BaseUserAvatar from '~/components/BaseUserAvatar.vue'

const config = useRuntimeConfig()
const route = useRoute()
const API_BASE_URL = config.public.apiBaseUrl
const { connect, subscribe, unsubscribe, isConnected } = useWebSocket()
const { fetchUnreadCount: refreshGlobalUnreadCount } = useUnreadCount()
const { fetchChannelUnread: refreshChannelUnread } = useChannelsUnreadCount()

const messages = ref([])
const participants = ref([])
const loading = ref(true)
const sending = ref(false)
const error = ref(null)
const conversationId = route.params.id
const currentUser = ref(null)
const messagesListEl = ref(null)
const currentPage = ref(0)
const totalPages = ref(0)
const loadingMore = ref(false)
const conversationName = ref('')
const isChannel = ref(false)
const isFloatMode = computed(() => route.query.float !== undefined)
const floatRoute = useState('messageFloatRoute')
const replyTo = ref(null)
const newMessagesCount = ref(0)
const lightboxVisible = ref(false)
const lightboxIndex = ref(0)
const lightboxImgs = ref([])

const isUserNearBottom = ref(true)
function updateNearBottom() {
  const el = messagesListEl.value
  if (!el) return
  const threshold = 40 // px
  isUserNearBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight <= threshold
  if (isUserNearBottom.value) {
    newMessagesCount.value = 0
  }
}

const hasMoreMessages = computed(() => currentPage.value < totalPages.value - 1)

const otherParticipant = computed(() => {
  if (isChannel.value || !currentUser.value || participants.value.length === 0) {
    return null
  }
  return participants.value.find((p) => p.id !== currentUser.value.id)
})

function setReply(message) {
  replyTo.value = message
}

const messageReactionRefs = new Map()
function setMessageReactionRef(id, el) {
  if (el) {
    messageReactionRefs.set(id, el)
  } else {
    messageReactionRefs.delete(id)
  }
}

function getMessageLikeCount(message) {
  return (message.reactions || []).filter((reaction) => reaction.type === 'LIKE').length
}

function isMessageLiked(message) {
  const username = currentUser.value?.username
  if (!username) return false
  return (message.reactions || []).some(
    (reaction) => reaction.type === 'LIKE' && reaction.user === username,
  )
}

function toggleMessageLike(message) {
  const group = messageReactionRefs.get(message.id)
  group?.toggleReaction('LIKE')
}

/** Scroll helpers: smooth and instant modes. */
function scrollToBottomSmooth() {
  const el = messagesListEl.value
  if (!el) return
  // Prefer native smooth scrolling and fall back when unavailable.
  try {
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  } catch {
    // Fallback: lightweight animation.
    const start = el.scrollTop
    const end = el.scrollHeight
    const duration = 200
    const startTs = performance.now()
    function step(now) {
      const p = Math.min(1, (now - startTs) / duration)
      el.scrollTop = start + (end - start) * p
      if (p < 1) requestAnimationFrame(step)
    }
    requestAnimationFrame(step)
  }
}

function scrollToBottomInstant() {
  const el = messagesListEl.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

function handleScrollToBottom() {
  scrollToBottomSmooth()
  newMessagesCount.value = 0
}

async function fetchMessages(page = 0) {
  if (page === 0) {
    loading.value = true
    messages.value = []
  } else {
    loadingMore.value = true
  }
  error.value = null
  const token = getToken()
  if (!token) {
    toast.error('Please log in first.')
    loading.value = false
    return
  }

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/messages/conversations/${conversationId}?page=${page}&size=20`,
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    )
    if (!response.ok) throw new Error('Unable to load messages')

    const conversationData = await response.json()
    const pageData = conversationData.messages

    if (page === 0) {
      participants.value = conversationData.participants
      conversationName.value = conversationData.name
      isChannel.value = conversationData.channel
    }

    const newMessages = pageData.content.reverse().map((item) => ({
      ...item,
      src: item.sender.avatar,
      userId: item.sender.id,
      iconClick: () => {
        openUser(item.sender.id)
      },
    }))

    const list = messagesListEl.value
    const oldScrollHeight = list ? list.scrollHeight : 0

    if (page === 0) {
      messages.value = newMessages
    } else {
      messages.value = [...newMessages, ...messages.value]
    }

    currentPage.value = pageData.number
    totalPages.value = pageData.totalPages

    await nextTick()
    if (page > 0 && list) {
      // Loading older messages: preserve the current viewport position.
      const newScrollHeight = list.scrollHeight
      list.scrollTop = newScrollHeight - oldScrollHeight
    } else if (page === 0) {
      // First load: jump to the bottom without animation.
      scrollToBottomInstant()
    }
    updateNearBottom()
  } catch (e) {
    error.value = e.message
    toast.error(e.message)
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

async function loadMoreMessages() {
  if (hasMoreMessages.value && !loadingMore.value) {
    await fetchMessages(currentPage.value + 1)
  }
}

async function sendMessage(content, clearInput) {
  if (!content.trim()) return
  sending.value = true
  const token = getToken()
  try {
    let response
    if (isChannel.value) {
      response = await fetch(
        `${API_BASE_URL}/api/messages/conversations/${conversationId}/messages`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ content, replyToId: replyTo.value?.id }),
        },
      )
    } else {
      const recipient = otherParticipant.value
      if (!recipient) {
        toast.error('Unable to identify the recipient')
        return
      }
      response = await fetch(`${API_BASE_URL}/api/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          recipientId: recipient.id,
          content: content,
          replyToId: replyTo.value?.id,
        }),
      })
    }
    if (!response.ok) throw new Error('Failed to send message')

    const newMessage = await response.json()
    messages.value.push({
      ...newMessage,
      src: newMessage.sender.avatar,
      userId: newMessage.sender.id,
      iconClick: () => {
        openUser(newMessage.sender.id)
      },
    })
    clearInput()
    replyTo.value = null

    await nextTick()
    // Smooth scroll only after a message is sent successfully.
    scrollToBottomSmooth()
    newMessagesCount.value = 0
  } catch (e) {
    toast.error(e.message)
  } finally {
    sending.value = false
  }
}

async function markConversationAsRead() {
  const token = getToken()
  if (!token) return
  try {
    await fetch(`${API_BASE_URL}/api/messages/conversations/${conversationId}/read`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })
    refreshGlobalUnreadCount()
    refreshChannelUnread()
  } catch (e) {
    console.error('Failed to mark conversation as read', e)
  }
}

onMounted(async () => {
  // Track whether the user is near the bottom while scrolling.
  if (messagesListEl.value) {
    messagesListEl.value.addEventListener('scroll', updateNearBottom, { passive: true })
  }

  currentUser.value = await fetchCurrentUser()
  if (currentUser.value) {
    await fetchMessages(0)
    await markConversationAsRead()
    await nextTick()
    // On first channel entry, scroll to the bottom.
    scrollToBottomSmooth()
    const token = getToken()
    if (token) {
      if (isConnected.value) {
        subscribeToConversation()
      } else {
        connect(token)
      }
    }
  } else {
    toast.error('Please log in first.')
    loading.value = false
  }
})

const subscribeToConversation = () => {
  if (!currentUser.value) return
  const destination = `/topic/conversation/${conversationId}`

  subscribe(destination, async (message) => {
    try {
      const parsedMessage = JSON.parse(message.body)

      if (parsedMessage?.eventType === 'MESSAGE_REACTION') {
        applyMessageReactionSync(parsedMessage)
        return
      }

      if (parsedMessage.sender && parsedMessage.sender.id === currentUser.value.id) {
        return
      }

      messages.value.push({
        ...parsedMessage,
        src: parsedMessage.sender.avatar,
        userId: parsedMessage.sender.id,
        iconClick: () => openUser(parsedMessage.sender.id),
      })

      await markConversationAsRead()
      await nextTick()

      if (isUserNearBottom.value) {
        scrollToBottomSmooth()
      } else {
        newMessagesCount.value += 1
      }
    } catch (e) {
      console.error('Failed to parse websocket message', e)
    }
  })
}

function applyMessageReactionSync(event) {
  const targetMessageId = Number(event?.messageId)
  if (!Number.isFinite(targetMessageId)) return

  const targetMessage = messages.value.find((msg) => Number(msg.id) === targetMessageId)
  if (!targetMessage) return

  if (!Array.isArray(targetMessage.reactions)) {
    targetMessage.reactions = []
  }

  const reaction = event?.reaction
  if (!reaction?.type || !reaction?.user) return

  const sameReaction = (current) => current?.type === reaction.type && current?.user === reaction.user
  if (event.action === 'REMOVED') {
    targetMessage.reactions = targetMessage.reactions.filter((current) => !sameReaction(current))
    return
  }

  if (event.action === 'ADDED') {
    const existingIndex = targetMessage.reactions.findIndex((current) => sameReaction(current))
    if (existingIndex > -1) {
      targetMessage.reactions.splice(existingIndex, 1, reaction)
    } else {
      targetMessage.reactions.push(reaction)
    }
  }
}

watch(isConnected, (newValue) => {
  if (newValue) {
    subscribeToConversation()
  }
})

onActivated(async () => {
  // When returning to the page, refresh data, mark read, and scroll down.
  if (currentUser.value) {
    await fetchMessages(0)
    await markConversationAsRead()
    await nextTick()
    scrollToBottomSmooth()
    updateNearBottom()

    if (isConnected.value) {
      // If already connected, resubscribe.
      subscribeToConversation()
    } else {
      // If disconnected, connect first.
      const token = getToken()
      if (token) connect(token)
    }
  }
})

onDeactivated(() => {
  const destination = `/topic/conversation/${conversationId}`
  unsubscribe(destination)
})

onUnmounted(() => {
  const destination = `/topic/conversation/${conversationId}`
  unsubscribe(destination)

  if (messagesListEl.value) {
    messagesListEl.value.removeEventListener('scroll', updateNearBottom)
  }
})

function minimize() {
  floatRoute.value = route.fullPath
  navigateTo('/')
}

function handleContentClick(e) {
  handleMarkdownClick(e)
  if (e.target.tagName === 'IMG' && !e.target.classList.contains('emoji')) {
    const container = e.target.parentNode
    const imgs = [...container.querySelectorAll('img')].map((i) => i.src)
    lightboxImgs.value = imgs
    lightboxIndex.value = imgs.indexOf(e.target.src)
    lightboxVisible.value = true
  }
}

function openUser(id) {
  if (isFloatMode.value) {
    // No-op for now.
    // navigateTo(`/users/${id}?float=1`)
  } else {
    navigateTo(`/users/${id}`, { replace: true })
  }
}

function goBack() {
  if (isFloatMode.value) {
    navigateTo('/message-box?float=1')
  } else {
    navigateTo('/message-box')
  }
}
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  width: min(920px, 100%);
  margin: 0 auto;
  border-left: 1px solid #d2dade;
  border-right: 1px solid #d2dade;
  overflow: auto;
  height: calc(100vh - var(--header-height));
  position: relative;
}

.chat-container.float {
  height: 100vh;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 100;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 4px solid #009edb;
  background: #fff;
}

.header-main {
  display: flex;
  align-items: center;
}

.float-control {
  position: absolute;
  top: 0;
  right: 0;
  text-align: right;
  padding: 12px 12px;
  cursor: pointer;
}

.float-control i {
  cursor: pointer;
}

.back-button {
  font-size: 18px;
  color: var(--text-color-primary);
  margin-right: 15px;
  cursor: pointer;
}

.participant-name {
  color: #29424e;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 21px;
  font-weight: 400;
  margin: 0;
}

.messages-list {
  overflow-y: auto;
  overflow-x: hidden;
  padding: 20px;
  padding-bottom: 100px;
  display: flex;
  flex-direction: column;
  margin-bottom: 10px;
}

.load-more-container {
  text-align: center;
}

.load-more-button {
  color: var(--primary-color);
  font-size: 12px;
  cursor: pointer;
}

.load-more-button:hover {
  text-decoration: underline;
}

.message-item {
  display: flex;
  gap: 10px;
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  align-self: flex-end;
}

.message-content {
  display: flex;
  flex-direction: column;
}

.message-timestamp {
  font-size: 11px;
  color: var(--text-color-secondary);
  opacity: 0.6;
}

.message-header {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
}

.new-message-container {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  border: 1px solid var(--normal-border-color);
  border-radius: 0;
  padding: 3px 6px;
  box-shadow: 0 7px 18px rgba(31,57,69,.12);
  width: fit-content;
  position: absolute;
  bottom: calc(100% + 20px);
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  background-color: var(--background-color);
}

.user-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-color);
}

.message-item.sent {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-item.sent .message-timestamp {
  text-align: right;
}

/* Received messages */
.message-item.received {
  align-self: flex-start;
}

.message-item.received .message-content {
  align-items: flex-start;
}

.message-item.received .message-bubble {
  background-color: var(--bg-color-soft);
  border: 1px solid var(--border-color);
  border-bottom-left-radius: 4px;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 300px;
}

.error-container {
  text-align: center;
  padding: 50px;
  color: var(--text-color-secondary);
}

.message-input-area {
  margin-left: 10px;
  margin-right: 10px;
  position: relative;
}

.reply-icon {
  color: var(--primary-color);
  margin-right: 5px;
}

.reply-avatar {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  margin-right: 5px;
}

.reply-avatar :deep(.base-user-avatar-img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.reply-preview {
  margin-top: 10px;
  padding: 10px;
  border-left: 4px solid #009edb;
  margin-bottom: 5px;
  font-size: 13px;
  background-color: var(--normal-light-background-color);
}

.message-reaction-row {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 6px;
}

.message-reaction-actions {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
}

.reaction-action {
  cursor: pointer;
  padding: 4px 10px;
  border-radius: 0;
  display: flex;
  align-items: center;
  gap: 5px;
  opacity: 0.6;
  font-size: 16px;
  transition:
    background-color 0.2s ease,
    opacity 0.2s ease;
}

.reaction-action:hover {
  opacity: 1;
  background-color: var(--normal-light-background-color);
}

.reaction-action.like-action {
  color: #ff0000;
}

.reaction-action.selected {
  opacity: 1;
  background-color: var(--normal-light-background-color);
}

.reaction-count {
  font-size: 14px;
  font-weight: bold;
}

.reply-header {
  display: flex;
  flex-direction: row;
  align-items: center;
}

.reply-author {
  font-weight: bold;
  margin-bottom: 2px;
  opacity: 0.5;
}

.reply-btn {
  font-size: 12px;
  color: var(--primary-color);
}

.active-reply {
  background-color: var(--normal-light-background-color);
  padding: 5px 10px;
  border-left: 4px solid #009edb;
  margin-bottom: 5px;
  font-size: 13px;
}

.close-reply {
  margin-left: 8px;
  cursor: pointer;
}

@media (max-height: 200px) {
  .messages-list,
  .message-input-area {
    display: none;
  }
}

@media (max-width: 768px) {
  .messages-list {
    padding: 10px;
  }
}
</style>
