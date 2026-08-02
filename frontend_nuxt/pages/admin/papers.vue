<template>
  <main class="paper-shell">
    <div class="paper-container">
      <header class="paper-workspace-header">
        <div>
          <div class="paper-page-eyebrow">Admin Workspace</div>
          <h1 class="paper-page-title">Paper operations</h1>
          <p class="paper-page-description">
            Monitor published papers, review screening signals, feature strong records, and handle
            moderation actions without turning the platform into a journal workflow.
          </p>
        </div>
        <div class="paper-toolbar">
          <NuxtLink class="paper-button" to="/papers">Public feed</NuxtLink>
          <NuxtLink class="paper-button primary" to="/papers/submit">Submit paper</NuxtLink>
        </div>
      </header>

      <section v-if="!isAdmin" class="paper-card paper-empty">
        Admin access is required to manage papers.
      </section>

      <template v-else>
        <section class="paper-admin-filter paper-panel">
          <label class="paper-filter-field">
            Status
            <select v-model="statusFilter">
              <option value="">All statuses</option>
              <option v-for="status in statusOptions" :key="status" :value="status">
                {{ formatStatus(status) }}
              </option>
            </select>
          </label>
          <button class="paper-button" type="button" @click="refreshAdminPapers">
            Refresh
          </button>
        </section>

        <section class="paper-admin-layout">
          <div class="paper-admin-table paper-panel">
            <div class="paper-admin-row paper-admin-row-head">
              <span>Paper</span>
              <span>Submitter</span>
              <span>Status</span>
              <span>Score</span>
              <span>Featured</span>
              <span>RSS</span>
            </div>

            <button
              v-for="paper in papers"
              :key="paper.id"
              class="paper-admin-row"
              :class="{ active: selectedPaper?.id === paper.id }"
              type="button"
              @click="selectedPaper = paper"
            >
              <span class="paper-admin-paper-cell">
                <strong>{{ paper.title }}</strong>
                <small>{{ formatAuthors(paper.authors) }}</small>
              </span>
              <span>{{ paper.submitterUsername || 'Unknown' }}</span>
              <span>
                <span class="paper-pill" :class="statusClass(paper.publicationStatus)">
                  {{ formatStatus(paper.publicationStatus) }}
                </span>
              </span>
              <span>{{ formatScore(paper.scoreSnapshot?.compositeScore) }}</span>
              <span>{{ paper.pinned ? 'Yes' : 'No' }}</span>
              <span>{{ paper.rssExcluded ? 'Excluded' : 'Included' }}</span>
            </button>

            <div v-if="!pending && papers.length === 0" class="paper-empty compact">
              No papers match this filter.
            </div>
          </div>

          <aside class="paper-admin-detail paper-card">
            <template v-if="selectedPaper">
              <div class="paper-card-heading">
                <h2 class="paper-section-title">Selected Paper</h2>
                <span class="paper-mini-label">#{{ selectedPaper.id }}</span>
              </div>

              <h3 class="paper-admin-detail-title">{{ selectedPaper.title }}</h3>
              <p class="paper-section-note">{{ selectedPaper.abstractText }}</p>

              <div class="paper-admin-meta-grid">
                <div>
                  <span>Subject</span>
                  <strong>{{ selectedPaper.subjectArea || 'Unspecified' }}</strong>
                </div>
                <div>
                  <span>Type</span>
                  <strong>{{ selectedPaper.paperType || 'Research Article' }}</strong>
                </div>
                <div>
                  <span>Screening</span>
                  <strong>{{ formatStatus(selectedPaper.screeningStatus) }}</strong>
                </div>
                <div>
                  <span>Ratings</span>
                  <strong>{{ selectedPaper.scoreSnapshot?.ratingCount || 0 }}</strong>
                </div>
                <div>
                  <span>Feature</span>
                  <strong>{{ selectedPaper.pinned ? 'Featured' : 'Standard' }}</strong>
                </div>
                <div>
                  <span>RSS</span>
                  <strong>{{ selectedPaper.rssExcluded ? 'Excluded' : 'Included' }}</strong>
                </div>
              </div>

              <section class="paper-admin-section">
                <h4>AI screening</h4>
                <p>
                  {{ selectedPaper.screening?.summary || 'No screening summary available yet.' }}
                </p>
                <div class="paper-meta-row">
                  <span class="paper-pill">
                    Risk: {{ selectedPaper.screening?.riskLevel || 'Unknown' }}
                  </span>
                  <span class="paper-pill">
                    Detected: {{ selectedPaper.screening?.detectedSubjectArea || 'Not set' }}
                  </span>
                </div>
                <ul v-if="screeningCoverage.length" class="paper-screening-coverage">
                  <li v-for="item in screeningCoverage" :key="item.id">
                    {{ item.label }}: not run in the text-screening MVP
                  </li>
                </ul>
                <p v-if="selectedPaper.screeningStatus === 'FAILED'" class="paper-screening-error">
                  The screening service failed. The paper was not published or rejected.
                </p>
              </section>

              <section class="paper-admin-section">
                <h4>Platform operations</h4>
                <div class="paper-admin-action-grid">
                  <button
                    class="paper-button primary"
                    type="button"
                    @click="runAction(selectedPaper.pinned ? 'remove-feature' : 'feature')"
                  >
                    {{ selectedPaper.pinned ? 'Remove feature' : 'Feature paper' }}
                  </button>
                  <button
                    class="paper-button"
                    type="button"
                    @click="runAction(selectedPaper.rssExcluded ? 'include-rss' : 'exclude-rss')"
                  >
                    {{ selectedPaper.rssExcluded ? 'Include in RSS' : 'Exclude from RSS' }}
                  </button>
                  <button
                    class="paper-button"
                    type="button"
                    @click="runAction(selectedPaper.discussionClosed ? 'reopen-discussion' : 'close-discussion')"
                  >
                    {{ selectedPaper.discussionClosed ? 'Reopen discussion' : 'Close discussion' }}
                  </button>
                  <button
                    v-if="selectedPaper.publicationStatus === 'PUBLISHED'"
                    class="paper-button danger"
                    type="button"
                    @click="runAction('retract')"
                  >
                    Retract paper
                  </button>
                  <NuxtLink class="paper-button" :to="`/papers/${selectedPaper.id}`">
                    View public page
                  </NuxtLink>
                </div>
              </section>
            </template>

            <div v-else class="paper-empty compact">
              Select a paper to review screening signals, feature status, moderation controls, and
              the public paper page.
            </div>
          </aside>
        </section>
      </template>
    </div>
  </main>
</template>

<script setup>
import '~/assets/paper-platform.css'
import { authState } from '~/utils/auth'
import { toast } from '~/main'

useHead({
  title: 'Paper Admin - Open Research Evaluation',
})

const route = useRoute()
const {
  listAdminPapers,
  runAdminPaperAction,
  clearPublicPaperCache,
  runAdminPostAction,
  runPostAction,
} = usePaperApi()
const statusOptions = [
  'DRAFT',
  'SCREENING',
  'PUBLISHED',
  'NEEDS_REVISION',
  'REJECTED',
  'WITHDRAWN',
  'RETRACTED',
]

const statusFilter = ref('')
const selectedPaper = ref(null)
const isAdmin = computed(() => authState.role === 'ADMIN')
const adminQuery = computed(() => ({
  page: 0,
  pageSize: 50,
  status: statusFilter.value || undefined,
}))

const {
  data: paperData,
  pending,
  refresh,
} = await useAsyncData(
  'admin:papers',
  () => (isAdmin.value ? listAdminPapers(adminQuery.value) : []),
  { watch: [adminQuery, isAdmin] },
)

const papers = computed(() => (Array.isArray(paperData.value) ? paperData.value : []))

const screeningCoverage = computed(() => {
  const raw = selectedPaper.value?.screening?.issuesJson
  if (!raw) return []
  try {
    const dimensions = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (!Array.isArray(dimensions)) return []
    const labels = { '02': 'Plagiarism check', '03': 'Image integrity check' }
    return dimensions
      .filter((item) => item?.status === 'skipped' && labels[item.dimension_id])
      .map((item) => ({ id: item.dimension_id, label: labels[item.dimension_id] }))
  } catch {
    return []
  }
})

watch(
  papers,
  (items) => {
    if (!items.length) {
      selectedPaper.value = null
      return
    }
    const queryPaperId = Number(route.query.paperId)
    if (queryPaperId) {
      const queryPaper = items.find((paper) => paper.id === queryPaperId)
      if (queryPaper) {
        selectedPaper.value = queryPaper
        return
      }
    }
    if (!selectedPaper.value || !items.some((paper) => paper.id === selectedPaper.value.id)) {
      selectedPaper.value = items[0]
    } else {
      selectedPaper.value = items.find((paper) => paper.id === selectedPaper.value.id)
    }
  },
  { immediate: true },
)

const refreshAdminPapers = async () => {
  await refresh()
}

const runAction = async (action) => {
  if (!selectedPaper.value) return
  try {
    if (action === 'retract') {
      selectedPaper.value = await runAdminPaperAction(selectedPaper.value.id, action)
      clearPublicPaperCache()
    } else if (action === 'feature' || action === 'remove-feature') {
      await runAdminPostAction(selectedPaper.value.postId, action === 'feature' ? 'pin' : 'unpin')
    } else if (action === 'include-rss' || action === 'exclude-rss') {
      await runAdminPostAction(selectedPaper.value.postId, action === 'include-rss' ? 'rss-include' : 'rss-exclude')
    } else if (action === 'close-discussion' || action === 'reopen-discussion') {
      await runPostAction(selectedPaper.value.postId, action === 'close-discussion' ? 'close' : 'reopen')
    }
    await refresh()
    toast.success('Paper updated.')
  } catch (error) {
    toast.error(error?.data?.error || 'Failed to update paper.')
  }
}

const formatAuthors = (authors = []) => {
  if (!authors.length) return 'No authors recorded'
  const names = authors.map((author) => author.displayName || author).filter(Boolean)
  if (names.length <= 3) return names.join(', ')
  return `${names.slice(0, 3).join(', ')} et al.`
}

const formatStatus = (value) => {
  if (!value) return 'Not set'
  return String(value)
    .replaceAll('_', ' ')
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

const formatScore = (value) => Number(value || 0).toFixed(1)
const statusClass = (status) => ({
  status: status === 'PUBLISHED',
  warning: status === 'SCREENING' || status === 'NEEDS_REVISION',
  danger: status === 'REJECTED' || status === 'RETRACTED',
})
</script>
