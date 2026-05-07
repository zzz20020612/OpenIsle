<template>
  <main class="paper-shell">
    <div class="paper-container">
      <header class="paper-workspace-header">
        <div>
          <div class="paper-page-eyebrow">Paper Workspace</div>
          <h1 class="paper-page-title">Research record</h1>
        </div>
        <div class="paper-toolbar">
          <NuxtLink class="paper-button" to="/papers">Paper feed</NuxtLink>
          <NuxtLink class="paper-button" to="/papers/rankings">Rankings</NuxtLink>
        </div>
      </header>

      <section class="paper-panel paper-detail-header">
        <div class="paper-detail-header-top">
          <div class="paper-meta-row" style="margin-top: 0">
            <span class="paper-pill subject">{{ paper.subjectArea || 'Research Paper' }}</span>
            <span class="paper-pill">{{ paper.paperType || 'Research Article' }}</span>
            <span class="paper-pill status">{{ normalizeStatus(paper.screeningStatus) }}</span>
            <span v-if="paper.featured" class="paper-pill featured">Featured</span>
            <span v-if="paperRssIncluded(paper)" class="paper-pill">RSS included</span>
          </div>
          <div class="paper-detail-actions">
            <button
              v-if="canSubscribeToDiscussion"
              class="paper-button primary"
              type="button"
              @click="subscribeDiscussion"
            >
              Follow paper
            </button>
            <button
              v-else-if="canUnsubscribeFromDiscussion"
              class="paper-button active"
              type="button"
              @click="unsubscribeDiscussion"
            >
              Following
            </button>
            <NuxtLink
              v-else-if="!authState.loggedIn"
              class="paper-button"
              to="/login"
            >
              Sign in to follow
            </NuxtLink>
            <DropdownMenu v-if="paperActionMenuItems.length > 0" :items="paperActionMenuItems">
              <template #trigger>
                <more-one class="paper-action-menu-icon" />
              </template>
            </DropdownMenu>
          </div>
        </div>
        <h1 class="paper-detail-title">{{ paper.title }}</h1>
        <div class="paper-citation-authors" aria-label="Paper authors">
          <span
            v-for="(author, index) in paper.authors || []"
            :key="author.id || `${author.displayName || author}-${index}`"
            class="paper-citation-author"
          >
            <NuxtLink v-if="author.userId" :to="`/users/${author.userId}`">
              {{ author.displayName || `Author ${index + 1}` }}
            </NuxtLink>
            <span v-else>{{ author.displayName || `Author ${index + 1}` }}</span>
            <sup v-if="authorMarkers(author, index).length" class="paper-citation-markers">
              <span
                v-for="(marker, markerIndex) in authorMarkers(author, index)"
                :key="`${marker.label}-${markerIndex}`"
                class="paper-citation-marker"
                :class="{ 'has-note': marker.note }"
                :tabindex="marker.note ? 0 : undefined"
                :aria-label="marker.note || marker.label"
              >
                <span>{{ marker.label }}</span>
                <span v-if="markerIndex < authorMarkers(author, index).length - 1">,</span>
                <span v-if="marker.note" class="paper-citation-tooltip" role="tooltip">
                  {{ marker.note }}
                </span>
              </span>
            </sup>
          </span>
        </div>
        <div v-if="authorAffiliations.length" class="paper-citation-affiliations">
          <div v-for="affiliation in authorAffiliations" :key="affiliation.key">
            <sup>{{ affiliation.index }}</sup>
            <span>{{ affiliation.label }}</span>
          </div>
        </div>
        <p class="paper-page-description">{{ paper.abstractText }}</p>
        <div class="paper-meta-row">
          <span class="paper-pill">{{ paper.primaryInstitutionName || 'Independent' }}</span>
          <span class="paper-pill">{{ paper.scoreSnapshot?.ratingCount || 0 }} ratings</span>
          <span class="paper-score-chip">
            <strong>{{ formatScore(paper.scoreSnapshot?.compositeScore) }}</strong>
            score
          </span>
        </div>
      </section>

      <section class="paper-detail-layout">
        <article>
          <section class="paper-block">
            <h2 class="paper-block-title">Abstract</h2>
            <p class="paper-abstract">{{ paper.abstractText }}</p>
            <div v-if="paper.keywords?.length" class="paper-meta-row">
              <span v-for="keyword in paper.keywords" :key="keyword" class="paper-pill subject">
                {{ keyword }}
              </span>
            </div>
          </section>

          <section class="paper-block">
            <h2 class="paper-block-title">Manuscript</h2>
            <div v-if="paper.manuscriptFiles?.length || paper.supplementaryFiles?.length" class="paper-file-list paper-file-list-detail">
              <div v-for="file in paper.manuscriptFiles || []" :key="`main-${file.fileName}`" class="paper-file-row">
                <span>
                  <strong>{{ file.fileName }}</strong>
                  <small>{{ file.fileRole }} - {{ formatFileSize(file.fileSize) }}</small>
                </span>
              </div>
              <div v-for="file in paper.supplementaryFiles || []" :key="`supp-${file.fileName}`" class="paper-file-row">
                <span>
                  <strong>{{ file.fileName }}</strong>
                  <small>{{ file.fileRole }} - {{ formatFileSize(file.fileSize) }}</small>
                </span>
              </div>
            </div>
            <div class="paper-manuscript">{{ paper.content }}</div>
          </section>

          <section class="paper-block paper-discussion-block">
            <div class="paper-discussion-header">
              <div>
                <h2 class="paper-block-title">Reader Discussion</h2>
                <p class="paper-section-note">
                  Comments, replies, reactions, and notifications are powered by this paper's
                  linked OpenIsle post.
                </p>
              </div>
              <div class="paper-discussion-actions">
                <span class="paper-discussion-count">
                  {{ discussionCount }} {{ discussionCount === 1 ? 'comment' : 'comments' }}
                </span>
                <ReactionsGroup
                  v-if="paper.postId"
                  v-model="postReactions"
                  content-type="post"
                  :content-id="paper.postId"
                />
              </div>
            </div>

            <div class="paper-discussion-composer">
              <CommentEditor
                v-if="paper.postId"
                @submit="postComment"
                :loading="isPostingComment"
                :disabled="!authState.loggedIn || postClosed"
                :show-login-overlay="!authState.loggedIn"
              />
            </div>

            <div v-if="discussionMessage" class="paper-section-note">{{ discussionMessage }}</div>

            <div v-if="isLoadingComments" class="paper-section-note">Loading discussion...</div>
            <div v-else-if="paperComments.length" class="paper-comment-list">
              <CommentItem
                v-for="comment in paperComments"
                :key="comment.id"
                :comment="comment"
                :post-author-id="postAuthorId"
                :post-closed="postClosed"
                @deleted="fetchPaperComments"
              />
            </div>
            <div v-else class="paper-discussion-empty">
              <strong>No reader discussion yet.</strong>
              <span>Start with a question about the method, evidence, dataset, or application.</span>
            </div>
          </section>
        </article>

        <aside class="paper-sidebar">
          <section class="paper-card paper-evaluation-card">
            <div class="paper-card-heading">
              <h3 class="paper-section-title">Evaluation</h3>
              <span class="paper-mini-label">Reader score</span>
            </div>
            <div class="paper-score-panel">
              <div class="paper-score-large">{{ formatScore(paper.scoreSnapshot?.compositeScore) }}</div>
              <div class="paper-score-label">
                Composite score from {{ ratingCount }} {{ ratingCount === 1 ? 'rating' : 'ratings' }}.
              </div>
            </div>
            <div class="paper-score-breakdown">
              <div v-for="row in scoreRows" :key="row.label" class="paper-score-row">
                <span>{{ row.label }}</span>
                <strong>{{ formatScore(row.value) }}</strong>
              </div>
            </div>
          </section>

          <section class="paper-card">
            <h3 class="paper-section-title">Record Metadata</h3>
            <div class="paper-meta-row">
              <span class="paper-pill subject">{{ paper.subjectArea || 'General Research' }}</span>
              <span class="paper-pill">{{ paper.paperType || 'Research Article' }}</span>
              <span class="paper-pill status">{{ normalizeStatus(paper.screeningStatus) }}</span>
              <span v-if="paper.featured" class="paper-pill featured">Featured</span>
              <span v-if="paperRssIncluded(paper)" class="paper-pill">RSS included</span>
            </div>
          </section>

          <section class="paper-card paper-rating-card">
            <div class="paper-card-heading">
              <h3 class="paper-section-title">Rate this paper</h3>
              <span class="paper-mini-label">1-5 scale</span>
            </div>
            <div v-if="!authState.loggedIn" class="paper-abstract">
              Please sign in to rate this paper.
            </div>
            <form v-else class="paper-rating-form" @submit.prevent="submitRating">
              <div class="paper-rating-grid">
                <label class="paper-rating-field">
                  <span>Overall</span>
                  <input v-model.number="rating.overallScore" type="number" min="1" max="5" />
                </label>
                <label class="paper-rating-field">
                  <span>Innovation</span>
                  <input v-model.number="rating.innovationScore" type="number" min="1" max="5" />
                </label>
                <label class="paper-rating-field">
                  <span>Method</span>
                  <input v-model.number="rating.methodScore" type="number" min="1" max="5" />
                </label>
                <label class="paper-rating-field">
                  <span>Impact</span>
                  <input v-model.number="rating.impactScore" type="number" min="1" max="5" />
                </label>
              </div>
              <label class="paper-rating-comment">
                <span>Short assessment</span>
                <textarea
                  v-model="rating.comment"
                  placeholder="What should other readers know about this paper?"
                />
              </label>
              <button class="paper-button primary" type="submit" :disabled="submitting">
                {{ submitting ? 'Submitting...' : 'Submit rating' }}
              </button>
              <div v-if="ratingMessage" class="paper-abstract">{{ ratingMessage }}</div>
            </form>
          </section>
        </aside>
      </section>
    </div>
  </main>
</template>

<script setup>
import '~/assets/paper-platform.css'
import DropdownMenu from '~/components/DropdownMenu.vue'
import { authState, getToken } from '~/utils/auth'
import TimeManager from '~/utils/time'
import { toast } from '~/main'

const route = useRoute()
const { getPaper, ratePaper, runAdminPaperAction, runAdminPostAction, runPostAction } = usePaperApi()
const config = useRuntimeConfig()
const API_BASE_URL = config.public.apiBaseUrl

const paperId = computed(() => route.params.id)

const { data: paperData, refresh } = await useAsyncData(`paper:${paperId.value}`, () =>
  getPaper(paperId.value),
)

const paper = computed(() => paperData.value || {})
const postCore = ref({})
const postReactions = ref([])
const paperComments = ref([])
const isLoadingComments = ref(false)
const isPostingComment = ref(false)
const isUpdatingSubscription = ref(false)
const subscribed = ref(false)
const discussionMessage = ref('')
const postClosed = computed(() => Boolean(postCore.value?.closed))
const postAuthorId = computed(() => postCore.value?.author?.id || paper.value.postId || 0)
const ratingCount = computed(() => paper.value.scoreSnapshot?.ratingCount || 0)
const discussionCount = computed(() => paperComments.value.length)
const authorAffiliations = computed(() => {
  const seen = new Map()
  ;(paper.value.authors || []).forEach((author, index) => {
    const label = authorAffiliation(author, index)
    if (!label || label === 'Affiliation not provided' || seen.has(label)) return
    seen.set(label, {
      key: label,
      index: seen.size + 1,
      label,
    })
  })
  return Array.from(seen.values())
})
const scoreRows = computed(() => {
  const snapshot = paper.value.scoreSnapshot || {}
  return [
    { label: 'Overall', value: snapshot.averageOverallScore },
    { label: 'Innovation', value: snapshot.averageInnovationScore },
    { label: 'Method', value: snapshot.averageMethodScore },
    { label: 'Impact', value: snapshot.averageImpactScore },
  ]
})
const isPostAuthor = computed(() => {
  const author = postCore.value?.author
  if (!author || !authState.loggedIn) return false
  return author.username === authState.username
})
const canSubscribeToDiscussion = computed(
  () =>
    authState.loggedIn &&
    paper.value.postId &&
    !postClosed.value &&
    !isPostAuthor.value &&
    !subscribed.value &&
    !isUpdatingSubscription.value,
)
const canUnsubscribeFromDiscussion = computed(
  () =>
    authState.loggedIn &&
    paper.value.postId &&
    !postClosed.value &&
    !isPostAuthor.value &&
    subscribed.value &&
    !isUpdatingSubscription.value,
)

useHead(() => ({
  title: `${paper.value.title || 'Paper'} - Open Research Evaluation`,
}))

const rating = reactive({
  overallScore: 5,
  innovationScore: 5,
  methodScore: 5,
  impactScore: 5,
  comment: '',
})
const submitting = ref(false)
const ratingMessage = ref('')
const isAdmin = computed(() => authState.role === 'ADMIN')
const canManageDiscussion = computed(() => isAdmin.value || isPostAuthor.value)
const isRunningPaperAction = ref(false)
const paperActionMenuItems = computed(() => {
  if (!paper.value.id || (!isAdmin.value && !canManageDiscussion.value)) return []
  const items = []
  if (canManageDiscussion.value) {
    items.push({
      text: postClosed.value ? 'Reopen discussion' : 'Close discussion',
      onClick: () => runLinkedPostAction(postClosed.value ? 'reopen' : 'close'),
    })
  }
  if (isAdmin.value) {
    items.push({
      text: paper.value.featured ? 'Remove feature' : 'Feature paper',
      onClick: () => runLinkedAdminPostAction(paper.value.featured ? 'unpin' : 'pin'),
    })
    items.push({
      text: paperRssIncluded(paper.value) ? 'Exclude from RSS' : 'Include in RSS',
      onClick: () => runLinkedAdminPostAction(paperRssIncluded(paper.value) ? 'rss-exclude' : 'rss-include'),
    })
  }
  if (isAdmin.value && paper.value.publicationStatus === 'PUBLISHED') {
    items.push({
      text: 'Retract paper',
      color: 'red',
      onClick: () => runPaperAdminAction('retract'),
    })
  }
  if (isAdmin.value) {
    items.push({
      text: 'Open admin workspace',
      onClick: () => navigateTo(`/admin/papers?paperId=${paper.value.id}`),
    })
  }
  return items
})

const submitRating = async () => {
  submitting.value = true
  ratingMessage.value = ''
  try {
    await ratePaper(paperId.value, rating)
    ratingMessage.value = 'Rating submitted. The score has been updated.'
    await refresh()
  } catch (error) {
    ratingMessage.value = 'Unable to submit rating. Please try again.'
  } finally {
    submitting.value = false
  }
}

const tokenHeaders = () => {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

const fetchPostCore = async () => {
  if (!paper.value.postId) return
  try {
    const data = await $fetch(`${API_BASE_URL}/api/posts/${paper.value.postId}`, {
      headers: tokenHeaders(),
    })
    postCore.value = data || {}
    postReactions.value = data?.reactions || []
    subscribed.value = Boolean(data?.subscribed)
  } catch (error) {
    postCore.value = {}
    subscribed.value = Boolean(paper.value.subscribed)
  }
}

const mapComment = (comment, parentUserName = '', parentUserAvatar = '', parentUserId = '') => ({
  id: comment.id,
  userName: comment.author?.username || 'Unknown user',
  medal: comment.author?.displayMedal,
  userId: comment.author?.id,
  time: TimeManager.format(comment.createdAt),
  avatar: comment.author?.avatar,
  text: comment.content,
  reactions: comment.reactions || [],
  pinned: Boolean(comment.pinned ?? comment.pinnedAt ?? comment.pinned_at),
  isBot: Boolean(comment.author?.bot),
  reply: (comment.replies || []).map((reply) =>
    mapComment(reply, comment.author?.username, comment.author?.avatar, comment.author?.id),
  ),
  openReplies: true,
  src: comment.author?.avatar,
  createdAt: comment.createdAt,
  iconClick: () => navigateTo(`/users/${comment.author?.id}`),
  parentUserName,
  parentUserAvatar,
  parentUserId,
})

const fetchPaperComments = async () => {
  if (!paper.value.postId) return
  isLoadingComments.value = true
  try {
    const url = new URL(`${API_BASE_URL}/api/posts/${paper.value.postId}/comments`)
    url.searchParams.set('sort', 'NEWEST')
    url.searchParams.set('page', '0')
    url.searchParams.set('pageSize', '50')
    const data = await $fetch(url.toString(), { headers: tokenHeaders() })
    paperComments.value = (data || [])
      .filter((item) => item.kind === 'comment')
      .map((item) => mapComment(item.payload))
  } catch (error) {
    paperComments.value = []
  } finally {
    isLoadingComments.value = false
  }
}

const postComment = async (parentUserName, text, clear) => {
  if (!text.trim() || !paper.value.postId) return
  const token = getToken()
  if (!token) {
    discussionMessage.value = 'Please sign in before commenting.'
    return
  }

  isPostingComment.value = true
  discussionMessage.value = ''
  try {
    await $fetch(`${API_BASE_URL}/api/posts/${paper.value.postId}/comments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: { content: text },
    })
    clear()
    await fetchPaperComments()
    await fetchPostCore()
  } catch (error) {
    discussionMessage.value = 'Unable to publish comment. Please try again.'
  } finally {
    isPostingComment.value = false
  }
}

const subscribeDiscussion = async () => {
  if (!paper.value.postId || isUpdatingSubscription.value) return
  const token = getToken()
  if (!token) {
    discussionMessage.value = 'Please sign in before following this discussion.'
    return
  }

  isUpdatingSubscription.value = true
  discussionMessage.value = ''
  try {
    await $fetch(`${API_BASE_URL}/api/subscriptions/posts/${paper.value.postId}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })
    subscribed.value = true
    discussionMessage.value = 'You are now following this discussion.'
  } catch (error) {
    discussionMessage.value = 'Unable to follow this discussion. Please try again.'
  } finally {
    isUpdatingSubscription.value = false
  }
}

const unsubscribeDiscussion = async () => {
  if (!paper.value.postId || isUpdatingSubscription.value) return
  const token = getToken()
  if (!token) {
    discussionMessage.value = 'Please sign in before changing discussion notifications.'
    return
  }

  isUpdatingSubscription.value = true
  discussionMessage.value = ''
  try {
    await $fetch(`${API_BASE_URL}/api/subscriptions/posts/${paper.value.postId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    })
    subscribed.value = false
    discussionMessage.value = 'You are no longer following this discussion.'
  } catch (error) {
    discussionMessage.value = 'Unable to update this discussion. Please try again.'
  } finally {
    isUpdatingSubscription.value = false
  }
}

const runPaperAdminAction = async (action) => {
  if (!paper.value.id || isRunningPaperAction.value) return
  isRunningPaperAction.value = true
  discussionMessage.value = ''
  try {
    await runAdminPaperAction(paper.value.id, action)
    if (action === 'retract') {
      toast.success('Paper retracted.')
      await navigateTo(`/admin/papers?paperId=${paper.value.id}`)
      return
    }
    await refresh()
    await fetchPostCore()
    toast.success('Paper updated.')
  } catch (error) {
    toast.error(error?.data?.error || 'Failed to update paper.')
  } finally {
    isRunningPaperAction.value = false
  }
}

const runLinkedAdminPostAction = async (action) => {
  if (!paper.value.postId || isRunningPaperAction.value) return
  isRunningPaperAction.value = true
  discussionMessage.value = ''
  try {
    await runAdminPostAction(paper.value.postId, action)
    await refresh()
    await fetchPostCore()
    toast.success('Paper updated.')
  } catch (error) {
    toast.error(error?.data?.error || 'Failed to update paper.')
  } finally {
    isRunningPaperAction.value = false
  }
}

const runLinkedPostAction = async (action) => {
  if (!paper.value.postId || isRunningPaperAction.value) return
  const token = getToken()
  if (!token) {
    toast.error('Please sign in first.')
    return
  }
  isRunningPaperAction.value = true
  try {
    await runPostAction(paper.value.postId, action)
    await fetchPostCore()
    toast.success(action === 'close' ? 'Discussion closed.' : 'Discussion reopened.')
  } catch (error) {
    toast.error(error?.data?.error || 'Failed to update discussion.')
  } finally {
    isRunningPaperAction.value = false
  }
}

watch(
  () => [paper.value.postId, authState.loggedIn, authState.username],
  async ([postId]) => {
    if (!postId) return
    subscribed.value = Boolean(paper.value.subscribed)
    await Promise.all([fetchPostCore(), fetchPaperComments()])
  },
  { immediate: true },
)

watch(
  () => paper.value.subscribed,
  (value) => {
    subscribed.value = Boolean(value)
  },
  { immediate: true },
)

const formatScore = (value) => Number(value || 0).toFixed(1)
const authorAffiliation = (author, index) => {
  const institution = author?.institution || paper.value.authorInstitutions?.[index]
  const country = author?.country
  if (institution && country) return `${institution}, ${country}`
  return institution || country || 'Affiliation not provided'
}
const authorMarkers = (author, index) => {
  const markers = []
  const affiliation = authorAffiliation(author, index)
  const affiliationIndex = authorAffiliations.value.find((item) => item.label === affiliation)?.index
  if (affiliationIndex) {
    markers.push({
      label: affiliationIndex,
    })
  }
  if (author.equalContribution) {
    markers.push({
      label: '*',
      note: 'Equal contribution.',
    })
  }
  if (author.correspondingAuthor) {
    markers.push({
      label: '†',
      note: `Corresponding author: ${author.displayName || `Author ${index + 1}`}`,
    })
  }
  return markers
}
const paperRssIncluded = (record = {}) => {
  return !record.rssExcluded
}
const formatFileSize = (size) => {
  if (!size) return 'Unknown size'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}
const normalizeStatus = (value) => {
  if (!value) return 'Screened'
  return String(value).replaceAll('_', ' ').toLowerCase()
}
</script>
