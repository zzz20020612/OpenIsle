<template>
  <main class="paper-shell">
    <div class="paper-container">
      <header class="paper-workspace-header">
        <div>
          <div class="paper-page-eyebrow">Rankings</div>
          <h1 class="paper-page-title">Research signals</h1>
          <p class="paper-page-description">
            Ranked views generated from paper score snapshots. Use them as discovery signals, not
            final academic judgments.
          </p>
        </div>
        <div class="paper-toolbar">
          <NuxtLink class="paper-button" to="/papers">Paper feed</NuxtLink>
        </div>
      </header>

      <section>
        <div class="paper-tabs">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="paper-tab"
            :class="{ active: activeTab === tab.key }"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>

        <div class="paper-ranking-table">
          <template v-if="activeTab === 'papers'">
            <NuxtLink
              v-for="item in visibleRows"
              :key="rowKey(item)"
              class="paper-ranking-item"
              :to="`/papers/${item.paperId}`"
            >
              <span class="paper-rank-number">#{{ item.rank }}</span>
              <span>
                <span class="paper-rank-title">{{ rowTitle(item) }}</span>
                <span class="paper-rank-subtitle">{{ rowSubtitle(item) }}</span>
              </span>
              <span class="paper-rank-score">{{ formatScore(item.averageCompositeScore ?? item.compositeScore) }}</span>
            </NuxtLink>
          </template>
          <template v-else>
            <div
              v-for="item in visibleRows"
              :key="rowKey(item)"
              class="paper-ranking-item"
            >
              <span class="paper-rank-number">#{{ item.rank }}</span>
              <span>
                <span class="paper-rank-title">{{ rowTitle(item) }}</span>
                <span class="paper-rank-subtitle">{{ rowSubtitle(item) }}</span>
              </span>
              <span class="paper-rank-score">{{ formatScore(item.averageCompositeScore ?? item.compositeScore) }}</span>
            </div>
          </template>
        </div>

        <div v-if="visibleRows.length === 0" class="paper-empty">No ranking data yet.</div>
      </section>
    </div>
  </main>
</template>

<script setup>
import '~/assets/paper-platform.css'

const { getTopRatedPapers, getAuthorRankings, getInstitutionRankings } = usePaperApi()

useHead({
  title: 'Rankings - Open Research Evaluation',
})

const activeTab = ref('papers')
const tabs = [
  { key: 'papers', label: 'Top Papers' },
  { key: 'authors', label: 'Top Authors' },
  { key: 'institutions', label: 'Top Institutions' },
]

const { data: papersData } = await useAsyncData('rankings:papers', () => getTopRatedPapers(50))
const { data: authorsData } = await useAsyncData('rankings:authors', () => getAuthorRankings(50))
const { data: institutionsData } = await useAsyncData('rankings:institutions', () =>
  getInstitutionRankings(50),
)

const visibleRows = computed(() => {
  if (activeTab.value === 'authors') return Array.isArray(authorsData.value) ? authorsData.value : []
  if (activeTab.value === 'institutions') {
    return Array.isArray(institutionsData.value) ? institutionsData.value : []
  }
  return Array.isArray(papersData.value) ? papersData.value : []
})

const rowKey = (item) => item.paperId || item.authorName || item.institutionName
const rowTitle = (item) => item.title || item.authorName || item.institutionName
const rowSubtitle = (item) => {
  if (activeTab.value === 'papers') {
    return `${item.ratingCount || 0} ratings - ${item.subjectArea || 'Research'}`
  }
  return `${item.paperCount || 0} papers - ${item.totalRatingCount || 0} ratings`
}
const formatScore = (value) => Number(value || 0).toFixed(1)
</script>

