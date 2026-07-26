<template>
  <main class="journal-page">
    <div class="journal-container">
      <header class="journal-topbar">
        <NuxtLink to="/papers">Papers</NuxtLink>
        <nav>
          <NuxtLink to="/papers/rankings">Rankings</NuxtLink>
          <NuxtLink to="/experts">Experts</NuxtLink>
        </nav>
      </header>

      <article class="journal-record-header">
        <div class="journal-record-meta">
          <span>{{ paper.paperType || 'Research Article' }}</span>
          <span>{{ paper.subjectArea || 'Research' }}</span>
          <span>Published research record</span>
        </div>
        <h1>{{ paper.title }}</h1>
        <div class="paper-citation-authors" aria-label="Paper authors">
          <span
            v-for="(author, index) in paper.authors || []"
            :key="author.id || `${author.displayName || author}-${index}`"
            class="paper-citation-author"
          >
            <NuxtLink v-if="author.expertProfileId" :to="`/experts/${author.expertProfileId}`">
              {{ author.displayName || `Author ${index + 1}` }}
            </NuxtLink>
            <NuxtLink v-else-if="author.userId" :to="`/users/${author.userId}`">
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
        <a
          v-if="correspondingAuthor?.email"
          class="journal-corresponding-email"
          :href="`mailto:${correspondingAuthor.email}`"
        >Correspondence: {{ correspondingAuthor.email }}</a>

        <div class="journal-action-row">
          <button
            v-if="primaryManuscript"
            type="button"
            class="journal-primary-action"
            @click="openPaperFile(primaryManuscript, 'download')"
          >
            <Download :size="17" /> Download Manuscript
          </button>
          <button
            v-if="firstPreviewableSi"
            type="button"
            class="journal-action"
            @click="openPaperFile(firstPreviewableSi, 'preview')"
          >
            <PreviewOpen :size="17" /> Preview Supporting Information
          </button>
          <button
            v-if="canSubscribeToDiscussion"
            class="journal-action"
            type="button"
            @click="subscribeDiscussion"
          >Follow paper</button>
          <button
            v-else-if="canUnsubscribeFromDiscussion"
            class="journal-action active"
            type="button"
            @click="unsubscribeDiscussion"
          >Following</button>
          <NuxtLink v-else-if="!authState.loggedIn" class="journal-action" to="/login">
            Sign in to follow
          </NuxtLink>
          <DropdownMenu v-if="paperActionMenuItems.length > 0" :items="paperActionMenuItems">
            <template #trigger><more-one class="paper-action-menu-icon" /></template>
          </DropdownMenu>
        </div>
      </article>

      <section class="journal-layout">
        <article class="journal-article">
          <section id="abstract" class="journal-section">
            <h2>Abstract</h2>
            <p class="journal-abstract">{{ paper.abstractText }}</p>
            <div v-if="paper.keywords?.length" class="journal-keywords">
              <span v-for="keyword in paper.keywords" :key="keyword">{{ keyword }}</span>
            </div>
          </section>

          <section v-if="paper.tocGraphic?.id" id="toc-graphic" class="journal-section">
            <h2>TOC Graphic</h2>
            <figure class="journal-toc-figure">
              <img
                :src="contentUrl(paper.tocGraphic, 'preview')"
                :alt="paper.tocGraphic.description || `TOC graphic for ${paper.title}`"
              />
              <figcaption v-if="paper.tocGraphic.description">{{ paper.tocGraphic.description }}</figcaption>
            </figure>
          </section>

          <section v-if="article?.sections?.length" id="article-content" class="journal-section journal-full-article">
            <div class="journal-full-article-heading">
              <div>
                <h2>Article</h2>
                <p>Read the structured online version of this manuscript.</p>
              </div>
              <details class="article-contents-menu">
                <summary>Contents</summary>
                <nav><a v-for="section in article.sections" :key="section.key" :href="`#${section.key}`">{{ section.heading }}</a></nav>
              </details>
            </div>
            <PaperArticleRenderer :article="article" :figure-source="figureSource" />
          </section>

          <section id="files" class="journal-section">
            <h2>Manuscript & Supporting Information</h2>
            <div v-if="allPublicFiles.length" class="journal-file-list">
              <article v-for="file in allPublicFiles" :key="file.id || file.fileName" class="journal-file-row">
                <FileText :size="20" />
                <div>
                  <strong>{{ file.displayName || file.fileName }}</strong>
                  <span>{{ fileRoleLabel(file.fileRole) }} · {{ formatFileSize(file.fileSize) }}</span>
                  <p v-if="file.description">{{ file.description }}</p>
                  <small v-if="file.id">{{ file.viewCount || 0 }} views · {{ file.downloadCount || 0 }} downloads</small>
                </div>
                <div v-if="file.id || file.url" class="journal-file-actions">
                  <button
                    v-if="file.previewable"
                    type="button"
                    title="Preview file"
                    aria-label="Preview file"
                    @click="openPaperFile(file, 'preview')"
                  ><PreviewOpen :size="17" /></button>
                  <button
                    type="button"
                    title="Download file"
                    aria-label="Download file"
                    @click="openPaperFile(file, 'download')"
                  ><Download :size="17" /></button>
                </div>
              </article>
            </div>
            <p v-else class="journal-empty">No downloadable files are available for this record.</p>
          </section>

          <section id="authors" class="journal-section">
            <h2>Author Information</h2>
            <div class="journal-author-list">
              <article v-for="(author, index) in paper.authors || []" :key="author.id || index">
                <div class="journal-author-index">{{ index + 1 }}</div>
                <div>
                  <h3>{{ author.displayName }}</h3>
                  <p>
                    {{ author.correspondingAuthor ? 'Corresponding Author' : 'Author' }}
                    <template v-if="author.equalContribution"> · Equal contribution</template>
                  </p>
                  <ul v-if="author.affiliations?.length">
                    <li v-for="affiliation in author.affiliations" :key="affiliation.id || affiliation.displayOrder">
                      {{ affiliation.organizationName }}<template v-if="affiliation.department">, {{ affiliation.department }}</template>
                      · {{ [affiliation.city, affiliation.region, affiliation.country].filter(Boolean).join(', ') }}
                    </li>
                  </ul>
                  <div v-if="author.contributionRoles?.length" class="journal-credit-roles">
                    <span v-for="role in author.contributionRoles" :key="role">{{ role }}</span>
                  </div>
                </div>
              </article>
            </div>
          </section>

          <section id="declarations" class="journal-section">
            <h2>Funding & Declarations</h2>
            <dl class="journal-declarations">
              <div>
                <dt>Funding</dt>
                <dd v-if="paper.funding?.length">
                  <span v-for="item in paper.funding" :key="item.id || item.funderName">
                    {{ item.funderName }}<template v-if="item.grantId"> ({{ item.grantId }})</template>
                  </span>
                </dd>
                <dd v-else>{{ paper.fundingStatement || 'No funding information provided.' }}</dd>
              </div>
              <div><dt>Conflict of Interest</dt><dd>{{ paper.conflictOfInterest || 'Not provided.' }}</dd></div>
              <div><dt>Data Availability</dt><dd>{{ paper.dataAvailability || 'Not provided.' }}</dd></div>
              <div><dt>Ethics Statement</dt><dd>{{ paper.ethicsStatement || 'Not provided.' }}</dd></div>
              <div><dt>Preprint or Prior Posting</dt><dd>{{ paper.preprintStatement || 'Not provided.' }}</dd></div>
              <div><dt>AI Tool Use</dt><dd>{{ paper.aiUseDisclosure || 'Not provided.' }}</dd></div>
            </dl>
          </section>

          <section id="discussion" class="paper-block paper-discussion-block">
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
          <nav class="journal-jump-nav" aria-label="On this page">
            <strong>On this page</strong>
            <a href="#abstract">Abstract</a>
            <a v-if="paper.tocGraphic?.id" href="#toc-graphic">TOC Graphic</a>
            <a href="#files">Files</a>
            <a href="#authors">Authors</a>
            <a href="#declarations">Declarations</a>
            <a href="#discussion">Reader Discussion</a>
          </nav>
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

    <Teleport to="body">
      <div v-if="previewFile" class="journal-viewer-backdrop" @click.self="closePreview">
        <section class="journal-viewer" role="dialog" aria-modal="true" aria-label="File preview">
          <header>
            <div>
              <strong>{{ previewFile.displayName || previewFile.fileName }}</strong>
              <span>{{ previewFile.description || fileRoleLabel(previewFile.fileRole) }}</span>
            </div>
            <div>
              <button
                type="button"
                title="Download file"
                aria-label="Download file"
                @click="openPaperFile(previewFile, 'download')"
              ><Download :size="18" /></button>
              <button
                type="button"
                title="Close preview"
                aria-label="Close preview"
                @click="closePreview"
              ><CloseOne :size="18" /></button>
            </div>
          </header>
          <iframe :src="previewUrl" :title="`Preview ${previewFile.displayName || previewFile.fileName}`"></iframe>
        </section>
      </div>
    </Teleport>
  </main>
</template>

<script setup>
import { CloseOne, Download, FileText, PreviewOpen } from '@icon-park/vue-next'
import '~/assets/paper-platform.css'
import DropdownMenu from '~/components/DropdownMenu.vue'
import { authState, getToken } from '~/utils/auth'
import TimeManager from '~/utils/time'
import PaperArticleRenderer from '~/components/paper-article/PaperArticleRenderer.vue'
import { toast } from '~/main'

const route = useRoute()
const {
  getPaper,
  ratePaper,
  runAdminPaperAction,
  runAdminPostAction,
  runPostAction,
  clearPublicPaperCache,
  paperFileContentUrl,
  getPaperArticle,
} = usePaperApi()
const config = useRuntimeConfig()
const API_BASE_URL = config.public.apiBaseUrl

const paperId = computed(() => route.params.id)

const { data: paperData, error: paperError, refresh } = await useAsyncData(`paper:${paperId.value}`, () =>
  getPaper(paperId.value),
)

if (paperError.value) {
  throw createError({
    statusCode: paperError.value.statusCode || 404,
    statusMessage: paperError.value.statusMessage || 'Paper not found',
    fatal: true,
  })
}

const paper = computed(() => paperData.value || {})
const { data: articleData } = await useAsyncData(`paper-article:${paperId.value}`, () =>
  getPaperArticle(paperId.value).catch(() => ({ sections: [] })),
)
const article = computed(() => articleData.value || { sections: [] })
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
const previewFile = ref(null)
const previewUrl = ref('')
const previewObjectUrl = ref('')
const allPublicFiles = computed(() => {
  const seen = new Set()
  return [...(paper.value.manuscriptFiles || []), ...(paper.value.supplementaryFiles || [])]
    .filter((file) => {
      const key = file.id || `${file.fileRole}-${file.fileName}`
      if (seen.has(key)) return false
      seen.add(key)
      return file.fileRole !== 'TOC_GRAPHIC'
    })
})
const figureFiles = computed(() => [...(paper.value.manuscriptFiles || []), ...(paper.value.supplementaryFiles || [])])
const primaryManuscript = computed(() =>
  (paper.value.manuscriptFiles || []).find((file) =>
    file.fileRole === 'MANUSCRIPT' || /manuscript/i.test(file.fileRole || ''),
  ),
)
const firstPreviewableSi = computed(() =>
  (paper.value.supplementaryFiles || []).find((file) =>
    file.previewable && file.fileRole === 'SUPPORTING_INFORMATION',
  ),
)
const correspondingAuthor = computed(() =>
  (paper.value.authors || []).find((author) => author.correspondingAuthor),
)
const authorAffiliations = computed(() => {
  const seen = new Map()
  ;(paper.value.authors || []).forEach((author, authorIndex) => {
    const affiliations = author.affiliations?.length
      ? author.affiliations
      : [{ organizationName: authorAffiliation(author, authorIndex) }]
    affiliations.forEach((affiliation) => {
      const label = normalizedAffiliationLabel(affiliation)
      if (!label || label === 'Affiliation not provided' || seen.has(label)) return
      seen.set(label, { key: label, index: seen.size + 1, label })
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
      clearPublicPaperCache()
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
const normalizedAffiliationLabel = (affiliation = {}) => {
  const organization = affiliation.organizationName || affiliation.institution
  const location = [affiliation.city, affiliation.region, affiliation.country].filter(Boolean).join(', ')
  if (organization && location) return `${organization}, ${location}`
  return organization || location || 'Affiliation not provided'
}
const authorMarkers = (author, index) => {
  const affiliations = author.affiliations?.length
    ? author.affiliations
    : [{ organizationName: authorAffiliation(author, index) }]
  const markers = affiliations
    .map(normalizedAffiliationLabel)
    .map((label) => authorAffiliations.value.find((item) => item.label === label)?.index)
    .filter(Boolean)
    .map((label) => ({ label }))
  if (author.equalContribution) {
    markers.push({
      label: '*',
      note: 'Equal contribution.',
    })
  }
  if (author.correspondingAuthor) {
    markers.push({
      label: '†',
      note: author.email
        ? `Corresponding author: ${author.displayName || `Author ${index + 1}`} (${author.email})`
        : `Corresponding author: ${author.displayName || `Author ${index + 1}`}`,
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
const fileRoleLabel = (role) => {
  const labels = {
    MANUSCRIPT: 'Manuscript',
    COVER_LETTER: 'Cover Letter',
    TOC_GRAPHIC: 'TOC Graphic',
    SUPPORTING_INFORMATION: 'Supporting Information',
    REVIEW_ONLY: 'Review Only',
    PDF_VERSION: 'PDF Version',
    LATEX_SOURCE: 'LaTeX Source',
    DATASET: 'Dataset',
    CODE: 'Code',
    OTHER: 'Other',
  }
  return labels[role] || String(role || 'File').replaceAll('_', ' ')
}
const contentUrl = (file, mode = 'download') => {
  if (file?.url) return file.url
  if (!file?.id) return ''
  return paperFileContentUrl(paperId.value, file.id, mode)
}
const figureSource = (block) => {
  const file = figureFiles.value.find((item) => String(item.id) === String(block.fileId))
  return file ? contentUrl(file, 'preview') : ''
}
const closePreview = () => {
  previewFile.value = null
  previewUrl.value = ''
  if (previewObjectUrl.value) {
    URL.revokeObjectURL(previewObjectUrl.value)
    previewObjectUrl.value = ''
  }
  if (process.client) document.body.style.overflow = ''
}
const downloadBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename || 'paper-file'
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
const openPaperFile = async (file, mode = 'download') => {
  const url = contentUrl(file, mode)
  if (!url) return
  try {
    if (file.visibility === 'PRIVATE') {
      const response = await fetch(url, { headers: tokenHeaders() })
      if (!response.ok) throw new Error(`File request failed with status ${response.status}`)
      const blob = await response.blob()
      if (mode === 'preview') {
        closePreview()
        previewObjectUrl.value = URL.createObjectURL(blob)
        previewUrl.value = previewObjectUrl.value
        previewFile.value = file
        document.body.style.overflow = 'hidden'
      } else {
        downloadBlob(blob, file.displayName || file.fileName)
      }
      return
    }
    if (mode === 'preview') {
      closePreview()
      previewFile.value = file
      previewUrl.value = url
      document.body.style.overflow = 'hidden'
    } else {
      window.open(url, '_blank', 'noopener,noreferrer')
    }
  } catch (error) {
    toast.error(error?.message || 'Unable to open this file.')
  }
}
const handlePreviewKeydown = (event) => {
  if (event.key === 'Escape' && previewFile.value) closePreview()
}
onMounted(() => window.addEventListener('keydown', handlePreviewKeydown))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', handlePreviewKeydown)
  closePreview()
})
const normalizeStatus = (value) => {
  if (!value) return 'Screened'
  return String(value).replaceAll('_', ' ').toLowerCase()
}
</script>

<style scoped>
.journal-page { min-height: 100vh; background: #f4f5f4; color: #17232a; padding: 0 20px 64px; }
.journal-container { width: min(1280px, 100%); margin: 0 auto; background: #fff; border-right: 1px solid #dde1e2; border-left: 1px solid #dde1e2; }
.journal-topbar { min-height: 52px; display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 0 30px; border-bottom: 1px solid #d9dedf; background: #f8f9f8; }
.journal-topbar a { color: #315667; font-size: 13px; font-weight: 750; text-decoration: none; }
.journal-topbar > a::before { content: '← '; }
.journal-topbar nav { display: flex; gap: 18px; }
.journal-record-header { padding: 34px 44px 28px; border-bottom: 3px solid #273b45; }
.journal-record-meta { display: flex; flex-wrap: wrap; gap: 0; margin-bottom: 16px; color: #5f6d74; font-size: 12px; font-weight: 750; text-transform: uppercase; }
.journal-record-meta span + span::before { content: '·'; margin: 0 9px; color: #9aa4a9; }
.journal-record-header h1 { max-width: 1000px; margin: 0 0 18px; color: #142127; font-family: Georgia, 'Times New Roman', serif; font-size: 40px; font-weight: 500; line-height: 1.18; letter-spacing: 0; }
.journal-corresponding-email { display: inline-block; margin-top: 12px; color: #2a627a; font-size: 12px; font-weight: 700; text-decoration: none; }
.journal-action-row { display: flex; flex-wrap: wrap; align-items: center; gap: 9px; margin-top: 24px; padding-top: 18px; border-top: 1px solid #dce1e3; }
.journal-primary-action, .journal-action { min-height: 42px; display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 8px 13px; font-size: 12px; font-weight: 800; text-decoration: none; cursor: pointer; }
.journal-primary-action { border: 1px solid #1b5269; background: #205f79; color: #fff; }
.journal-action { border: 1px solid #b9c4c9; background: #fff; color: #32454f; }
.journal-action.active { border-color: #5b8065; color: #376348; background: #f1f7f2; }
.journal-layout { display: grid; grid-template-columns: minmax(0, 1fr) 310px; align-items: start; }
.journal-article { min-width: 0; padding: 0 44px 30px; border-right: 1px solid #dce1e3; }
.journal-section { scroll-margin-top: 80px; padding: 30px 0; border-bottom: 1px solid #dce1e3; }
.journal-section h2 { margin: 0 0 18px; color: #21323b; font-family: Georgia, 'Times New Roman', serif; font-size: 25px; font-weight: 500; letter-spacing: 0; }
.journal-abstract { max-width: 78ch; margin: 0; color: #26363e; font-family: Georgia, 'Times New Roman', serif; font-size: 17px; line-height: 1.72; white-space: pre-line; }
.journal-keywords { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 20px; }
.journal-keywords span { padding: 5px 8px; border: 1px solid #cad4d8; background: #f0f4f5; color: #31586a; font-size: 12px; font-weight: 750; }
.journal-toc-figure { width: min(720px, 100%); margin: 0; }
.journal-toc-figure img { display: block; max-width: 100%; max-height: 520px; object-fit: contain; border: 1px solid #d5dbde; background: #fff; }
.journal-toc-figure figcaption { margin-top: 8px; color: #66737a; font-size: 12px; line-height: 1.45; }
.journal-full-article-heading { display: flex; align-items: start; justify-content: space-between; gap: 18px; }
.journal-full-article-heading p { margin: -10px 0 18px; color: #68747c; font-size: 13px; }
.article-contents-menu { position: relative; flex: 0 0 auto; }
.article-contents-menu summary { padding: 8px 10px; border: 1px solid #bdcbd0; color: #31586a; font-size: 12px; font-weight: 750; cursor: pointer; }
.article-contents-menu nav { position: absolute; z-index: 2; right: 0; width: 230px; display: grid; gap: 2px; padding: 10px; border: 1px solid #cbd5d9; background: #fff; box-shadow: 0 6px 18px rgba(31, 48, 58, .12); }
.article-contents-menu a { padding: 5px 3px; color: #52646e; font-size: 12px; text-decoration: none; }
.article-contents-menu a:hover { color: #1f617f; }
.journal-file-list { border: 1px solid #d2d9dc; border-bottom: 0; }
.journal-file-row { display: grid; grid-template-columns: 26px minmax(0, 1fr) auto; gap: 11px; align-items: start; padding: 14px; border-bottom: 1px solid #d2d9dc; }
.journal-file-row > svg { margin-top: 2px; color: #4c6877; }
.journal-file-row > div:nth-child(2) { display: grid; gap: 3px; min-width: 0; }
.journal-file-row strong { overflow-wrap: anywhere; }
.journal-file-row span, .journal-file-row p, .journal-file-row small { margin: 0; color: #68757c; font-size: 12px; line-height: 1.45; }
.journal-file-actions { display: grid; grid-template-columns: repeat(2, 36px); gap: 6px; }
.journal-file-actions button { width: 36px; height: 36px; display: grid; place-items: center; border: 1px solid #bdc7cc; background: #fff; color: #34505e; cursor: pointer; }
.journal-empty { margin: 0; color: #69757c; font-size: 13px; }
.journal-author-list { border-top: 1px solid #d6dcdf; }
.journal-author-list > article { display: grid; grid-template-columns: 42px minmax(0, 1fr); border-bottom: 1px solid #d6dcdf; }
.journal-author-index { display: grid; place-items: start center; padding-top: 16px; border-right: 1px solid #e0e4e6; color: #68757c; font-size: 12px; font-weight: 800; }
.journal-author-list > article > div:last-child { padding: 14px 16px; }
.journal-author-list h3 { margin: 0; font-size: 15px; }
.journal-author-list p { margin: 4px 0; color: #66737b; font-size: 12px; }
.journal-author-list ul { margin: 8px 0 0; padding-left: 18px; color: #41515a; font-size: 12px; line-height: 1.5; }
.journal-credit-roles { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 10px; }
.journal-credit-roles span { padding: 3px 6px; background: #f1f3f3; color: #5c686f; font-size: 10px; }
.journal-declarations { display: grid; gap: 20px; margin: 0; }
.journal-declarations > div { display: grid; grid-template-columns: 180px minmax(0, 1fr); gap: 18px; }
.journal-declarations dt { color: #3a4a52; font-size: 12px; font-weight: 800; }
.journal-declarations dd { margin: 0; color: #34434b; font-size: 13px; line-height: 1.6; white-space: pre-line; }
.journal-declarations dd span { display: block; }
.journal-article > :deep(.paper-block) { margin: 30px 0 0; border: 0; border-top: 2px solid #344d59; border-radius: 0; padding: 28px 0 0; box-shadow: none; }
.journal-layout > :deep(.paper-sidebar) { position: sticky; top: 70px; padding: 24px 20px; }
.journal-jump-nav { display: grid; gap: 0; margin-bottom: 18px; padding-bottom: 14px; border-bottom: 1px solid #d8dfe2; }
.journal-jump-nav strong { margin-bottom: 7px; color: #2d414b; font-size: 12px; text-transform: uppercase; }
.journal-jump-nav a { padding: 6px 0; color: #52646e; font-size: 12px; text-decoration: none; }
.journal-jump-nav a:hover { color: #1f617f; }
.journal-viewer-backdrop { position: fixed; z-index: 2000; inset: 0; display: grid; place-items: center; padding: 18px; background: rgba(18, 27, 32, .78); }
.journal-viewer { width: min(1180px, 100%); height: min(900px, calc(100vh - 36px)); display: grid; grid-template-rows: auto minmax(0, 1fr); background: #fff; }
.journal-viewer > header { min-height: 58px; display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 10px 14px; border-bottom: 1px solid #d5dcdf; }
.journal-viewer > header > div:first-child { display: grid; gap: 2px; min-width: 0; }
.journal-viewer > header strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.journal-viewer > header span { color: #69757c; font-size: 12px; }
.journal-viewer > header > div:last-child { display: flex; gap: 7px; }
.journal-viewer button { width: 38px; height: 38px; display: grid; place-items: center; border: 1px solid #bdc7cc; background: #fff; color: #334c59; cursor: pointer; }
.journal-viewer iframe { width: 100%; height: 100%; border: 0; background: #e8ebec; }
button:focus-visible, a:focus-visible { outline: 3px solid rgba(31, 104, 139, .25); outline-offset: 1px; }
@media (max-width: 960px) {
  .journal-layout { grid-template-columns: 1fr; }
  .journal-article { border-right: 0; }
  .journal-layout > :deep(.paper-sidebar) { position: static; border-top: 1px solid #dce1e3; }
}
@media (max-width: 680px) {
  .journal-page { padding: 0 0 40px; }
  .journal-container { border: 0; }
  .journal-topbar { padding: 0 16px; }
  .journal-record-header { padding: 26px 16px 22px; }
  .journal-record-header h1 { font-size: 30px; }
  .journal-article { padding: 0 16px 24px; }
  .journal-section { padding: 24px 0; }
  .journal-declarations > div { grid-template-columns: 1fr; gap: 5px; }
  .journal-file-row { grid-template-columns: 24px minmax(0, 1fr); }
  .journal-file-actions { grid-column: 2; justify-content: start; }
  .journal-action-row > * { width: 100%; }
  .journal-viewer-backdrop { padding: 0; }
  .journal-viewer { width: 100%; height: 100vh; }
}
</style>
