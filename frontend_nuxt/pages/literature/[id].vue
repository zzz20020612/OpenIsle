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
            <span class="paper-pill" :class="{ subject: paper.completeness?.state === 'complete' }">{{ processingStatusLabel }}</span>
            <span v-if="paper.citation_count != null" class="paper-pill">
              {{ paper.citation_count }} citations
            </span>
            <a v-if="normalizedDoi" class="paper-pill literature-doi" :href="doiUrl" target="_blank" rel="noopener">
              DOI {{ normalizedDoi }}
            </a>
            <a v-if="paper.pdf_available" class="paper-pill literature-doi" :href="pdfViewUrl" target="_blank" rel="noopener">View open PDF</a>
            <button v-if="paper.pdf_available && clientReady && authState.loggedIn" class="paper-pill literature-doi" type="button" @click="downloadPdf">Download PDF</button>
          </div>
        </header>

        <section v-if="paper.completeness?.state !== 'complete'" class="paper-card literature-processing-notice" :class="paper.completeness?.state">
          <strong>{{ processingStatusLabel }}</strong>
          <p>{{ completenessExplanation }}</p>
          <ul v-if="paper.completeness?.reasons?.length">
            <li v-for="reason in paper.completeness.reasons" :key="reason">{{ reason }}</li>
          </ul>
        </section>

        <div class="paper-detail-layout">
          <div>
            <nav class="literature-content-tabs" aria-label="Literature record content">
              <button v-for="tab in contentTabs" :key="tab.id" type="button" :class="{ active: activeContentTab === tab.id }" @click="activeContentTab = tab.id">{{ tab.label }}</button>
            </nav>

            <div class="literature-reading-context">
              <span>{{ activeTabMeta.eyebrow }}</span>
              <p>{{ activeTabMeta.description }}</p>
            </div>

            <section v-show="activeContentTab === 'abstract'" class="paper-block">
              <h2 class="paper-block-title">Abstract</h2>
              <div class="paper-manuscript literature-prose">
                {{ paper.abstract || 'No abstract is available for this record.' }}
              </div>
            </section>

            <section v-show="activeContentTab === 'knowledge'" class="paper-block">
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
              <p v-else class="literature-muted">{{ missingArtifactText('knowledge card') }}</p>
            </section>

            <section v-show="activeContentTab === 'methods'" class="paper-block">
              <h2 class="paper-block-title">Methods</h2>
              <template v-if="methods">
                <KnowledgeField label="Methodology" :value="methods.methodology" />
                <KnowledgeField label="Workflow" :value="methods.workflow" />
                <KnowledgeField label="Data sources" :value="methods.data_sources" />
                <KnowledgeField label="Models and algorithms" :value="methods.models_algorithms" />
                <KnowledgeField label="Evaluation metrics" :value="methods.evaluation_metrics" />
              </template>
              <p v-else class="literature-muted">{{ missingArtifactText('structured methods') }}</p>
            </section>

            <section v-show="activeContentTab === 'data'" class="paper-block">
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

            <section v-show="activeContentTab === 'sections'" class="paper-block">
              <div class="paper-card-heading"><h2 class="paper-block-title">Sections</h2><span class="paper-mini-label">Machine-extracted from the source PDF</span></div>
              <div v-if="sections.length" class="literature-sections">
                <details v-for="(section,index) in sections" :key="section.id || index" class="literature-section" :open="index === 0">
                  <summary><span>{{ section.heading || section.title || `Section ${index + 1}` }}</span><small v-if="section.page_start != null">Pages {{ Number(section.page_start) + 1 }}–{{ Number(section.page_end ?? section.page_start) + 1 }}</small></summary>
                  <div class="paper-manuscript literature-prose">{{ section.text || section.content }}</div>
                </details>
              </div><p v-else class="literature-muted">No parsed sections are available for this record.</p>
            </section>

            <section v-show="activeContentTab === 'figures'" class="paper-block">
              <h2 class="paper-block-title">Figures and Tables</h2>
              <div v-if="figures.length" class="literature-data-list"><article v-for="(figure,index) in figures" :key="figure.id || index" class="literature-data-item"><strong>{{ figure.label || figure.title || `Figure ${index + 1}` }}</strong><p>{{ figure.caption || figure.description || 'Caption unavailable' }}</p></article></div><p v-else class="literature-muted">No figures or tables were extracted.</p>
            </section>

            <section v-show="activeContentTab === 'citations'" class="paper-block">
              <h2 class="paper-block-title">Citations</h2>
              <AdminDataTable :rows="citations" empty="No structured citations are available." />
            </section>

            <details class="paper-block literature-supplement">
              <summary>Authors and related literature</summary>
              <h2 class="paper-block-title">Authors</h2>
              <AdminDataTable :rows="paperAuthors" empty="No structured author records are available." />
              <h2 class="paper-block-title literature-subheading">Similar Literature</h2>
              <div v-if="similar.length" class="literature-data-list"><NuxtLink v-for="item in similar" :key="item.id || item.paper_id" class="literature-similar" :to="`/literature/${item.id || item.paper_id}`"><strong>{{ item.title || item.paper_title }}</strong><span>{{ item.score ?? item.similarity ?? '' }}</span></NuxtLink></div><p v-else class="literature-muted">No similar-paper recommendations are available.</p>
            </details>

            <details class="paper-block literature-supplement">
              <summary>Reader evaluations ({{ ratings.length }})</summary>
              <div class="paper-card-heading literature-supplement-heading">
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
            </details>
          </div>

          <aside class="paper-sidebar">
            <section class="paper-card literature-rating-card">
              <div class="literature-score-heading">
                <span>
                  <small>{{ scoreStatusLabel }}</small>
                  <strong>{{ score.compositeScore == null ? '—' : Number(score.compositeScore).toFixed(2) }}</strong>
                </span>
                <p>{{ score.ratingCount || 0 }} {{ score.ratingCount === 1 ? 'rating' : 'ratings' }} · n_eff {{ Number(score.effectiveSampleSize || 0).toFixed(1) }}</p>
              </div>
              <p class="paper-section-note score-rule-note">
                Rule {{ score.ruleVersion || 'SCHOLARHENG-1.0' }} · weighted 0–5 evaluation.
                <template v-if="score.rankingStatus === 'INITIAL'">Fewer than five ratings: dimension summaries are shown without a single overall score.</template>
                <template v-else-if="score.rankingStatus === 'PROVISIONAL'">This score is provisional and does not enter the formal ranking.</template>
                <template v-else-if="score.rankingStatus === 'FORMAL'">This paper meets the current formal-ranking sample thresholds.</template>
              </p>

              <ClientOnly>
                <details v-if="clientReady && authState.loggedIn" class="literature-evaluate-panel">
                  <summary>{{ myRating ? 'Update your evaluation' : 'Evaluate this paper' }}</summary>
                  <div class="literature-evaluate-body">
                  <h2 class="paper-section-title">{{ myRating ? 'Update your evaluation' : 'Six-dimensional evaluation' }}</h2>
                  <p class="paper-section-note">Scores stay hidden from your form until submission. Each user keeps one active evaluation.</p>
                  <div class="literature-dimensions">
                    <fieldset v-for="dimension in dimensions" :key="dimension.key">
                      <legend><span>{{ dimension.label }}</span><small>{{ dimension.hint }}</small></legend>
                      <div role="group" :aria-label="`${dimension.label} score`">
                        <button
                          v-for="value in scoreOptions"
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
                  </div>
                </details>
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
                <template v-if="paper.pdf_available">The downloaded open PDF is connected to this record and can be viewed here. Registered users can also download it through OpenIsle.</template>
                <template v-else>No open PDF has been downloaded for this record yet. Metadata remains available, and the processing workflow can retry open-access discovery.</template>
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
import { authState, getToken } from '~/utils/auth'

const route = useRoute()
const runtimeConfig = useRuntimeConfig()
const {
  getLiterature,
  getKnowledge,
  getMethods,
  getDataPoints,
  getScore,
  listRatings,
  getMyRating,
  rateLiterature,
  explore,
} = useLiteratureApi()
const paperId = computed(() => String(route.params.id))
const clientReady = ref(false)
const activeContentTab = ref('sections')
const contentTabs = [
  { id: 'abstract', label: 'Abstract' },
  { id: 'sections', label: 'Sections' },
  { id: 'figures', label: 'Figures' },
  { id: 'citations', label: 'Citations' },
  { id: 'knowledge', label: 'Knowledge' },
  { id: 'methods', label: 'Methods' },
  { id: 'data', label: 'Data' },
]
const tabMeta = {
  abstract: { eyebrow: 'Paper overview', description: 'Read the authors’ abstract before checking the extracted evidence.' },
  sections: { eyebrow: 'Full-text reading', description: 'Parsed chapter content from the source PDF. Open one chapter at a time.' },
  figures: { eyebrow: 'Visual evidence', description: 'Figures and tables identified during PDF processing.' },
  citations: { eyebrow: 'Reference trail', description: 'Structured citations linked to this literature record.' },
  knowledge: { eyebrow: 'AI synthesis', description: 'Machine-extracted claims and research insights; verify them against Sections or the PDF.' },
  methods: { eyebrow: 'Method extraction', description: 'A structured view of methodology, workflow, data sources, and evaluation.' },
  data: { eyebrow: 'Reported results', description: 'Quantitative data points detected in the paper.' },
}
const activeTabMeta = computed(() => tabMeta[activeContentTab.value] || tabMeta.sections)

const dimensions = [
  { key: 'originalityScore', label: 'Originality', short: 'Originality', hint: '25% · What is genuinely new?', weight: .25 },
  { key: 'rigorScore', label: 'Methodological rigor', short: 'Rigor', hint: '20% · Are the methods reliable?', weight: .20 },
  { key: 'evidenceScore', label: 'Evidence sufficiency', short: 'Evidence', hint: '20% · Do results support claims?', weight: .20 },
  { key: 'significanceScore', label: 'Scholarly significance', short: 'Significance', hint: '15% · Does the work matter?', weight: .15 },
  { key: 'reproducibilityScore', label: 'Reproducibility', short: 'Reproducibility', hint: '10% · Is the process transparent?', weight: .10 },
  { key: 'clarityScore', label: 'Clarity', short: 'Clarity', hint: '10% · Is the argument clear?', weight: .10 },
]
const scoreOptions = [0, 1, 2, 3, 4, 5]
const ratingForm = reactive({
  originalityScore: null,
  rigorScore: null,
  evidenceScore: null,
  significanceScore: null,
  reproducibilityScore: null,
  clarityScore: null,
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
    const [knowledgeResult, methodsResult, dataPointsResult, score, ratings, citations, authors, similar] = await Promise.all([
      getKnowledge(paperId.value).catch(() => null),
      getMethods(paperId.value).catch(() => null),
      getDataPoints(paperId.value).catch(() => null),
      getScore(paperId.value).catch(() => ({})),
      listRatings(paperId.value).catch(() => []),
      explore(`/paper/${paperId.value}/citations`).catch(() => ({})),
      explore(`/paper/${paperId.value}/authors`).catch(() => ({})),
      explore(`/paper/${paperId.value}/similar`, { top_k: 8 }).catch(() => ({})),
    ])
    return { paper, knowledgeResult, methodsResult, dataPointsResult, score, ratings, citations, authors, similar }
  },
  { watch: [paperId] },
)

const paper = computed(() => data.value?.paper || null)
const knowledge = computed(() => data.value?.knowledgeResult?.knowledge || null)
const methods = computed(() => data.value?.methodsResult?.methods || null)
const dataPoints = computed(() => data.value?.dataPointsResult?.data_points || [])
const score = computed(() => data.value?.score || {})
const ratings = computed(() => Array.isArray(data.value?.ratings) ? data.value.ratings : [])
const sections = computed(() => paper.value?.sections || paper.value?.fulltext?.sections || [])
const figures = computed(() => paper.value?.figures || paper.value?.fulltext?.figures || [])
const citations = computed(() => data.value?.citations?.citations || data.value?.citations?.items || [])
const paperAuthors = computed(() => data.value?.authors?.authors || data.value?.authors?.items || [])
const similar = computed(() => data.value?.similar?.papers || data.value?.similar?.results || data.value?.similar?.items || [])
const canSubmitRating = computed(() =>
  dimensions.every((dimension) => Number.isInteger(ratingForm[dimension.key]) && ratingForm[dimension.key] >= 0 && ratingForm[dimension.key] <= 5) &&
  ratingForm.readConfirmed &&
  ratingForm.comment.trim().length >= 20,
)
const scoreStatusLabel = computed(() => ({
  INITIAL: 'Initial distribution',
  PROVISIONAL: 'Provisional score',
  FORMAL: 'Formal score',
})[score.value.rankingStatus] || 'Research evaluation')
const publicationYear = computed(() => {
  const date = paper.value?.published_date
  return date ? String(date).slice(0, 4) : ''
})
const processingStatusLabel = computed(() => ({
  complete: 'Complete · ready for review',
  processing: 'Processing now',
  retryable: 'Processing can be retried',
  incomplete: 'Processing is incomplete',
  terminal: 'Automatic processing unavailable',
})[paper.value?.completeness?.state] || ({
  extracted: 'PDF parsed · knowledge extracted', partially_extracted: 'Knowledge partially extracted',
  parsed: 'PDF parsed', pdf_downloaded: 'PDF downloaded', metadata_only: 'Metadata only',
})[paper.value?.processing_status] || 'Processing status unavailable')
const completenessExplanation = computed(() => ({
  processing: 'A background task is currently working on this record.',
  retryable: 'The source or processing step failed temporarily. An administrator can retry it from the knowledge workflow.',
  incomplete: 'Some required content is missing or too short for a reliable demonstration.',
  terminal: 'The source cannot currently be processed automatically, for example because no open PDF is available.',
})[paper.value?.completeness?.state] || 'The completeness audit has not run for this record.')
const normalizedDoi = computed(() => {
  const value = String(paper.value?.doi || '').trim()
  if (!/^10\.\d{4,9}\/\S+$/i.test(value)) return ''
  return value
})
const doiUrl = computed(() => normalizedDoi.value ? `https://doi.org/${normalizedDoi.value}` : '')
const pdfViewUrl = computed(() => `${runtimeConfig.public.apiBaseUrl}/api/literature/papers/${paperId.value}/pdf`)
const downloadPdf = async () => {
  const response = await fetch(`${runtimeConfig.public.apiBaseUrl}/api/literature/papers/${paperId.value}/pdf/download`, { headers: { Authorization: `Bearer ${getToken()}` } })
  if (!response.ok) return window.alert('The PDF is not available for download.')
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url; link.download = `literature-${paperId.value}.pdf`; link.click()
  URL.revokeObjectURL(url)
}
const qualityLabel = computed(() => {
  const score = Number(knowledge.value?.quality_score)
  if (!Number.isFinite(score)) return 'Not assessed'
  return score <= 1 ? `${Math.round(score * 100)}%` : score.toFixed(1)
})

function missingArtifactText(name) {
  const completeness = paper.value?.completeness
  if (completeness?.state === 'processing') return `The ${name} is still being generated.`
  if (completeness?.retryable) return `The ${name} is missing. An administrator can retry the ${completeness.stage || 'processing'} stage.`
  if (completeness?.state === 'terminal') return `The ${name} cannot be generated until an accessible source PDF is available.`
  return `No ${name} has been extracted for this record yet.`
}

useHead(() => ({ title: paper.value?.title ? `${paper.value.title} - Knowledge Base` : 'Literature - OpenIsle' }))

onMounted(async () => {
  clientReady.value = true
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
  dimensions.forEach((dimension) => { ratingForm[dimension.key] = Number(rating[dimension.key]) })
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
  return dimensions.reduce((sum, dimension) => sum + Number(rating?.[dimension.key] || 0) * dimension.weight, 0).toFixed(2)
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

.literature-processing-notice { margin: 14px 0; padding: 16px 18px; border-left: 4px solid var(--paper-amber); }
.literature-processing-notice.processing { border-left-color: var(--paper-teal); }
.literature-processing-notice.terminal { border-left-color: #a33d34; }
.literature-processing-notice p { margin: 6px 0; color: var(--paper-muted); }
.literature-processing-notice ul { margin: 8px 0 0; padding-left: 20px; color: var(--paper-muted); font-size: 13px; }

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
.literature-content-tabs{position:sticky;top:0;z-index:3;display:flex;overflow:auto;margin-bottom:0;border:1px solid var(--paper-line);background:var(--paper-line);gap:1px}.literature-content-tabs button{min-width:max-content;border:0;padding:12px 15px;background:#fff;color:var(--paper-muted);font-size:12px;font-weight:800;cursor:pointer}.literature-content-tabs button.active{background:var(--paper-teal);color:#fff}.literature-reading-context{display:flex;align-items:baseline;gap:14px;padding:12px 15px;margin-bottom:14px;border:1px solid var(--paper-line);border-top:0;background:var(--paper-surface-soft)}.literature-reading-context span{flex:0 0 auto;color:var(--paper-teal);font-size:10px;font-weight:850;letter-spacing:.09em;text-transform:uppercase}.literature-reading-context p{margin:0;color:var(--paper-muted);font-size:12px;line-height:1.5}.literature-section{border-top:1px solid var(--paper-line)}.literature-section summary{display:flex;justify-content:space-between;gap:16px;padding:16px 0;cursor:pointer;font:500 19px Georgia,serif}.literature-section summary small{color:var(--paper-soft);font:700 10px var(--paper-font-ui);text-transform:uppercase}.literature-section .paper-manuscript{max-width:72ch;padding:4px 0 24px;font-size:16px;line-height:1.85}.literature-similar{display:flex;justify-content:space-between;gap:14px;padding:12px 0;border-top:1px solid var(--paper-line);color:var(--paper-ink);text-decoration:none}.literature-similar span{color:var(--paper-green)}
.literature-supplement{padding:0}.literature-supplement>summary,.literature-evaluate-panel>summary{padding:16px 18px;color:var(--paper-ink);cursor:pointer;font-weight:800;list-style-position:inside}.literature-supplement[open]{padding:0 18px 18px}.literature-supplement[open]>summary{margin:0 -18px 18px;border-bottom:1px solid var(--paper-line)}.literature-supplement-heading{margin-top:0}.literature-subheading{margin-top:24px}.literature-evaluate-panel{margin-top:8px;border:1px solid var(--paper-line)}.literature-evaluate-panel>summary{color:var(--paper-teal)}.literature-evaluate-body{padding:0 14px 14px}

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
  grid-template-columns: repeat(6, 1fr);
  gap: 5px;
}

.literature-dimensions button {
  height: 32px;
  border: 1px solid var(--paper-line-strong);
  border-radius: 0;
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
  border-radius: 0;
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
.score-rule-note { margin: -6px 0 18px; }

.literature-review-list {
  display: grid;
  gap: 14px;
}

.literature-review {
  padding: 16px;
  border: 1px solid var(--paper-line);
  border-radius: 0;
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
  border-radius: 0;
  background: var(--paper-surface);
  color: var(--paper-muted);
  font-size: 10px;
  font-weight: 700;
}
</style>
