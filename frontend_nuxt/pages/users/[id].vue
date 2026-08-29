<template>
  <div class="profile-page">
    <div v-if="isLoading" class="loading-page">
      <l-hatch size="28" stroke="4" speed="3.5" color="var(--primary-color)" />
    </div>

    <div v-else>
      <header class="profile-page-header">
        <BaseUserAvatar
          :src="user.avatar"
          :user-id="user.id"
          alt="avatar"
          class="profile-page-header-avatar-img"
        />
        <div class="profile-page-header-user-info">
          <h1 class="profile-page-header-user-info-name">{{ user.username }}</h1>
          <p class="profile-page-header-user-info-description">
            {{ user.introduction || 'No profile summary yet.' }}
          </p>
          <div class="profile-page-header-user-info-buttons">
            <button
              v-if="!isMine && !subscribed"
              class="profile-page-header-subscribe-button"
              type="button"
              @click="subscribeUser"
            >
              <add-user />
              Follow
            </button>
            <button
              v-if="!isMine && subscribed"
              class="profile-page-header-unsubscribe-button"
              type="button"
              @click="unsubscribeUser"
            >
              <reduce-user />
              Unfollow
            </button>
            <button
              v-if="!isMine"
              class="profile-page-header-send-mail-button"
              type="button"
              @click="sendMessage"
            >
              <message-one />
              Message
            </button>
          </div>
        </div>
      </header>

      <section class="profile-info">
        <div class="profile-info-item">
          <span class="profile-info-item-label">Joined</span>
          <strong class="profile-info-item-value">{{ formatDate(user.createdAt) }}</strong>
        </div>
        <div class="profile-info-item">
          <span class="profile-info-item-label">Latest paper activity</span>
          <strong class="profile-info-item-value">
            {{ user.lastPostTime ? formatDate(user.lastPostTime) : 'No records yet' }}
          </strong>
        </div>
        <div class="profile-info-item">
          <span class="profile-info-item-label">Latest discussion</span>
          <strong class="profile-info-item-value">
            {{ user.lastCommentTime ? formatDate(user.lastCommentTime) : 'No discussion yet' }}
          </strong>
        </div>
        <div class="profile-info-item">
          <span class="profile-info-item-label">Views</span>
          <strong class="profile-info-item-value">{{ user.totalViews || 0 }}</strong>
        </div>
      </section>

      <BaseTabs v-model="selectedTab" :tabs="tabs">
        <div v-if="tabLoading" class="tab-loading">
          <l-hatch size="28" stroke="4" speed="3.5" color="var(--primary-color)" />
        </div>
        <template v-else>
          <section v-if="selectedTab === 'summary'" class="profile-summary">
            <div class="total-summary">
              <h2 class="summary-title">Statistics</h2>
              <div class="total-summary-content">
                <div class="total-summary-item">
                  <span class="total-summary-item-label">Active days</span>
                  <strong class="total-summary-item-value">{{ user.visitedDays || 0 }}</strong>
                </div>
                <div class="total-summary-item">
                  <span class="total-summary-item-label">Read records</span>
                  <strong class="total-summary-item-value">{{ user.readPosts || 0 }}</strong>
                </div>
                <div class="total-summary-item">
                  <span class="total-summary-item-label">Reactions sent</span>
                  <strong class="total-summary-item-value">{{ user.likesSent || 0 }}</strong>
                </div>
                <div class="total-summary-item">
                  <span class="total-summary-item-label">Reactions received</span>
                  <strong class="total-summary-item-value">{{ user.likesReceived || 0 }}</strong>
                </div>
              </div>
            </div>

            <div class="summary-divider">
              <div class="hot-reply">
                <h2 class="summary-title">Popular replies</h2>
                <BaseTimeline v-if="hotReplies.length > 0" :items="hotReplies">
                  <template #item="{ item }">
                    <NuxtLink :to="recordLink(item.comment.post)" class="timeline-link">
                      {{ item.comment.post.title }}
                    </NuxtLink>
                    <template v-if="item.comment.parentComment">
                      <NuxtLink
                        :to="commentLink(item.comment.post, item.comment.parentComment.id)"
                        class="timeline-comment-link"
                      >
                        {{ stripMarkdownLength(item.comment.parentComment.content, 200) }}
                      </NuxtLink>
                      <next class="reply-icon" />
                      replied with
                    </template>
                    <template v-else> commented with </template>
                    <NuxtLink
                      :to="commentLink(item.comment.post, item.comment.id)"
                      class="timeline-comment-link"
                    >
                      {{ stripMarkdownLength(item.comment.content, 200) }}
                    </NuxtLink>
                    <div class="timeline-date">{{ formatDate(item.comment.createdAt) }}</div>
                  </template>
                </BaseTimeline>
                <div v-else class="summary-empty">No popular replies yet.</div>
              </div>

              <div class="hot-topic">
                <h2 class="summary-title">Popular records</h2>
                <BaseTimeline v-if="hotPosts.length > 0" :items="hotPosts">
                  <template #item="{ item }">
                    <TimelinePostItem :item="item" />
                  </template>
                </BaseTimeline>
                <div v-else class="summary-empty">No popular records yet.</div>
              </div>

              <div class="hot-tag">
                <h2 class="summary-title">Created tags</h2>
                <BaseTimeline v-if="hotTags.length > 0" :items="hotTags">
                  <template #item="{ item }">
                    <TimelineTagItem :item="item" />
                  </template>
                </BaseTimeline>
                <div v-else class="summary-empty">No created tags yet.</div>
              </div>
            </div>
          </section>

          <section v-else-if="selectedTab === 'timeline'" class="profile-timeline">
            <div class="timeline-tabs">
              <button
                :class="['timeline-tab-item', { selected: timelineFilter === 'all' }]"
                type="button"
                @click="timelineFilter = 'all'"
              >
                All
              </button>
              <button
                :class="['timeline-tab-item', { selected: timelineFilter === 'articles' }]"
                type="button"
                @click="timelineFilter = 'articles'"
              >
                Records
              </button>
              <button
                :class="['timeline-tab-item', { selected: timelineFilter === 'comments' }]"
                type="button"
                @click="timelineFilter = 'comments'"
              >
                Discussions
              </button>
              <button
                v-if="isMine"
                :class="['timeline-tab-item', { selected: timelineFilter === 'reads' }]"
                type="button"
                @click="timelineFilter = 'reads'"
              >
                Reading history
              </button>
            </div>
            <BasePlaceholder
              v-if="
                timelineFilter === 'reads'
                  ? readPosts.length === 0
                  : filteredTimelineItems.length === 0
              "
              :text="timelineFilter === 'reads' ? 'No reading history yet.' : 'No activity yet.'"
              icon="inbox"
            />
            <div class="timeline-list">
              <BaseTimeline v-if="timelineFilter !== 'reads'" :items="filteredTimelineItems">
                <template #item="{ item }">
                  <TimelinePostItem v-if="item.type === 'post'" :item="item" />
                  <TimelineCommentGroup
                    v-else-if="item.type === 'comment' || item.type === 'reply'"
                    :item="item"
                  />
                  <TimelineTagItem v-else-if="item.type === 'tag'" :item="item" />
                </template>
              </BaseTimeline>
              <BaseTimeline v-else :items="readPosts">
                <template #item="{ item }">
                  <TimelineReadItem :item="item" />
                </template>
              </BaseTimeline>
            </div>
          </section>

          <section v-else-if="selectedTab === 'following'" class="follow-container">
            <div class="follow-tabs">
              <button
                :class="['follow-tab-item', { selected: followTab === 'followers' }]"
                type="button"
                @click="followTab = 'followers'"
              >
                Followers
              </button>
              <button
                :class="['follow-tab-item', { selected: followTab === 'following' }]"
                type="button"
                @click="followTab = 'following'"
              >
                Following
              </button>
            </div>
            <div class="follow-list">
              <UserList v-if="followTab === 'followers'" :users="followers" />
              <UserList v-else :users="followings" />
            </div>
          </section>

          <section v-else-if="selectedTab === 'favorites'" class="favorites-container">
            <BaseTimeline v-if="favoritePosts.length > 0" :items="favoritePosts">
              <template #item="{ item }">
                <NuxtLink :to="recordLink(item.post)" class="timeline-link">
                  {{ item.post.title }}
                </NuxtLink>
                <div class="timeline-snippet">{{ stripMarkdown(item.post.snippet) }}</div>
                <div class="timeline-date">{{ formatDate(item.post.createdAt) }}</div>
              </template>
            </BaseTimeline>
            <BasePlaceholder v-else text="No followed records yet." icon="inbox" />
          </section>

        </template>
      </BaseTabs>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import BasePlaceholder from '~/components/BasePlaceholder.vue'
import BaseTimeline from '~/components/BaseTimeline.vue'
import BaseTabs from '~/components/BaseTabs.vue'
import TimelineCommentGroup from '~/components/TimelineCommentGroup.vue'
import TimelinePostItem from '~/components/TimelinePostItem.vue'
import TimelineReadItem from '~/components/TimelineReadItem.vue'
import TimelineTagItem from '~/components/TimelineTagItem.vue'
import BaseUserAvatar from '~/components/BaseUserAvatar.vue'
import UserList from '~/components/UserList.vue'
import { toast } from '~/main'
import { authState, getToken } from '~/utils/auth'
import { stripMarkdown, stripMarkdownLength } from '~/utils/markdown'
import TimeManager from '~/utils/time'

const config = useRuntimeConfig()
const route = useRoute()
const API_BASE_URL = config.public.apiBaseUrl
const username = computed(() => String(route.params.id || ''))
const user = ref({})

definePageMeta({
  alias: ['/users/:id/'],
  keepalive: false,
  key: (route) => route.fullPath,
})

useHead(() => ({
  title: `${user.value.username || 'Profile'} - Open Research Evaluation`,
}))

const hotPosts = ref([])
const hotReplies = ref([])
const hotTags = ref([])
const favoritePosts = ref([])
const timelineItems = ref([])
const readPosts = ref([])
const timelineFilter = ref('all')
const followers = ref([])
const followings = ref([])
const subscribed = ref(false)
const isLoading = ref(true)
const tabLoading = ref(false)
const followTab = ref('followers')
const selectedTab = ref(
  ['summary', 'timeline', 'following', 'favorites'].includes(route.query.tab)
    ? route.query.tab
    : 'summary',
)

const tabs = [
  { key: 'summary', label: 'Summary', icon: 'chart-line' },
  { key: 'timeline', label: 'Timeline', icon: 'alarm-clock' },
  { key: 'following', label: 'Network', icon: 'add-user' },
  { key: 'favorites', label: 'Following', icon: 'bookmark' },
]

const requestController = new AbortController()
const isAbortError = (error) => error?.name === 'AbortError'
const redirectingTo404 = ref(false)

onBeforeUnmount(() => {
  requestController.abort()
})

const profileFetch = async (path, options = {}) => {
  try {
    return await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      signal: requestController.signal,
    })
  } catch (error) {
    if (isAbortError(error)) return null
    throw error
  }
}

const filteredTimelineItems = computed(() => {
  if (timelineFilter.value === 'articles') {
    return timelineItems.value.filter((item) => item.type === 'post')
  }
  if (timelineFilter.value === 'comments') {
    return timelineItems.value.filter((item) => item.type === 'comment' || item.type === 'reply')
  }
  if (timelineFilter.value === 'reads') return []
  return timelineItems.value
})

const isMine = computed(
  () => authState.username === username.value || String(authState.userId) === username.value,
)
const formatDate = (date) => (date ? TimeManager.format(date) : '')
const recordLink = (post) => {
  if (post?.paperId) return `/papers/${post.paperId}`
  if (post?.type === 'PAPER') return '#'
  return post?.id ? `/posts/${post.id}` : '#'
}
const commentLink = (post, commentId) => {
  const base = recordLink(post)
  return commentId ? `${base}#comment-${commentId}` : base
}

const fetchUser = async () => {
  const token = getToken()
  const headers = token ? { Authorization: `Bearer ${token}` } : {}
  const res = await profileFetch(`/api/users/${username.value}`, { headers })
  if (res?.ok) {
    const data = await res.json()
    user.value = data
    subscribed.value = Boolean(data.subscribed)
  } else if (res?.status === 404) {
    redirectingTo404.value = true
    await navigateTo('/404', { replace: true })
  }
}

const fetchSummary = async () => {
  const [postsRes, repliesRes, tagsRes] = await Promise.all([
    profileFetch(`/api/users/${username.value}/hot-posts`),
    profileFetch(`/api/users/${username.value}/hot-replies`),
    profileFetch(`/api/users/${username.value}/hot-tags`),
  ])
  const posts = postsRes?.ok ? await postsRes.json() : []
  const replies = repliesRes?.ok ? await repliesRes.json() : []
  const tags = tagsRes?.ok ? await tagsRes.json() : []
  hotPosts.value = posts.map((post) => ({ icon: 'file-text', type: 'post', post, createdAt: post.createdAt }))
  hotReplies.value = replies.map((comment) => ({ icon: 'comment-icon', comment }))
  hotTags.value = tags.map((tag) => ({ icon: 'tag-one', type: 'tag', tag, createdAt: tag.createdAt }))
}

const isDiscussionItem = (item) => item && (item.type === 'comment' || item.type === 'reply')
const toDateKey = (value) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

const combineDiscussionItems = (items) => {
  const result = []
  items.forEach((item) => {
    if (!isDiscussionItem(item)) {
      result.push(item)
      return
    }

    const dateKey = toDateKey(item.createdAt)
    const last = result[result.length - 1]
    if (last && isDiscussionItem(last) && last.dateKey === dateKey) {
      last.entries.push({
        type: item.type,
        comment: item.comment,
        createdAt: item.createdAt,
      })
      if (item.type === 'comment' && last.type === 'reply') last.type = 'comment'
      if (new Date(item.createdAt) > new Date(last.createdAt)) last.createdAt = item.createdAt
    } else {
      result.push({
        type: item.type,
        icon: item.icon,
        createdAt: item.createdAt,
        dateKey,
        entries: [
          {
            type: item.type,
            comment: item.comment,
            createdAt: item.createdAt,
          },
        ],
      })
    }
  })
  return result
}

const fetchTimeline = async () => {
  const [postsRes, repliesRes, tagsRes] = await Promise.all([
    profileFetch(`/api/users/${username.value}/posts?limit=50`),
    profileFetch(`/api/users/${username.value}/replies?limit=50`),
    profileFetch(`/api/users/${username.value}/tags?limit=50`),
  ])
  const posts = postsRes?.ok ? await postsRes.json() : []
  const replies = repliesRes?.ok ? await repliesRes.json() : []
  const tags = tagsRes?.ok ? await tagsRes.json() : []
  const mapped = [
    ...posts.map((post) => ({ type: 'post', icon: 'file-text', post, createdAt: post.createdAt })),
    ...replies.map((comment) => ({
      type: comment.parentComment ? 'reply' : 'comment',
      icon: 'comment-icon',
      comment,
      createdAt: comment.createdAt,
    })),
    ...tags.map((tag) => ({ type: 'tag', icon: 'tag-one', tag, createdAt: tag.createdAt })),
  ]
  mapped.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
  timelineItems.value = combineDiscussionItems(mapped)
}

const fetchReadHistory = async () => {
  if (!isMine.value || !getToken()) {
    readPosts.value = []
    return
  }
  const res = await profileFetch(`/api/users/${username.value}/read-posts?limit=50`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  })
  readPosts.value = res?.ok ? (await res.json()).map((item) => ({ ...item, icon: 'file-text' })) : []
}

const fetchFollowUsers = async () => {
  const [followerRes, followingRes] = await Promise.all([
    profileFetch(`/api/users/${username.value}/followers`),
    profileFetch(`/api/users/${username.value}/following`),
  ])
  followers.value = followerRes?.ok ? await followerRes.json() : []
  followings.value = followingRes?.ok ? await followingRes.json() : []
}

const fetchFavorites = async () => {
  const res = await profileFetch(`/api/users/${username.value}/subscribed-posts`)
  favoritePosts.value = res?.ok ? (await res.json()).map((post) => ({ icon: 'bookmark', post })) : []
}

const withTabLoading = async (fn) => {
  tabLoading.value = true
  try {
    await fn()
  } finally {
    tabLoading.value = false
  }
}

const subscribeUser = async () => {
  const token = getToken()
  if (!token) {
    toast.error('Please sign in first.')
    return
  }
  const res = await profileFetch(`/api/subscriptions/users/${username.value}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  })
  if (res?.ok) {
    subscribed.value = true
    toast.success('Followed.')
  } else {
    toast.error('Unable to follow this user.')
  }
}

const unsubscribeUser = async () => {
  const token = getToken()
  if (!token) {
    toast.error('Please sign in first.')
    return
  }
  const res = await profileFetch(`/api/subscriptions/users/${username.value}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  })
  if (res?.ok) {
    subscribed.value = false
    toast.success('Unfollowed.')
  } else {
    toast.error('Unable to unfollow this user.')
  }
}

const sendMessage = async () => {
  const token = getToken()
  if (!token) {
    toast.error('Please sign in first.')
    return
  }
  try {
    const response = await profileFetch('/api/messages/conversations', {
      method: 'POST',
      body: JSON.stringify({ recipientId: user.value.id }),
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    })
    const result = await response.json()
    await navigateTo(`/message-box/${result.conversationId}`)
  } catch (error) {
    toast.error('Unable to start a message thread.')
  }
}

const loadInitialTab = async () => {
  if (selectedTab.value === 'summary') await withTabLoading(fetchSummary)
  else if (selectedTab.value === 'timeline') await withTabLoading(fetchTimeline)
  else if (selectedTab.value === 'following') await withTabLoading(fetchFollowUsers)
  else if (selectedTab.value === 'favorites') await withTabLoading(fetchFavorites)
}

const init = async () => {
  try {
    await fetchUser()
  } catch (error) {
    if (!isAbortError(error)) throw error
  } finally {
    if (!requestController.signal.aborted) isLoading.value = false
  }
  if (requestController.signal.aborted || redirectingTo404.value) return
  await loadInitialTab()
}

onMounted(init)

watch(selectedTab, async (tab) => {
  if (tab === 'timeline') {
    if (timelineFilter.value === 'reads' && readPosts.value.length === 0) await withTabLoading(fetchReadHistory)
    else if (timelineItems.value.length === 0) await withTabLoading(fetchTimeline)
  } else if (tab === 'following' && followers.value.length === 0 && followings.value.length === 0) {
    await withTabLoading(fetchFollowUsers)
  } else if (tab === 'favorites' && favoritePosts.value.length === 0) {
    await withTabLoading(fetchFavorites)
  } else if (tab === 'summary' && hotPosts.value.length === 0 && hotReplies.value.length === 0) {
    await withTabLoading(fetchSummary)
  }
})

watch(timelineFilter, async (filter) => {
  if (selectedTab.value !== 'timeline') return
  if (filter === 'reads' && readPosts.value.length === 0) await withTabLoading(fetchReadHistory)
  else if (filter !== 'reads' && timelineItems.value.length === 0) await withTabLoading(fetchTimeline)
})

watch(isMine, (value) => {
  if (!value && timelineFilter.value === 'reads') timelineFilter.value = 'all'
})
</script>

<style scoped>
.loading-page {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 300px;
}

.profile-page {
  width: min(1040px, calc(100% - 40px));
  margin: 0 auto;
  padding: 46px 0 72px;
  color: #2b414b;
}

.profile-page-header {
  display: flex;
  align-items: center;
  padding: 28px 30px;
  gap: 26px;
  border: 1px solid #c5d0d4;
  border-top: 5px solid #009edb;
  background: #fff;
}

.profile-page-header-avatar-img {
  width: 128px;
  height: 128px;
  border-radius: 50%;
}

.profile-page-header-avatar-img :deep(.base-user-avatar-img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.profile-page-header-user-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.profile-page-header-user-info-name {
  margin: 0;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 32px;
  font-weight: 400;
}

.profile-page-header-user-info-description {
  margin: 0;
  font-size: 15px;
  max-width: 680px;
  color: #5d6e76;
  line-height: 1.6;
}

.profile-page-header-user-info-buttons {
  display: flex;
  flex-direction: row;
  gap: 10px;
}

.profile-page-header-subscribe-button,
.profile-page-header-unsubscribe-button,
.profile-page-header-send-mail-button {
  display: inline-flex;
  flex-direction: row;
  gap: 5px;
  align-items: center;
  font-size: 14px;
  min-height: 38px;
  border-radius: 0;
  padding: 7px 12px;
  width: fit-content;
  cursor: pointer;
}

.profile-page-header-subscribe-button {
  color: white;
  border: 1px solid #0065a8;
  background: #0065a8;
}

.profile-page-header-unsubscribe-button,
.profile-page-header-send-mail-button {
  color: #0065a8;
  background: #fff;
  border: 1px solid #0065a8;
}

.profile-level-target {
  font-size: 12px;
  opacity: 0.8;
}

.profile-info {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: 18px 0 26px;
  padding: 0;
  gap: 1px;
  background: #cbd5d9;
  border: 1px solid #cbd5d9;
  scrollbar-width: none;
  overflow-x: auto;
}

.profile-info-item {
  display: grid;
  gap: 5px;
  align-content: center;
  min-height: 70px;
  padding: 12px 15px;
  background: #f6f8f8;
  white-space: nowrap;
}

.profile-info-item-label {
  color: #63737a;
  font-size: 11px;
  font-weight: 750;
  letter-spacing: .06em;
  text-transform: uppercase;
}

.profile-info-item-value {
  font-size: 14px;
}

:deep(.base-tabs-header) {
  position: sticky;
  top: 0;
  z-index: 200;
  background: #fff;
  display: flex;
  flex-direction: row;
  padding: 0;
  border-bottom: 4px solid #009edb;
  scrollbar-width: none;
  overflow-x: auto;
}

:deep(.base-tabs-item) {
  display: flex;
  flex: 0 0 auto;
  flex-direction: row;
  gap: 10px;
  align-items: center;
  justify-content: center;
  min-height: 43px;
  padding: 0 17px;
  width: auto;
  cursor: pointer;
  white-space: nowrap;
}

:deep(.base-tabs-item.selected) {
  color: #fff;
  background: #0065a8;
  border: 0;
}

.profile-summary {
  display: flex;
  flex-direction: column;
  padding: 26px 0;
  row-gap: 32px;
}

.summary-title {
  color: #2d4651;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 22px;
  margin: 0 0 10px;
  font-weight: 400;
}

.total-summary-content {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  gap: 1px;
  border: 1px solid #d0d9dc;
  background: #d0d9dc;
}

.total-summary-item {
  display: flex;
  flex-direction: row;
  min-width: 180px;
  flex: 1;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  padding: 14px;
  background: #fff;
}

.total-summary-item-label {
  font-size: 16px;
  opacity: 0.7;
}

.total-summary-item-value {
  font-size: 22px;
  font-weight: 700;
}

.summary-divider {
  display: flex;
  flex-direction: row;
  row-gap: 32px;
  column-gap: 20px;
  width: 100%;
  flex-wrap: wrap;
}

.hot-reply,
.hot-topic,
.hot-tag {
  width: 40%;
}

.timeline-tabs,
.follow-tabs {
  display: flex;
  flex-direction: row;
  margin-top: 18px;
  border-bottom: 1px solid #c9d3d7;
}

.timeline-tab-item,
.follow-tab-item {
  padding: 10px 20px;
  cursor: pointer;
  background: transparent;
  border: none;
  color: var(--text-color);
}

.timeline-tab-item.selected,
.follow-tab-item.selected {
  color: #0065a8;
  border-bottom: 3px solid #009edb;
}

.timeline-list,
.favorites-container,
.follow-list {
  padding: 10px 20px;
}

.timeline-date {
  font-size: 12px;
  color: gray;
  margin-top: 5px;
  white-space: nowrap;
}

.timeline-snippet {
  font-size: 14px;
  color: #666;
  margin-top: 5px;
}

.timeline-link {
  font-weight: 700;
  text-decoration: none;
  color: var(--text-color);
  word-break: break-word;
}

.timeline-link:hover,
.timeline-comment-link:hover {
  color: var(--primary-color);
  text-decoration: underline;
}

.timeline-comment-link {
  color: var(--text-color);
  word-break: break-word;
  text-decoration: underline;
  margin-left: 5px;
}

.reply-icon {
  color: var(--primary-color);
  margin-left: 5px;
}

.summary-empty {
  margin-top: 10px;
  font-size: 14px;
  opacity: 0.5;
}

.tab-loading {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px 0;
}

@media (max-width: 768px) {
  .profile-page {
    width: min(100% - 28px, 1040px);
    padding-top: 28px;
  }

  .profile-page-header {
    align-items: flex-start;
    padding: 22px 20px;
  }

  .profile-page-header-avatar-img {
    width: 96px;
    height: 96px;
  }

  :deep(.base-tabs-item) {
    width: auto;
  }

  .summary-divider {
    flex-direction: column;
  }

  .hot-reply,
  .hot-topic,
  .hot-tag {
    width: 100%;
  }
  .profile-info { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
