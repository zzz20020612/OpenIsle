import { navigateTo, useRuntimeConfig } from 'nuxt/app'
import { reactive, ref } from 'vue'
import { toast } from '~/composables/useToast'
import { authState, getToken } from '~/utils/auth'
import { reactionEmojiMap } from '~/utils/reactions'
import { resolveCommentPath, resolveContentPath } from '~/utils/contentRoutes'

export const notificationState = reactive({
  unreadCount: 0,
})

export const LEGACY_NOTIFICATION_TYPES = new Set([
  'ACTIVITY_REDEEM',
  'POINT_REDEEM',
  'DONATION',
  'LOTTERY_WIN',
  'LOTTERY_DRAW',
  'POLL_VOTE',
  'POLL_RESULT_OWNER',
  'POLL_RESULT_PARTICIPANT',
  'CATEGORY_PROPOSAL_RESULT_OWNER',
  'CATEGORY_PROPOSAL_RESULT_PARTICIPANT',
])

const ADMIN_NOTIFICATION_TYPES = new Set([
  'POST_REVIEW_REQUEST',
  'REGISTER_REQUEST',
])

const hiddenNotificationTypes = () => [
  ...LEGACY_NOTIFICATION_TYPES,
  ...(authState.role === 'ADMIN' ? [] : ADMIN_NOTIFICATION_TYPES),
]

export const isVisibleNotificationType = (type) =>
  !LEGACY_NOTIFICATION_TYPES.has(type) &&
  (authState.role === 'ADMIN' || !ADMIN_NOTIFICATION_TYPES.has(type))

const iconMap = {
  POST_VIEWED: 'HistoryIcon',
  COMMENT_REPLY: 'MessageOne',
  POST_REVIEWED: 'CheckCorrect',
  POST_REVIEW_REQUEST: 'FileText',
  POST_UPDATED: 'Edit',
  USER_ACTIVITY: 'UserIcon',
  FOLLOWED_POST: 'Pin',
  USER_FOLLOWED: 'AddUser',
  USER_UNFOLLOWED: 'ReduceUser',
  POST_SUBSCRIBED: 'Bookmark',
  POST_UNSUBSCRIBED: 'Bookmark',
  REGISTER_REQUEST: 'AlarmClock',
  MENTION: 'HashtagKey',
  POST_DELETED: 'ClearIcon',
  POST_FEATURED: 'Star',
}

export async function fetchUnreadCount() {
  const config = useRuntimeConfig()
  const API_BASE_URL = config.public.apiBaseUrl
  try {
    const token = getToken()
    if (!token) {
      notificationState.unreadCount = 0
      return 0
    }
    const ids = await collectUnreadNotificationIds(hiddenNotificationTypes())
    notificationState.unreadCount = ids.length
    return ids.length
  } catch (e) {
    notificationState.unreadCount = 0
    return 0
  }
}

export async function markNotificationsRead(ids) {
  try {
    const config = useRuntimeConfig()
    const API_BASE_URL = config.public.apiBaseUrl

    const token = getToken()
    if (!token || !ids || ids.length === 0) return false
    const res = await fetch(`${API_BASE_URL}/api/notifications/read`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ids }),
    })
    return res.ok
  } catch (e) {
    return false
  }
}

const MARK_ALL_FETCH_SIZE = 100
const MARK_ALL_CHUNK_SIZE = 200
const MARK_ALL_MAX_PAGES = 200

async function fetchUnreadNotificationsPage(page, size) {
  const config = useRuntimeConfig()
  const API_BASE_URL = config.public.apiBaseUrl
  const token = getToken()
  if (!token) throw new Error('NO_TOKEN')

  const res = await fetch(`${API_BASE_URL}/api/notifications/unread?page=${page}&size=${size}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!res.ok) throw new Error('FETCH_UNREAD_FAILED')
  const data = await res.json()
  return Array.isArray(data) ? data : []
}

async function collectUnreadNotificationIds(excludedTypes = []) {
  const excludedTypeSet = new Set(excludedTypes)
  const ids = []

  for (let page = 0; page < MARK_ALL_MAX_PAGES; page++) {
    const pageData = await fetchUnreadNotificationsPage(page, MARK_ALL_FETCH_SIZE)
    if (pageData.length === 0) break

    for (const notification of pageData) {
      if (!notification || excludedTypeSet.has(notification.type)) continue
      if (typeof notification.id !== 'number') continue
      ids.push(notification.id)
    }

    if (pageData.length < MARK_ALL_FETCH_SIZE) break
  }

  return [...new Set(ids)]
}

async function markNotificationsReadInChunks(ids) {
  for (let i = 0; i < ids.length; i += MARK_ALL_CHUNK_SIZE) {
    const chunk = ids.slice(i, i + MARK_ALL_CHUNK_SIZE)
    const ok = await markNotificationsRead(chunk)
    if (!ok) return false
  }
  return true
}

export async function fetchNotificationPreferences() {
  try {
    const config = useRuntimeConfig()
    const API_BASE_URL = config.public.apiBaseUrl

    const token = getToken()
    if (!token) return []
    const res = await fetch(`${API_BASE_URL}/api/notifications/prefs`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) return []
    const preferences = await res.json()
    return preferences.filter((preference) => isVisibleNotificationType(preference.type))
  } catch (e) {
    return []
  }
}

export async function updateNotificationPreference(type, enabled) {
  try {
    const config = useRuntimeConfig()
    const API_BASE_URL = config.public.apiBaseUrl
    const token = getToken()
    if (!token) return false
    const res = await fetch(`${API_BASE_URL}/api/notifications/prefs`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ type, enabled }),
    })
    return res.ok
  } catch (e) {
    return false
  }
}

export async function fetchEmailNotificationPreferences() {
  try {
    const config = useRuntimeConfig()
    const API_BASE_URL = config.public.apiBaseUrl

    const token = getToken()
    if (!token) return []
    const res = await fetch(`${API_BASE_URL}/api/notifications/email-prefs`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) return []
    const preferences = await res.json()
    return preferences.filter((preference) => isVisibleNotificationType(preference.type))
  } catch (e) {
    return []
  }
}

export async function updateEmailNotificationPreference(type, enabled) {
  try {
    const config = useRuntimeConfig()
    const API_BASE_URL = config.public.apiBaseUrl
    const token = getToken()
    if (!token) return false
    const res = await fetch(`${API_BASE_URL}/api/notifications/email-prefs`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ type, enabled }),
    })
    return res.ok
  } catch (e) {
    return false
  }
}

/** Build the shared notification loader and read-state operations. */
function createFetchNotifications() {
  const notifications = ref([])
  const isLoadingMessage = ref(false)
  const hasMore = ref(true)

  const fetchNotifications = async ({
    page = 0,
    size = 30,
    unread = false,
    append = false,
  } = {}) => {
    const config = useRuntimeConfig()
    const API_BASE_URL = config.public.apiBaseUrl
    try {
      const token = getToken()
      if (!token) {
        toast.error('Please sign in to view notifications.')
        return
      }
      if (!append) notifications.value = []
      isLoadingMessage.value = true
      const res = await fetch(
        `${API_BASE_URL}/api/notifications${unread ? '/unread' : ''}?page=${page}&size=${size}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      )
      isLoadingMessage.value = false
      if (!res.ok) {
        toast.error('Unable to load notifications.')
        return
      }
      const data = await res.json()
      const arr = []

      for (const n of data) {
        if (!isVisibleNotificationType(n.type)) continue
        try {
          if (n.type === 'COMMENT_REPLY' && n.comment?.author) {
          arr.push({
            ...n,
            src: n.comment.author.avatar,
            iconClick: () => {
              markNotificationRead(n.id)
              navigateTo(`/users/${n.comment.author.id}`, { replace: true })
            },
          })
        } else if (n.type === 'REACTION') {
          arr.push({
            ...n,
            emoji: reactionEmojiMap[n.reactionType],
            iconClick: () => {
              if (n.fromUser) {
                markNotificationRead(n.id)
                navigateTo(`/users/${n.fromUser.id}`, { replace: true })
              }
            },
          })
        } else if (n.type === 'POST_VIEWED') {
          arr.push({
            ...n,
            src: n.fromUser ? n.fromUser.avatar : null,
            icon: n.fromUser ? undefined : iconMap[n.type],
            iconClick: () => {
              if (n.fromUser) {
                markNotificationRead(n.id)
                navigateTo(`/users/${n.fromUser.id}`, { replace: true })
              }
            },
          })
        } else if (n.type === 'POST_DELETED') {
          arr.push({
            ...n,
            src: n.fromUser ? n.fromUser.avatar : null,
            icon: n.fromUser ? undefined : iconMap[n.type],
            iconClick: () => {
              if (n.fromUser) {
                markNotificationRead(n.id)
                navigateTo(`/users/${n.fromUser.id}`, { replace: true })
              }
            },
          })
        } else if ((n.type === 'POST_UPDATED' || n.type === 'USER_ACTIVITY') && n.comment?.author) {
          arr.push({
            ...n,
            src: n.comment.author.avatar,
            iconClick: () => {
              markNotificationRead(n.id)
              navigateTo(`/users/${n.comment.author.id}`, { replace: true })
            },
          })
        } else if (n.type === 'MENTION') {
          arr.push({
            ...n,
            icon: iconMap[n.type],
            iconClick: () => {
              if (n.fromUser) {
                markNotificationRead(n.id)
                navigateTo(`/users/${n.fromUser.id}`, { replace: true })
              }
            },
          })
        } else if (n.type === 'USER_FOLLOWED' || n.type === 'USER_UNFOLLOWED') {
          arr.push({
            ...n,
            icon: iconMap[n.type],
            iconClick: () => {
              if (n.fromUser) {
                markNotificationRead(n.id)
                navigateTo(`/users/${n.fromUser.id}`, { replace: true })
              }
            },
          })
        } else if (
          n.type === 'FOLLOWED_POST' ||
          n.type === 'POST_SUBSCRIBED' ||
          n.type === 'POST_UNSUBSCRIBED'
        ) {
          arr.push({
            ...n,
            icon: iconMap[n.type],
            iconClick: () => {
              if (n.post) {
                markNotificationRead(n.id)
                navigateTo(resolveContentPath(n.post), { replace: true })
              }
            },
          })
        } else if (n.type === 'POST_REVIEW_REQUEST') {
          arr.push({
            ...n,
            src: n.fromUser ? n.fromUser.avatar : null,
            icon: n.fromUser ? undefined : iconMap[n.type],
            iconClick: () => {
              if (n.post) {
                markNotificationRead(n.id)
                navigateTo(resolveContentPath(n.post), { replace: true })
              }
            },
          })
        } else if (n.type === 'POST_FEATURED') {
          arr.push({
            ...n,
            icon: iconMap[n.type],
            iconClick: () => {
              if (n.post) {
                markNotificationRead(n.id)
                navigateTo(resolveContentPath(n.post), { replace: true })
              }
            },
          })
        } else if (n.type === 'REGISTER_REQUEST') {
          arr.push({
            ...n,
            icon: iconMap[n.type],
            iconClick: () => {},
          })
        } else {
          arr.push({
            ...n,
            icon: iconMap[n.type],
          })
        }
        } catch (error) {
          console.warn('Notification rendered with limited context.', n?.id, n?.type, error)
          arr.push({ ...n, icon: iconMap[n.type] })
        }
      }

      if (append) notifications.value.push(...arr)
      else notifications.value = arr
      hasMore.value = data.length === size
    } catch (e) {
      console.error(e)
      isLoadingMessage.value = false
    }
  }

  const markNotificationRead = async (id) => {
    if (!id) return
    const n = notifications.value.find((n) => n.id === id)
    if (!n || n.read) return
    n.read = true
    if (notificationState.unreadCount > 0) notificationState.unreadCount--
    const ok = await markNotificationsRead([id])
    if (!ok) {
      n.read = false
      notificationState.unreadCount++
    } else {
      fetchUnreadCount()
    }
  }

  const markAllRead = async () => {
    // Fetch every unread page so read-all covers notifications outside the current viewport.
    const localIdsToMark = notifications.value
      .filter((n) => n.type !== 'REGISTER_REQUEST' && !n.read)
      .map((n) => n.id)

    notifications.value.forEach((n) => {
      if (n.type !== 'REGISTER_REQUEST') n.read = true
    })
    notificationState.unreadCount = notifications.value.filter((n) => !n.read).length

    try {
      const idsToMark = await collectUnreadNotificationIds([
        ...hiddenNotificationTypes(),
        ...(authState.role === 'ADMIN' ? ['REGISTER_REQUEST'] : []),
      ])
      if (idsToMark.length > 0) {
        const ok = await markNotificationsReadInChunks(idsToMark)
        if (!ok) throw new Error('MARK_READ_FAILED')
      }

      await fetchUnreadCount()
      if (authState.role === 'ADMIN') {
        toast.success('All notifications marked as read except membership requests')
      } else {
        toast.success('All notifications marked as read')
      }
    } catch (e) {
      notifications.value.forEach((n) => {
        if (localIdsToMark.includes(n.id)) n.read = false
      })
      await fetchUnreadCount()
      toast.error('Unable to mark notifications as read. Please try again.')
      return
    }
  }
  return {
    fetchNotifications,
    markNotificationRead,
    notifications,
    isLoadingMessage,
    markAllRead,
    hasMore,
  }
}

export const {
  fetchNotifications,
  markNotificationRead,
  notifications,
  isLoadingMessage,
  markAllRead,
  hasMore,
} = createFetchNotifications()
