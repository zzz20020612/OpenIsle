<template>
  <main class="paper-shell">
    <div class="paper-container literature-detail-container">
      <div class="literature-page-links">
        <NuxtLink class="literature-back" to="/literature">← Back to Knowledge Base</NuxtLink>
        <NuxtLink class="literature-back" to="/papers/rankings">View evaluation rankings →</NuxtLink>
      </div>

      <section v-if="pending" class="paper-card literature-state">Loading literature record…</section>

      <section v-else-if="error" class="paper-card literature-state unavailable" role="alert">
        <strong>Literature record unavailable</strong>
        <p>The record could not be loaded from the knowledge service.</p>
        <button class="paper-button" type="button" @click="refresh()">Try again</button>
      </section>

      <template v-else-if="paper">
        <header class="paper-detail-header paper-panel">
          <div class="paper-page-eyebrow">Existing Literature · Record {{ paper.id }}</div>
          <h1 class="paper-detail-title">{{ paper.title || 'Untitled literature record' }}</h1>
          <p class="literature-authors">{{ formatAuthors(paper.author) }}</p>
          <div class="paper-meta-row">
            <span v-if="paper.journal" class="paper-pill subject">{{ paper.journal }}</span>
            <span v-if="publicationYear" class="paper-pill">{{ publicationYear }}</span>
            <span v-if="paper.source" class="paper-pill">Source: {{ paper.source }}</span>
            <span v-if="paper.citation_count != null" class="paper-pill">
              {{ paper.citation_count }} citations
            </span>
            <a v-if="paper.doi" class="paper-pill literature-doi" :href="doiUrl" target="_blank" rel="noopener">
              DOI {{ paper.doi }}
            </a>
          </div>
        </header>

        <div class="paper-detail-layout">
          <div>
            <section class="paper-block">
              <h2 class="paper-block-title">Abstract</h2>
              <div class="paper-manuscript literature-prose">
                {{ paper.abstract || 'No abstract is available for this record.' }}
              </div>
            </section>

            <section class="paper-block">
              <div class="paper-card-heading">
                <h2 class="paper-block-title">Extracted Knowledge</h2>
                <span class="paper-mini-label">Machine extracted · verify with source</span>
              </div>
              <template v-if="knowledge">
                <KnowledgeField label="Research question" :value="knowledge.research_question" />
                <KnowledgeField label="Core answer" :value="knowledge.core_answer" />
                <KnowledgeField label="Key claims" :value="knowledge.key_claims" />
                <KnowledgeField label="Evidence generation" :value="knowledge.evidence_generation" />
                <KnowledgeField label="Boundaries and limitations" :value="knowledge.boundaries" />
                <KnowledgeField label="Reusable inspiration" :value="knowledge.reusable_inspiration" />
              </template>
              <p v-else class="literature-muted">No knowledge card has been extracted for this record yet.</p>
            </section>

            <section class="paper-block">
              <h2 class="paper-block-title">Methods</h2>
              <template v-if="methods">
                <KnowledgeField label="Methodology" :value="methods.methodology" />
                <KnowledgeField label="Workflow" :value="methods.workflow" />
                <KnowledgeField label="Data sources" :value="methods.data_sources" />
                <KnowledgeField label="Models and algorithms" :value="methods.models_algorithms" />
                <KnowledgeField label="Evaluation metrics" :value="methods.evaluation_metrics" />
              </template>
              <p v-else class="literature-muted">No structured methods have been extracted yet.</p>
            </section>

            <section class="paper-block">
              <h2 class="paper-block-title">Extracted Data Points</h2>
              <div v-if="dataPoints.length" class="literature-data-list">
                <article v-for="point in dataPoints" :key="point.id" class="literature-data-item">
                  <strong>{{ point.metric_name || 'Reported metric' }}</strong>
                  <span class="literature-data-value">
                    {{ point.metric_value || '—' }}{{ point.unit ? ` ${point.unit}` : '' }}
                  </span>
                  <p v-if="point.context">{{ point.context }}</p>
                </article>
              </div>
              <p v-else class="literature-muted">No structured data points have been extracted yet.</p>
            </section>

            <section class="paper-block">
              <div class="paper-card-heading">
                <h2 class="paper-block-title">Reader Evaluations</h2>
                <span class="paper-mini-label">Registered readers · human judgment</span>
              </div>
              <div v-if="ratings.length" class="literature-review-list">
                <article v-for="rating in ratings" :key="rating.ratingId" class="literature-review">
                  <div class="literature-review-head">
                    <span><strong>{{ rating.raterUsername }}</strong><small>{{ formatDate(rating.updatedAt) }}</small></span>
                    <b>{{ ratingAverage(rating) }}</b>
                  </div>
                  <p>{{ rating.comment }}</p>
                  <div class="literature-review-scores">
                    <span v-for="dimension in dimensions" :key="dimension.key">
                      {{ dimension.short }} {{ rating[dimension.key] }}
                    </span>
                  </div>
                </article>
              </div>
              <p v-else class="literature-muted">No human evaluations yet. Be the first registered reader to evaluate this paper.</p>
            </section>
          </div>

          <aside class="paper-sidebar">
            <section class="paper-card literature-rating-card">
              <div class="literature-score-heading">
                <span>
                  <small>Community score</small>
                  <strong>{{ score.ratingCount ? Number(score.compositeScore).toFixed(1) : '—' }}</strong>
                </span>
                <p>{{ score.ratingCount || 0 }} verified {{ score.ratingCount === 1 ? 'rating' : 'ratings' }}</p>
              </div>

              <ClientOnly>
                <template v-if="authState.loggedIn">
                  <h2 class="paper-section-title">{{ myRating ? 'Update your evaluation' : 'Six-dimensional evaluation' }}</h2>
                  <p class="paper-section-note">Scores stay hidden from your form until submission. Each user keeps one active evaluation.</p>
                  <div class="literature-dimensions">
                    <fieldset v-for="dimension in dimensions" :key="dimension.key">
                      <legend><span>{{ dimension.label }}</span><small>{{ dimension.hint }}</small></legend>
                      <div role="group" :aria-label="`${dimension.label} score`">
                        <button
                          v-for="value in 5"
                          :key="value"
                          type="button"
                          :class="{ selected: ratingForm[dimension.key] === value }"
                          :aria-pressed="ratingForm[dimension.key] === value"
                          @click="ratingForm[dimension.key] = value"
                        >{{ value }}</button>
                      </div>
                    </fieldset>
                  </div>
                  <label class="literature-comment-label" for="literature-rating-comment">
                    Evaluation <span>{{ ratingForm.comment.length }}/500</span>
                  </label>
                  <textarea
                    id="literature-rating-comment"
                    v-model="ratingForm.comment"
                    maxlength="500"
                    placeholder="Describe the paper's strengths, limitations, and concrete reasons for your scores (at least 20 characters)."
                  />
                  <label class="literature-read-confirmation">
                    <input v-model="ratingForm.readConfirmed" type="checkbox">
                    <span>I have read the paper's main content and evaluated it independently.</span>
                  </label>
                  <p v-if="ratingError" class="literature-rating-error" role="alert">{{ ratingError }}</p>
                  <p v-if="ratingSuccess" class="literature-rating-success" role="status">Your evaluation has been saved and the ranking recalculated.</p>
                  <button class="paper-button primary literature-submit-rating" type="button" :disabled="!canSubmitRating || submittingRating" @click="submitRating">
                    {{ submittingRating ? 'Saving…' : myRating ? 'Update evaluation' : 'Submit evaluation' }}
                  </button>
                </template>
                <template v-else>
                  <h2 class="paper-section-title">Evaluate this paper</h2>
                  <p class="paper-section-note">Browsing is public. Sign in with a registered OpenIsle account to submit a human evaluation.</p>
                  <NuxtLink class="paper-button primary literature-submit-rating" :to="`/login?redirect=${encodeURIComponent(route.fullPath)}`">Log in to evaluate</NuxtLink>
                </template>
                <template #fallback>
                  <h2 class="paper-section-title">Evaluate this paper</h2>
                  <p class="paper-section-note">Sign in with a registered OpenIsle account to submit a human evaluation.</p>
                </template>
              </ClientOnly>
            </section>

            <section class="paper-card literature-quality">
              <h2 class="paper-section-title">Extraction quality</h2>
              <strong>{{ qualityLabel }}</strong>
              <p>
                This score describes extraction confidence. It is not the platform's scholarly rating or
                ranking score.
              </p>
            </section>

            <section class="paper-card">
              <h2 class="paper-section-title">Record provenance</h2>
              <dl class="literature-facts">
                <div><dt>Source</dt><dd>{{ paper.source || 'Not recorded' }}</dd></div>
                <div><dt>Language</dt><dd>{{ paper.language || 'Not recorded' }}</dd></div>
                <div><dt>Journal tier</dt><dd>{{ paper.journal_tier || 'Not recorded' }}</dd></div>
                <div><dt>Parser</dt><dd>{{ paper.fulltext_meta?.parser_used || 'Not recorded' }}</dd></div>
                <div><dt>Pages</dt><dd>{{ paper.fulltext_meta?.page_count || 'Not recorded' }}</dd></div>
              </dl>
            </section>

            <section class="paper-card">
              <h2 class="paper-section-title">PDF access</h2>
              <p class="paper-section-note">
                Metadata and extracted knowledge are connected. PDF viewing and registered-user downloads
                will be enabled after the source system provides a stable file access contract.
              </p>
            </section>
          </aside>
        </div>
      </template>
    </div>
  </main>
</template>

<script setup>
import '~/assets/paper-platform.css'
import { authState } from '~/utils/auth'

const route = useRoute()
const {
  getLiterature,
  getKnowledge,
  getMethods,
  getDataPoints,
  getScore,
  listRatings,
  getMyRating,
  rateLiterature,
} = useLiteratureApi()
const paperId = computed(() => String(route.params.id))

const dimensions = [
  { key: 'originalityScore', label: 'Originality', short: 'Originality', hint: 'What is genuinely new?' },
  { key: 'rigorScore', label: 'Methodological rigor', short: 'Rigor', hint: 'Are the methods reliable?' },
  { key: 'evidenceScore', label: 'Evidence sufficiency', short: 'Evidence', hint: 'Do the results support the claims?' },
  { key: 'significanceScore', label: 'Scholarly significance', short: 'Significance', hint: 'Does the work matter to the field?' },
  { key: 'reproducibilityScore', label: 'Reproducibility', short: 'Reproducibility', hint: 'Is the process transparent?' },
  { key: 'clarityScore', label: 'Clarity', short: 'Clarity', hint: 'Is the argument understandable?' },
]
const ratingForm = reactive({
  originalityScore: 0,
  rigorScore: 0,
  evidenceScore: 0,
  significanceScore: 0,
  reproducibilityScore: 0,
  clarityScore: 0,
  comment: '',
  readConfirmed: false,
})
const myRating = ref(null)
const submittingRating = ref(false)
const ratingError = ref('')
const ratingSuccess = ref(false)

const { data, pending, error, refresh } = await useAsyncData(
  () => `literature:${paperId.value}`,
  async () => {
    const paper = await getLiterature(paperId.value)
    const [knowledgeResult, methodsResult, dataPointsResult, score, ratings] = await Promise.all([
      getKnowledge(paperId.value).catch(() => null),
      getMethods(paperId.value).catch(() => null),
      getDataPoints(paperId.value).catch(() => null),
      getScore(paperId.value).catch(() => ({})),
      listRatings(paperId.value).catch(() => []),
    ])
    return { paper, knowledgeResult, methodsResult, dataPointsResult, score, ratings }
  },
  { watch: [paperId] },
)

const paper = computed(() => data.value?.paper || null)
const knowledge = computed(() => data.value?.knowledgeResult?.knowledge || null)
const methods = computed(() => data.value?.methodsResult?.methods || null)
const dataPoints = computed(() => data.value?.dataPointsResult?.data_points || [])
const score = computed(() => data.value?.score || {})
const ratings = computed(() => Array.isArray(data.value?.ratings) ? data.value.ratings : [])
const canSubmitRating = computed(() =>
  dimensions.every((dimension) => ratingForm[dimension.key] >= 1) &&
  ratingForm.readConfirmed &&
  ratingForm.comment.trim().length >= 20,
)
const publicationYear = computed(() => {
  const date = paper.value?.published_date
  return date ? String(date).slice(0, 4) : ''
})
const doiUrl = computed(() => `https://doi.org/${paper.value?.doi || ''}`)
const qualityLabel = computed(() => {
  const score = Number(knowledge.value?.quality_score)
  if (!Number.isFinite(score)) return 'Not assessed'
  return score <= 1 ? `${Math.round(score * 100)}%` : score.toFixed(1)
})

useHead(() => ({ title: paper.value?.title ? `${paper.value.title} - Knowledge Base` : 'Literature - OpenIsle' }))

onMounted(async () => {
  if (!authState.loggedIn) return
  try {
    myRating.value = await getMyRating(paperId.value)
    fillRatingForm(myRating.value)
  } catch {
    myRating.value = null
  }
})

function fillRatingForm(rating) {
  if (!rating) return
  dimensions.forEach((dimension) => { ratingForm[dimension.key] = Number(rating[dimension.key] || 0) })
  ratingForm.comment = rating.comment || ''
  ratingForm.readConfirmed = true
}

async function submitRating() {
  if (!canSubmitRating.value || submittingRating.value) return
  submittingRating.value = true
  ratingError.value = ''
  ratingSuccess.value = false
  try {
    myRating.value = await rateLiterature(paperId.value, { ...ratingForm, comment: ratingForm.comment.trim() })
    ratingSuccess.value = true
    await refresh()
  } catch (error) {
    ratingError.value = error?.data?.message || error?.data?.error || 'The evaluation could not be saved. Please try again.'
  } finally {
    submittingRating.value = false
  }
}

function ratingAverage(rating) {
  const total = dimensions.reduce((sum, dimension) => sum + Number(rating?.[dimension.key] || 0), 0)
  return (total / dimensions.length).toFixed(1)
}

function formatDate(value) {
  if (!value) return 'Recently'
  return new Intl.DateTimeFormat('en', { dateStyle: 'medium' }).format(new Date(value))
}

function formatAuthors(value) {
  if (!value) return 'Authors not available'
  if (Array.isArray(value)) {
    const names = value
      .map((author) => {
        if (typeof author === 'string') return author
        return author?.name || author?.full_name ||
          [author?.given || author?.given_name, author?.family || author?.family_name].filter(Boolean).join(' ')
      })
      .filter(Boolean)
    return names.length ? names.join(', ') : 'Authors not available'
  }
  return String(value)
}
</script>

<style scoped>
.literature-detail-container {
  max-width: 1180px;
}

.literature-page-links {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.literature-back {
  display: inline-block;
  margin: 0 0 14px 2px;
  color: var(--paper-muted);
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
}

.literature-back:hover,
.literature-doi:hover {
  color: var(--paper-teal);
}

.literature-authors {
  margin: 14px 0 0;
  color: var(--paper-muted);
  font-family: var(--paper-font-title);
  font-size: 17px;
  line-height: 1.55;
}

.literature-doi {
  text-decoration: none;
}

.literature-prose {
  white-space: pre-line;
}

.literature-muted,
.literature-quality p {
  margin: 0;
  color: var(--paper-muted);
  font-size: 13px;
  line-height: 1.6;
}

.literature-quality > strong {
  display: block;
  margin-bottom: 8px;
  color: var(--paper-green);
  font-size: 30px;
}

.literature-facts {
  display: grid;
  gap: 9px;
  margin: 0;
}

.literature-facts div {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: 10px;
  padding-top: 9px;
  border-top: 1px solid var(--paper-line);
  font-size: 12px;
}

.literature-facts dt {
  color: var(--paper-soft);
}

.literature-facts dd {
  margin: 0;
  color: var(--paper-ink);
  overflow-wrap: anywhere;
}

.literature-data-list {
  display: grid;
  gap: 8px;
}

.literature-data-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 6px 14px;
  padding: 12px 0;
  border-top: 1px solid var(--paper-line);
}

.literature-data-item:first-child {
  border-top: 0;
  padding-top: 0;
}

.literature-data-value {
  color: var(--paper-green);
  font-weight: 760;
}

.literature-data-item p {
  grid-column: 1 / -1;
  margin: 0;
  color: var(--paper-muted);
  font-size: 12px;
  line-height: 1.5;
}

.literature-state {
  text-align: center;
}

.literature-state p {
  color: var(--paper-muted);
}

.literature-score-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 14px;
  padding-bottom: 16px;
  margin-bottom: 18px;
  border-bottom: 1px solid var(--paper-line);
}

.literature-score-heading span {
  display: grid;
}

.literature-score-heading small {
  color: var(--paper-soft);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.literature-score-heading strong {
  color: var(--paper-green);
  font-size: 42px;
  line-height: 1;
}

.literature-score-heading p {
  margin: 0;
  color: var(--paper-muted);
  font-size: 12px;
}

.literature-dimensions {
  display: grid;
  gap: 14px;
  margin: 18px 0;
}

.literature-dimensions fieldset {
  min-width: 0;
  padding: 0;
  border: 0;
}

.literature-dimensions legend {
  display: flex;
  justify-content: space-between;
  width: 100%;
  margin-bottom: 7px;
  color: var(--paper-ink);
  font-size: 12px;
  font-weight: 750;
}

.literature-dimensions legend small {
  color: var(--paper-soft);
  font-weight: 500;
}

.literature-dimensions fieldset > div {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 5px;
}

.literature-dimensions button {
  height: 32px;
  border: 1px solid var(--paper-line-strong);
  border-radius: 7px;
  background: var(--paper-surface);
  color: var(--paper-muted);
  cursor: pointer;
  font-weight: 750;
}

.literature-dimensions button:hover,
.literature-dimensions button.selected {
  border-color: var(--paper-teal);
  background: var(--paper-teal);
  color: white;
}

.literature-comment-label {
  display: flex;
  justify-content: space-between;
  margin-bottom: 7px;
  color: var(--paper-ink);
  font-size: 12px;
  font-weight: 750;
}

.literature-rating-card textarea {
  box-sizing: border-box;
  width: 100%;
  min-height: 116px;
  padding: 11px 12px;
  border: 1px solid var(--paper-line-strong);
  border-radius: 9px;
  background: var(--paper-surface);
  color: var(--paper-ink);
  font: inherit;
  font-size: 13px;
  line-height: 1.55;
  resize: vertical;
}

.literature-read-confirmation {
  display: flex;
  gap: 8px;
  margin: 13px 0;
  color: var(--paper-muted);
  font-size: 12px;
  line-height: 1.45;
}

.literature-read-confirmation input {
  margin-top: 2px;
}

.literature-submit-rating {
  box-sizing: border-box;
  display: flex;
  justify-content: center;
  width: 100%;
}

.literature-submit-rating:disabled {
  cursor: not-allowed;
  opacity: .45;
}

.literature-rating-error,
.literature-rating-success {
  margin: 10px 0;
  font-size: 12px;
  line-height: 1.45;
}

.literature-rating-error { color: #b42318; }
.literature-rating-success { color: var(--paper-green); }

.literature-review-list {
  display: grid;
  gap: 14px;
}

.literature-review {
  padding: 16px;
  border: 1px solid var(--paper-line);
  border-radius: 12px;
  background: var(--paper-surface-soft);
}

.literature-review-head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
}

.literature-review-head span {
  display: grid;
  gap: 2px;
}

.literature-review-head small {
  color: var(--paper-soft);
  font-size: 11px;
}

.literature-review-head b {
  color: var(--paper-green);
  font-size: 24px;
}

.literature-review p {
  margin: 11px 0;
  color: var(--paper-muted);
  font-size: 13px;
  line-height: 1.6;
}

.literature-review-scores {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.literature-review-scores span {
  padding: 4px 7px;
  border-radius: 999px;
  background: var(--paper-surface);
  color: var(--paper-muted);
  font-size: 10px;
  font-weight: 700;
}
</style>
