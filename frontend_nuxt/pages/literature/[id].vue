<template>
  <main class="paper-shell">
    <div class="paper-container literature-detail-container">
      <NuxtLink class="literature-back" to="/literature">← Back to Knowledge Base</NuxtLink>

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
          </div>

          <aside class="paper-sidebar">
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

const route = useRoute()
const { getLiterature, getKnowledge, getMethods, getDataPoints } = useLiteratureApi()
const paperId = computed(() => String(route.params.id))

const { data, pending, error, refresh } = await useAsyncData(
  () => `literature:${paperId.value}`,
  async () => {
    const paper = await getLiterature(paperId.value)
    const [knowledgeResult, methodsResult, dataPointsResult] = await Promise.all([
      getKnowledge(paperId.value).catch(() => null),
      getMethods(paperId.value).catch(() => null),
      getDataPoints(paperId.value).catch(() => null),
    ])
    return { paper, knowledgeResult, methodsResult, dataPointsResult }
  },
  { watch: [paperId] },
)

const paper = computed(() => data.value?.paper || null)
const knowledge = computed(() => data.value?.knowledgeResult?.knowledge || null)
const methods = computed(() => data.value?.methodsResult?.methods || null)
const dataPoints = computed(() => data.value?.dataPointsResult?.data_points || [])
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
</style>
