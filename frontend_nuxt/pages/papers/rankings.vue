<template>
  <main class="paper-shell">
    <div class="paper-container">
      <header class="paper-workspace-header">
        <div>
          <div class="paper-page-eyebrow">Rankings</div>
          <h1 class="paper-page-title">Scholar衡 evaluation rankings</h1>
          <p class="paper-page-description">
            Six-dimensional human evaluations of the existing literature corpus. Rankings are discovery
            signals with visible sample sizes, not final academic judgments.
          </p>
        </div>
        <div class="paper-toolbar">
          <NuxtLink class="paper-button" to="/literature">Knowledge base</NuxtLink>
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
              :to="`/literature/${item.literaturePaperId}`"
            >
              <span class="paper-rank-number">#{{ item.rank }}</span>
              <span>
                <span class="paper-rank-title">{{ rowTitle(item) }}</span>
                <span class="paper-rank-subtitle">{{ rowSubtitle(item) }}</span>
              </span>
              <span class="paper-rank-score">{{ formatScore(item.compositeScore) }}</span>
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
              <span class="paper-rank-score">{{ formatScore(item.averageCompositeScore) }}</span>
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

const { getPaperRankings, getAuthorRankings } = useLiteratureApi()

useHead({
  title: 'Rankings - Open Research Evaluation',
})

const activeTab = ref('papers')
const tabs = [
  { key: 'papers', label: 'Evaluated Papers' },
  { key: 'authors', label: 'Scholar Ranking' },
]

const { data: papersData } = await useAsyncData('rankings:literature-papers', () => getPaperRankings(50))
const { data: authorsData } = await useAsyncData('rankings:literature-authors', () => getAuthorRankings(50))

const visibleRows = computed(() => {
  if (activeTab.value === 'authors') return Array.isArray(authorsData.value) ? authorsData.value : []
  return Array.isArray(papersData.value) ? papersData.value : []
})

const rowKey = (item) => item.literaturePaperId || item.authorName
const rowTitle = (item) => item.title || item.authorName
const rowSubtitle = (item) => {
  if (activeTab.value === 'papers') {
    const authors = Array.isArray(item.authors) && item.authors.length ? item.authors.slice(0, 3).join(', ') : 'Authors unavailable'
    return `${item.ratingCount || 0} ratings · ${authors}${item.journal ? ` · ${item.journal}` : ''}`
  }
  return `${item.paperCount || 0} evaluated papers · ${item.totalRatingCount || 0} ratings`
}
const formatScore = (value) => Number(value || 0).toFixed(1)
</script>

