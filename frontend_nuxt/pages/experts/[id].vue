<template>
  <main class="paper-shell">
    <div class="paper-container">
      <header class="paper-workspace-header">
        <div>
          <div class="paper-page-eyebrow">Expert Database</div>
          <h1 class="paper-page-title">{{ expert.displayName || 'Expert profile' }}</h1>
          <p class="paper-page-description">
            Research identity generated from submitted paper authorship records.
          </p>
        </div>
        <div class="paper-toolbar">
          <NuxtLink class="paper-button" to="/papers">Papers</NuxtLink>
          <NuxtLink class="paper-button" to="/papers/rankings">Rankings</NuxtLink>
        </div>
      </header>

      <section class="paper-panel expert-profile-panel">
        <div>
          <div class="paper-meta-row" style="margin-top: 0">
            <span class="paper-pill subject">{{ formatIdentity(expert.identityStatus) }}</span>
            <span class="paper-pill">{{ expert.paperCount || 0 }} linked papers</span>
            <span v-if="expert.country" class="paper-pill">{{ expert.country }}</span>
          </div>
          <h2 class="paper-block-title">{{ expert.displayName || 'Unnamed expert' }}</h2>
          <p class="paper-page-description">
            {{ expert.primaryInstitutionName || 'No primary institution recorded yet.' }}
          </p>
        </div>
        <div class="expert-profile-facts">
          <div v-if="expert.orcid">
            <span>ORCID</span>
            <strong>{{ expert.orcid }}</strong>
          </div>
          <div v-if="expert.email">
            <span>Email</span>
            <strong>{{ expert.email }}</strong>
          </div>
          <div v-if="expert.userId">
            <span>Platform account</span>
            <NuxtLink :to="`/users/${expert.userId}`">Open profile</NuxtLink>
          </div>
        </div>
      </section>

      <section class="paper-block">
        <div class="paper-section-heading-row">
          <h2 class="paper-block-title">Linked papers</h2>
          <span class="paper-muted">{{ expert.paperCount || 0 }} records</span>
        </div>
        <div v-if="expert.papers?.length" class="expert-paper-list">
          <NuxtLink
            v-for="paper in expert.papers"
            :key="paper.paperId"
            class="expert-paper-row"
            :to="`/papers/${paper.paperId}`"
          >
            <div>
              <strong>{{ paper.title }}</strong>
              <small>{{ paper.subjectArea || 'Research paper' }} · {{ paper.authorRole }}</small>
            </div>
            <div class="paper-score-chip compact">
              <strong>{{ formatScore(paper.scoreSnapshot?.compositeScore) }}</strong>
              score
            </div>
          </NuxtLink>
        </div>
        <BasePlaceholder v-else text="No public papers linked to this expert yet." icon="inbox" />
      </section>
    </div>
  </main>
</template>

<script setup>
import BasePlaceholder from '~/components/BasePlaceholder.vue'
import { usePaperApi } from '~/composables/paperApi'

const route = useRoute()
const { getExpert } = usePaperApi()
const { data: expertData } = await useAsyncData(`expert:${route.params.id}`, () =>
  getExpert(route.params.id),
)

const expert = computed(() => expertData.value || {})

const formatIdentity = (status) => {
  if (!status) return 'Unmatched'
  return String(status)
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

const formatScore = (score) => {
  const numeric = Number(score || 0)
  return numeric > 0 ? numeric.toFixed(2) : 'New'
}
</script>
