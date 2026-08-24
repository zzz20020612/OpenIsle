<template>
  <main class="paper-shell">
    <div class="paper-container">
      <header class="paper-workspace-header">
        <div>
          <div class="paper-page-eyebrow">Paper Library</div>
          <h1 class="paper-page-title">Papers under public evaluation</h1>
          <p class="paper-page-description">
            A working feed of published research records, reader scores, authors, and institutions.
          </p>
        </div>
        <div class="paper-toolbar">
          <NuxtLink class="paper-button" to="/papers/rankings">Rankings</NuxtLink>
          <NuxtLink class="paper-button primary" to="/papers/submit">Submit paper</NuxtLink>
        </div>
      </header>

      <dl class="paper-register-summary" aria-label="Paper register summary">
        <div><dt>Published records</dt><dd>{{ papers.length }}</dd></div>
        <div><dt>Highest score</dt><dd>{{ topScore }}</dd></div>
        <div><dt>Recorded ratings</dt><dd>{{ totalRatings }}</dd></div>
      </dl>

      <section class="paper-filter-bar paper-panel">
        <label class="paper-filter-field">
          Subject
          <select v-model="subjectFilter">
            <option value="">All subjects</option>
            <option v-for="subject in availableSubjects" :key="subject" :value="subject">
              {{ subject }}
            </option>
          </select>
        </label>
        <label class="paper-filter-field">
          Minimum score
          <select v-model="minScoreFilter">
            <option value="">Any score</option>
            <option v-for="option in scoreOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
        <label class="paper-filter-field">
          Sort
          <select v-model="sortFilter">
            <option value="latest">Latest</option>
            <option value="score">Highest score</option>
          </select>
        </label>
        <button class="paper-button" type="button" @click="clearFilters">
          Clear filters
        </button>
      </section>

      <section>
        <div class="paper-list">
          <div class="paper-feed-table paper-panel">
            <div class="paper-feed-row paper-feed-head">
              <span>Paper</span>
              <span>Authors</span>
              <span>Comments</span>
              <span>Views</span>
              <span>Score</span>
            </div>

            <article
              v-for="paper in papers"
              :key="paper.id"
              class="paper-feed-row paper-feed-item"
              @click="navigateTo(`/papers/${paper.id}`)"
            >
              <div class="paper-feed-main">
                <h2 class="paper-feed-title">
                  <pin v-if="paper.featured" theme="outline" class="paper-feed-pin" />
                  <star v-if="!paper.rssExcluded" theme="filled" size="16" class="paper-feed-rss" />
                  <NuxtLink :to="`/papers/${paper.id}`" @click.stop>{{ paper.title }}</NuxtLink>
                </h2>
                <p class="paper-feed-abstract">{{ paper.abstractText }}</p>
                <div v-if="!paper.rssExcluded" class="paper-feed-statuses">
                  <span v-if="!paper.rssExcluded" class="paper-feed-status rss">RSS</span>
                </div>
                <div class="paper-feed-tags">
                  <span class="paper-source-tag">{{ paper.subjectArea || 'General Research' }}</span>
                  <span class="paper-source-tag">{{ paper.paperType || 'Research Article' }}</span>
                  <span v-for="keyword in paper.keywords || []" :key="keyword" class="paper-source-tag muted">
                    {{ keyword }}
                  </span>
                </div>
              </div>

              <div class="paper-feed-authors">
                <strong>{{ formatAuthors(paper.authors) }}</strong>
                <small>{{ formatInstitutionSummary(paper.authors, paper.primaryInstitutionName) }}</small>
              </div>

              <span class="paper-feed-number">{{ paper.commentCount || 0 }}</span>
              <span class="paper-feed-number">{{ paper.views || 0 }}</span>
              <span class="paper-feed-score">
                {{ formatScore(paper.scoreSnapshot?.compositeScore) }}
                <small>{{ paper.scoreSnapshot?.ratingCount || 0 }} ratings</small>
              </span>
            </article>
          </div>

          <div v-if="!pending && papers.length === 0" class="paper-card paper-empty">
            No published papers yet.
          </div>
        </div>

        <aside class="paper-register-ranking">
          <section>
            <h3 class="paper-section-title">Top Rated</h3>
            <p class="paper-section-note">Based on current reader score snapshots.</p>
            <div class="paper-ranking-list">
              <NuxtLink
                v-for="item in topPapers"
                :key="item.paperId"
                class="paper-ranking-item"
                :to="`/papers/${item.paperId}`"
              >
                <span class="paper-rank-number">#{{ item.rank }}</span>
                <span>
                  <span class="paper-rank-title">{{ item.title }}</span>
                  <span class="paper-rank-subtitle">{{ item.ratingCount }} ratings</span>
                </span>
                <span class="paper-rank-score">{{ formatScore(item.compositeScore) }}</span>
              </NuxtLink>
            </div>
          </section>
        </aside>
      </section>
    </div>
  </main>
</template>

<script setup>
import '~/assets/paper-platform.css'

const route = useRoute()
const router = useRouter()
const { listPapers, getTopRatedPapers, getPaperFilters } = usePaperApi()

useHead({
  title: 'Papers - Open Research Evaluation',
})

const subjectFilter = ref(typeof route.query.subject === 'string' ? route.query.subject : '')
const minScoreFilter = ref(typeof route.query.minScore === 'string' ? route.query.minScore : '')
const sortFilter = ref(typeof route.query.sort === 'string' ? route.query.sort : 'latest')

const paperQuery = computed(() => ({
  page: 0,
  pageSize: 30,
  subject: subjectFilter.value || undefined,
  minScore: minScoreFilter.value === '' ? undefined : Number(minScoreFilter.value),
  sort: sortFilter.value || 'latest',
}))

const { data: papersData, pending, refresh } = await useAsyncData(
  'papers:feed',
  () => listPapers(paperQuery.value),
  { watch: [paperQuery] },
)

const { data: filterData } = await useAsyncData('papers:filters', () => getPaperFilters())

const { data: topData } = await useAsyncData('papers:top-rated:sidebar', () => getTopRatedPapers(5))

const papers = computed(() => (Array.isArray(papersData.value) ? papersData.value : []))
const topPapers = computed(() => (Array.isArray(topData.value) ? topData.value : []))
const availableSubjects = computed(() => filterData.value?.subjects || [])
const topScore = computed(() => {
  const first = topPapers.value[0]
  return first ? formatScore(first.compositeScore) : '0.0'
})
const totalRatings = computed(() =>
  papers.value.reduce((sum, paper) => sum + Number(paper.scoreSnapshot?.ratingCount || 0), 0),
)
const scoreOptions = [
  { value: '4', label: '4.0 and above' },
  { value: '3', label: '3.0 and above' },
  { value: '2', label: '2.0 and above' },
]

watch(
  [subjectFilter, minScoreFilter, sortFilter],
  async ([subject, minScore, sort]) => {
    const query = {
      ...route.query,
      subject: subject || undefined,
      minScore: minScore || undefined,
      sort: sort === 'latest' ? undefined : sort,
    }
    await router.replace({ query })
  },
)

watch(
  () => route.query,
  (query) => {
    subjectFilter.value = typeof query.subject === 'string' ? query.subject : ''
    minScoreFilter.value = typeof query.minScore === 'string' ? query.minScore : ''
    sortFilter.value = typeof query.sort === 'string' ? query.sort : 'latest'
  },
)

const clearFilters = async () => {
  subjectFilter.value = ''
  minScoreFilter.value = ''
  sortFilter.value = 'latest'
  await refresh()
}

const formatAuthors = (authors = []) => {
  if (!authors.length) return 'No authors recorded'
  const names = authors.map((author) => author.displayName || author).filter(Boolean)
  if (names.length <= 2) return names.join(', ')
  return `${names.slice(0, 2).join(', ')} et al.`
}
const formatInstitutionSummary = (authors = [], fallback = '') => {
  const institutions = [
    ...new Set(
      authors
        .map((author) => author.institution)
        .filter(Boolean),
    ),
  ]
  if (institutions.length === 0) return fallback || 'Independent'
  if (institutions.length === 1) return institutions[0]
  const firstAuthorInstitution = authors[0]?.institution || institutions[0]
  return `${firstAuthorInstitution} et al. (multiple institutions)`
}
const formatScore = (value) => Number(value || 0).toFixed(1)
const normalizeStatus = (value) => {
  if (!value) return 'Screened'
  return String(value).replaceAll('_', ' ').toLowerCase()
}
</script>

<style scoped>
.paper-register-summary{display:flex;flex-wrap:wrap;margin:0 0 24px;padding:0;border-top:1px solid var(--paper-line);border-bottom:1px solid var(--paper-line)}
.paper-register-summary div{display:flex;align-items:baseline;gap:10px;min-width:190px;padding:12px 24px 12px 0;margin-right:24px;border-right:1px solid var(--paper-line)}
.paper-register-summary div:last-child{border-right:0}.paper-register-summary dt{color:var(--paper-muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em}.paper-register-summary dd{margin:0;font-family:Georgia,serif;font-size:23px;color:var(--paper-ink)}
.paper-register-ranking{margin-top:32px;padding-top:22px;border-top:3px solid #0065a8}.paper-register-ranking .paper-ranking-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));border-top:1px solid var(--paper-line)}
@media(max-width:720px){.paper-register-summary{display:grid}.paper-register-summary div{border-right:0;margin-right:0}.paper-register-ranking .paper-ranking-list{grid-template-columns:1fr}}
</style>
