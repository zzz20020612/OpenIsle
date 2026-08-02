<template>
  <div class="message-page">
    <BaseTabs v-model="selectedTab" :tabs="tabs">
      <template #right>
        <div class="message-page-header-right">
          <div class="message-page-header-right-item" @click="markAllRead">
            <check-correct class="message-page-header-right-item-button-icon" />
            <span class="message-page-header-right-item-button-text"> Mark all as read </span>
          </div>
        </div>
      </template>

      <div v-if="selectedTab === 'control'">
        <div class="message-control-container">
          <div class="message-control-title">Notification settings</div>
          <div class="message-control-item-container">
            <template v-for="pref in notificationPrefs">
              <div
                v-if="canShowNotification(pref.type)"
                :key="pref.type"
                class="message-control-item"
              >
                <div class="message-control-item-label">{{ formatType(pref.type) }}</div>
                <BaseSwitch
                  :model-value="pref.enabled"
                  @update:modelValue="(val) => togglePref(pref, val)"
                />
              </div>
            </template>
          </div>
        </div>
        <div class="message-control-container">
          <div class="message-control-title">Email notification settings</div>
          <div class="message-control-item-container">
            <div v-for="pref in emailPrefs" :key="pref.type" class="message-control-item">
              <div class="message-control-item-label">{{ formatType(pref.type) }}</div>
              <BaseSwitch
                :model-value="pref.enabled"
                @update:modelValue="(val) => toggleEmailPref(pref, val)"
              />
            </div>
          </div>
        </div>
      </div>

      <template v-else>
        <div v-if="isLoadingMessage" class="loading-message">
          <l-hatch size="28" stroke="4" speed="3.5" color="var(--primary-color)"></l-hatch>
        </div>

        <BasePlaceholder
          v-else-if="notifications.length === 0"
          text="No notifications yet"
          icon="inbox"
        />

        <div class="timeline-container" v-if="notifications.length > 0">
          <BaseTimeline :items="notifications">
            <template #item="{ item }">
              <div class="notif-content" :class="{ read: item.read }">
                <span v-if="!item.read" class="unread-dot"></span>
                <span class="notif-type">
                  <template v-if="item.type === 'COMMENT_REPLY' && item.parentComment">
                    <NotificationContainer :item="item" :markRead="markRead">
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="`/users/${item.comment.author.id}`"
                        >{{ item.comment.author.username }}
                      </NuxtLink>
                      replied to my comment
                      <span>
                        <NuxtLink
                          class="notif-content-text"
                          @click="markRead(item.id)"
                          :to="resolveCommentPath(item.post, item.parentComment.id)"
                        >
                          <span
                            v-html="stripMarkdownWithTiebaMoji(item.parentComment.content, 500)"
                          ></span>
                        </NuxtLink>
                      </span>
                      with
                      <span>
                        <NuxtLink
                          class="notif-content-text"
                          @click="markRead(item.id)"
                          :to="resolveCommentPath(item.post, item.comment.id)"
                        >
                          <span
                            v-html="stripMarkdownWithTiebaMoji(item.comment.content, 500)"
                          ></span>
                        </NuxtLink>
                      </span>
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'COMMENT_REPLY' && !item.parentComment">
                    <NotificationContainer :item="item" :markRead="markRead">
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="`/users/${item.comment.author.id}`"
                        >{{ item.comment.author.username }}
                      </NuxtLink>
                      replied to my post
                      <span>
                        <NuxtLink
                          class="notif-content-text"
                          @click="markRead(item.id)"
                          :to="resolveContentPath(item.post)"
                        >
                          {{ stripMarkdownLength(item.post.title, 100) }}
                        </NuxtLink>
                      </span>
                      with
                      <span>
                        <NuxtLink
                          class="notif-content-text"
                          @click="markRead(item.id)"
                          :to="resolveCommentPath(item.post, item.comment.id)"
                        >
                          <span
                            v-html="stripMarkdownWithTiebaMoji(item.comment.content, 500)"
                          ></span>
                        </NuxtLink>
                      </span>
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'ACTIVITY_REDEEM' && !item.parentComment">
                    <NotificationContainer :item="item" :markRead="markRead">
                      <span class="notif-user">{{ item.fromUser.username }} </span>
                      requested a reward redemption. Contact: {{ item.content }}
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'POINT_REDEEM' && !item.parentComment">
                    <NotificationContainer :item="item" :markRead="markRead">
                      <span class="notif-user">{{ item.fromUser.username }} </span>
                      requested a points redemption. Contact: {{ item.content }}
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'REACTION' && item.post && !item.comment">
                    <NotificationContainer :item="item" :markRead="markRead">
                      <span class="notif-user">{{ item.fromUser.username }} </span> reacted to my post
                      <span>
                        <NuxtLink
                          class="notif-content-text"
                          @click="markRead(item.id)"
                          :to="resolveContentPath(item.post)"
                        >
                          {{ stripMarkdownLength(item.post.title, 100) }}
                        </NuxtLink>
                      </span>

                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'REACTION' && item.comment">
                    <NotificationContainer :item="item" :markRead="markRead">
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="`/users/${item.fromUser.id}`"
                        >{{ item.fromUser.username }}
                      </NuxtLink>
                      reacted to my comment
                      <span>
                        <NuxtLink
                          class="notif-content-text"
                          @click="markRead(item.id)"
                          :to="resolveCommentPath(item.post, item.comment.id)"
                        >
                          <span
                            v-html="stripMarkdownWithTiebaMoji(item.comment.content, 500)"
                          ></span>
                        </NuxtLink>
                      </span>

                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'POST_VIEWED'">
                    <NotificationContainer :item="item" :markRead="markRead">
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="`/users/${item.fromUser.id}`"
                      >
                        {{ item.fromUser.username }}
                      </NuxtLink>
                      viewed your post
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveContentPath(item.post)"
                      >
                        {{ stripMarkdownLength(item.post.title, 100) }}
                      </NuxtLink>
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'LOTTERY_WIN'">
                    <NotificationContainer :item="item" :markRead="markRead">
                      Congratulations, you won in
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveContentPath(item.post)"
                      >
                        {{ stripMarkdownLength(item.post.title, 100) }}
                      </NuxtLink>

                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'LOTTERY_DRAW'">
                    <NotificationContainer :item="item" :markRead="markRead">
                      Your lottery post
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveContentPath(item.post)"
                      >
                        {{ stripMarkdownLength(item.post.title, 100) }}
                      </NuxtLink>
                      has been drawn
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'POLL_VOTE'">
                    <NotificationContainer :item="item" :markRead="markRead">
                      Someone voted in your poll
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveContentPath(item.post)"
                      >
                        {{ stripMarkdownLength(item.post.title, 100) }}
                      </NuxtLink>
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'POLL_RESULT_OWNER'">
                    <NotificationContainer :item="item" :markRead="markRead">
                      Your poll
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveContentPath(item.post)"
                      >
                        {{ stripMarkdownLength(item.post.title, 100) }}
                      </NuxtLink>
                      has results
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'POLL_RESULT_PARTICIPANT'">
                    <NotificationContainer :item="item" :markRead="markRead">
                      A poll you joined
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveContentPath(item.post)"
                      >
                        {{ stripMarkdownLength(item.post.title, 100) }}
                      </NuxtLink>
                      has results
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'CATEGORY_PROPOSAL_RESULT_OWNER'">
                    <NotificationContainer :item="item" :markRead="markRead">
                      Your category proposal
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveContentPath(item.post)"
                      >
                        {{ stripMarkdownLength(item.post.title, 100) }}
                      </NuxtLink>
                      <span v-if="item.approved">was approved</span>
                      <span v-else>
                        was rejected<span v-if="item.content">. Reason: {{ item.content }}</span>
                      </span>
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'CATEGORY_PROPOSAL_RESULT_PARTICIPANT'">
                    <NotificationContainer :item="item" :markRead="markRead">
                      A category proposal you joined
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveContentPath(item.post)"
                      >
                        {{ stripMarkdownLength(item.post.title, 100) }}
                      </NuxtLink>
                      <span v-if="item.approved">was approved</span>
                      <span v-else>
                        was rejected<span v-if="item.content">. Reason: {{ item.content }}</span>
                      </span>
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'POST_UPDATED'">
                    <NotificationContainer :item="item" :markRead="markRead">
                      A post you follow
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveContentPath(item.post)"
                      >
                        {{ stripMarkdownLength(item.post.title, 100) }}
                      </NuxtLink>
                      has a new comment
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveCommentPath(item.post, item.comment.id)"
                      >
                        <span v-html="stripMarkdownWithTiebaMoji(item.comment.content, 500)"></span>
                      </NuxtLink>
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'USER_ACTIVITY' && item.parentComment">
                    <NotificationContainer :item="item" :markRead="markRead">
                      Someone you follow
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="`/users/${item.comment.author.id}`"
                      >
                        {{ item.comment.author.username }}
                      </NuxtLink>
                      replied to a comment in
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveCommentPath(item.post, item.parentComment.id)"
                      >
                        <span
                          v-html="stripMarkdownWithTiebaMoji(item.parentComment.content, 500)"
                        ></span>
                      </NuxtLink>

                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveCommentPath(item.post, item.comment.id)"
                      >
                        <span v-html="stripMarkdownWithTiebaMoji(item.comment.content, 500)"></span>
                      </NuxtLink>
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'USER_ACTIVITY'">
                    <NotificationContainer :item="item" :markRead="markRead">
                      Someone you follow
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="`/users/${item.comment.author.id}`"
                      >
                        {{ item.comment.author.username }}
                      </NuxtLink>
                      commented on
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveContentPath(item.post)"
                      >
                        {{ stripMarkdownLength(item.post.title, 100) }}
                      </NuxtLink>

                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveCommentPath(item.post, item.comment.id)"
                      >
                        <span v-html="stripMarkdownWithTiebaMoji(item.comment.content, 500)"></span>
                      </NuxtLink>
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'MENTION' && item.comment">
                    <NotificationContainer :item="item" :markRead="markRead">
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="`/users/${item.fromUser.id}`"
                      >
                        {{ item.fromUser.username }}
                      </NuxtLink>
                      mentioned you in a comment:
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveCommentPath(item.post, item.comment.id)"
                      >
                        <span v-html="stripMarkdownWithTiebaMoji(item.comment.content, 500)"></span>
                      </NuxtLink>
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'MENTION'">
                    <NotificationContainer :item="item" :markRead="markRead">
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="`/users/${item.fromUser.id}`"
                      >
                        {{ item.fromUser.username }}
                      </NuxtLink>
                      mentioned you in
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveContentPath(item.post)"
                      >
                        {{ stripMarkdownLength(item.post.title, 100) }}
                      </NuxtLink>

                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'USER_FOLLOWED'">
                    <NotificationContainer :item="item" :markRead="markRead">
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="`/users/${item.fromUser.id}`"
                      >
                        {{ item.fromUser.username }}
                      </NuxtLink>
                      started following you
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'USER_UNFOLLOWED'">
                    <NotificationContainer :item="item" :markRead="markRead">
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="`/users/${item.fromUser.id}`"
                      >
                        {{ item.fromUser.username }}
                      </NuxtLink>
                      unfollowed you
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'FOLLOWED_POST'">
                    <NotificationContainer :item="item" :markRead="markRead">
                      Someone you follow
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="`/users/${item.fromUser.id}`"
                      >
                        {{ item.fromUser.username }}
                      </NuxtLink>
                      published a post
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveContentPath(item.post)"
                      >
                        {{ stripMarkdownLength(item.post.title, 100) }}
                      </NuxtLink>
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'POST_SUBSCRIBED'">
                    <NotificationContainer :item="item" :markRead="markRead">
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="`/users/${item.fromUser.id}`"
                      >
                        {{ item.fromUser.username }}
                      </NuxtLink>
                      subscribed to your post
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveContentPath(item.post)"
                      >
                        {{ stripMarkdownLength(item.post.title, 100) }}
                      </NuxtLink>
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'POST_UNSUBSCRIBED'">
                    <NotificationContainer :item="item" :markRead="markRead">
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="`/users/${item.fromUser.id}`"
                      >
                        {{ item.fromUser.username }}
                      </NuxtLink>
                      unsubscribed from your post
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveContentPath(item.post)"
                      >
                        {{ stripMarkdownLength(item.post.title, 100) }}
                      </NuxtLink>
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'POST_REVIEW_REQUEST' && item.fromUser">
                    <NotificationContainer :item="item" :markRead="markRead">
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="`/users/${item.fromUser.id}`"
                      >
                        {{ item.fromUser.username }}
                      </NuxtLink>
                      published a post
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveContentPath(item.post)"
                      >
                        {{ stripMarkdownLength(item.post.title, 100) }}
                      </NuxtLink>
                      and needs review
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'POST_REVIEW_REQUEST'">
                    <NotificationContainer :item="item" :markRead="markRead">
                      Your post
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveContentPath(item.post)"
                      >
                        {{ stripMarkdownLength(item.post.title, 100) }}
                      </NuxtLink>
                      has been submitted for review
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'REGISTER_REQUEST'">
                    <NotificationContainer :item="item" :markRead="markRead">
                      {{ item.fromUser.username }} requested membership. Reason: {{ item.content }}
                      <template #actions v-if="authState.role === 'ADMIN'">
                        <div v-if="!item.read" class="optional-buttons">
                          <div
                            class="mark-approve-button-item"
                            @click="approve(item.fromUser.id, item.id)"
                          >
                            Approve
                          </div>
                          <div
                            class="mark-reject-button-item"
                            @click="reject(item.fromUser.id, item.id)"
                          >
                            Reject
                          </div>
                        </div>
                        <div v-else class="has_read_button" @click="markRead(item.id)">Read</div>
                      </template>
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'POST_REVIEWED' && item.approved">
                    <NotificationContainer :item="item" :markRead="markRead">
                      Your post
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveContentPath(item.post)"
                      >
                        {{ stripMarkdownLength(item.post.title, 100) }}
                      </NuxtLink>
                      was approved
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'POST_REVIEWED' && item.approved === false">
                    <NotificationContainer :item="item" :markRead="markRead">
                      Your post
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveContentPath(item.post)"
                      >
                        {{ stripMarkdownLength(item.post.title, 100) }}
                      </NuxtLink>
                      was rejected by an administrator
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'POST_FEATURED'">
                    <NotificationContainer :item="item" :markRead="markRead">
                      Your post
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveContentPath(item.post)"
                      >
                        {{ stripMarkdownLength(item.post.title, 100) }}
                      </NuxtLink>
                      was featured
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'DONATION'">
                    <NotificationContainer :item="item" :markRead="markRead">
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="`/users/${item.fromUser.id}`"
                      >
                        {{ item.fromUser.username }}
                      </NuxtLink>
                      donated to you on
                      <NuxtLink
                        class="notif-content-text"
                        @click="markRead(item.id)"
                        :to="resolveContentPath(item.post)"
                      >
                        {{ stripMarkdownLength(item.post.title, 100) }}
                      </NuxtLink>

                      <template v-if="item.content">. You received {{ item.content }} points.</template>
                    </NotificationContainer>
                  </template>
                  <template v-else-if="item.type === 'POST_DELETED'">
                    <NotificationContainer :item="item" :markRead="markRead">
                      An administrator
                      <template v-if="item.fromUser">
                        <NuxtLink
                          class="notif-content-text"
                          @click="markRead(item.id)"
                          :to="`/users/${item.fromUser.id}`"
                        >
                          {{ item.fromUser.username }}
                        </NuxtLink>
                      </template>
                      deleted your post
                      <span class="notif-content-text">
                        <span v-html="stripMarkdownWithTiebaMoji(item.content, 500)"></span>
                      </span>
                    </NotificationContainer>
                  </template>
                  <template v-else>
                    <NotificationContainer :item="item" :markRead="markRead">
                      {{ formatType(item.type) }}
                    </NotificationContainer>
                  </template>
                </span>
                <span class="notif-time">{{ TimeManager.format(item.createdAt) }}</span>
              </div>
            </template>
          </BaseTimeline>
          <InfiniteLoadMore :key="selectedTab" :on-load="loadMore" :pause="isLoadingMessage" />
        </div>
      </template>
    </BaseTabs>
  </div>
</template>

<script setup>
import { ref, watch, onActivated } from 'vue'
import BasePlaceholder from '~/components/BasePlaceholder.vue'
import BaseTimeline from '~/components/BaseTimeline.vue'
import NotificationContainer from '~/components/NotificationContainer.vue'
import InfiniteLoadMore from '~/components/InfiniteLoadMore.vue'
import BaseTabs from '~/components/BaseTabs.vue'
import { toast } from '~/main'
import { authState, getToken } from '~/utils/auth'
import { stripMarkdownWithTiebaMoji } from '~/utils/markdown'
import { resolveCommentPath, resolveContentPath } from '~/utils/contentRoutes'
import {
  fetchNotifications,
  fetchUnreadCount,
  isLoadingMessage,
  markNotificationRead,
  notifications,
  markAllRead,
  hasMore,
  fetchNotificationPreferences,
  updateNotificationPreference,
  fetchEmailNotificationPreferences,
  updateEmailNotificationPreference,
} from '~/utils/notification'
import TimeManager from '~/utils/time'
import BaseSwitch from '~/components/BaseSwitch.vue'

const config = useRuntimeConfig()
const API_BASE_URL = config.public.apiBaseUrl
const route = useRoute()
const selectedTab = ref(
  ['all', 'unread', 'control'].includes(route.query.tab) ? route.query.tab : 'unread',
)
const tabs = [
  { key: 'all', label: 'Notifications' },
  { key: 'unread', label: 'Unread' },
  { key: 'control', label: 'Settings' },
]
const notificationPrefs = ref([])
const emailPrefs = ref([])
const page = ref(0)
const pageSize = 30

const loadMore = async () => {
  if (!hasMore.value) return true
  page.value++
  await fetchNotifications({
    page: page.value,
    size: pageSize,
    unread: selectedTab.value === 'unread',
    append: true,
  })
  return !hasMore.value
}

watch(selectedTab, async (tab) => {
  page.value = 0
  await fetchNotifications({ page: 0, size: pageSize, unread: tab === 'unread' })
})

const fetchPrefs = async () => {
  notificationPrefs.value = await fetchNotificationPreferences()
}

const fetchEmailPrefs = async () => {
  emailPrefs.value = await fetchEmailNotificationPreferences()
}

const togglePref = async (pref, value) => {
  const ok = await updateNotificationPreference(pref.type, value)
  if (ok) {
    pref.enabled = value
    await fetchNotifications({
      page: page.value,
      size: pageSize,
      unread: selectedTab.value === 'unread',
    })
    await fetchUnreadCount()
  } else {
    toast.error('Operation failed')
  }
}

const toggleEmailPref = async (pref, value) => {
  const ok = await updateEmailNotificationPreference(pref.type, value)
  if (ok) {
    pref.enabled = value
  } else {
    toast.error('Operation failed')
  }
}

const markRead = async (id) => {
  markNotificationRead(id)
  if (selectedTab.value === 'unread') {
    const index = notifications.value.findIndex((n) => n.id === id)
    if (index !== -1) notifications.value.splice(index, 1)
  }
}

const approve = async (id, nid) => {
  const token = getToken()
  if (!token) return
  const res = await fetch(`${API_BASE_URL}/api/admin/users/${id}/approve`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  })
  if (res.ok) {
    markRead(nid)
    toast.success('Approved')
  } else {
    toast.error('Operation failed')
  }
}

const reject = async (id, nid) => {
  const token = getToken()
  if (!token) return
  const res = await fetch(`${API_BASE_URL}/api/admin/users/${id}/reject`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  })
  if (res.ok) {
    markRead(nid)
    toast.success('Rejected')
  } else {
    toast.error('Operation failed')
  }
}

const formatType = (t) => {
  switch (t) {
    case 'POST_VIEWED':
      return 'Post viewed'
    case 'COMMENT_REPLY':
      return 'Someone replied to you'
    case 'REACTION':
      return 'New reaction'
    case 'POST_REVIEW_REQUEST':
      return 'Post pending review'
    case 'POST_REVIEWED':
      return 'Post review result'
    case 'POST_UPDATED':
      return 'New comment on followed post'
    case 'FOLLOWED_POST':
      return 'Followed user published a post'
    case 'POST_SUBSCRIBED':
      return 'New post subscription'
    case 'POST_UNSUBSCRIBED':
      return 'Post subscription canceled'
    case 'USER_FOLLOWED':
      return 'New follower'
    case 'USER_UNFOLLOWED':
      return 'Follower removed'
    case 'USER_ACTIVITY':
      return 'Followed user activity'
    case 'MENTION':
      return 'Mention'
    case 'REGISTER_REQUEST':
      return 'Membership request'
    case 'ACTIVITY_REDEEM':
      return 'Reward redemption request'
    case 'POINT_REDEEM':
      return 'Points redemption request'
    case 'DONATION':
      return 'Donation received'
    case 'LOTTERY_WIN':
      return 'Lottery win'
    case 'LOTTERY_DRAW':
      return 'Lottery result'
    case 'POST_DELETED':
      return 'Post deleted'
    case 'POST_FEATURED':
      return 'Post featured'
    case 'POLL_VOTE':
      return 'Poll participation'
    case 'POLL_RESULT_OWNER':
      return 'Your poll result published'
    case 'POLL_RESULT_PARTICIPANT':
      return 'Joined poll result published'
    case 'CATEGORY_PROPOSAL_RESULT_OWNER':
      return 'Category proposal result'
    case 'CATEGORY_PROPOSAL_RESULT_PARTICIPANT':
      return 'Joined category proposal result'
    default:
      return t
  }
}

const isAdmin = computed(() => authState.role === 'ADMIN')

const needAdminSet = new Set([
  'POST_REVIEW_REQUEST',
  'REGISTER_REQUEST',
  'POINT_REDEEM',
  'ACTIVITY_REDEEM',
])

const canShowNotification = (type) => {
  return !needAdminSet.has(type) || isAdmin.value
}

onActivated(async () => {
  page.value = 0
  await fetchNotifications({ page: 0, size: pageSize, unread: selectedTab.value === 'unread' })
  fetchPrefs()
  fetchEmailPrefs()
})
</script>

<style scoped>
.loading-message {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 300px;
}

.message-page {
  background-color: var(--background-color);
  overflow-x: hidden;
}

.message-page-header-right {
  display: flex;
  flex-direction: row;
  align-items: center;
}

.message-page-header-right-item {
  display: flex;
  flex-direction: row;
  align-items: center;
  cursor: pointer;
  color: var(--primary-color);
  padding-right: 10px;
  gap: 5px;
}

.message-page-header-right-item-button-icon {
  font-size: 12px;
}

.message-page-header-right-item-button-text {
  font-size: 12px;
}

.message-page-header-right-item-button-text:hover {
  text-decoration: underline;
}

.timeline-container {
  padding: 10px 20px;
  height: 100%;
}

.notif-content {
  display: flex;
  flex-direction: column;
  margin-bottom: 30px;
  position: relative;
}

.notif-content.read {
  opacity: 0.7;
}

.unread-dot {
  position: absolute;
  left: -10px;
  top: 4px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #ff4d4f;
}

.notif-type {
  font-weight: bold;
}

.notif-time {
  font-size: 12px;
  color: gray;
}

.notif-content-text {
  font-weight: bold;
  color: var(--primary-color) !important;
  text-decoration: none !important;
  word-break: break-all;
}

.optional-buttons {
  display: flex;
  flex-direction: row;
  gap: 10px;
}

.mark-approve-button-item {
  color: green;
  cursor: pointer;
}

.mark-reject-button-item {
  color: red;
  cursor: pointer;
}

.mark-approve-button-item:hover {
  text-decoration: underline;
}

.mark-reject-button-item:hover {
  text-decoration: underline;
}

.has_read_button {
  font-size: 12px;
}

.notif-content-text:hover {
  color: var(--primary-color) !important;
  text-decoration: underline !important;
}

.notif-user {
  font-weight: bold;
  color: var(--text-color);
}

.message-control-title {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 15px;
}

.message-control-container {
  padding: 20px;
}

.message-control-item-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.message-control-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 200px;
}

.message-control-item-label {
  font-size: 14px;
}

@media (max-width: 768px) {
  .has_read_button {
    display: none;
  }
}
</style>
