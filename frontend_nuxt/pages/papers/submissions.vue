<template>
  <main class="submission-list-page">
    <header>
      <div>
        <NuxtLink to="/papers">Papers</NuxtLink>
        <h1>My Submissions</h1>
        <p>Track screening decisions and open your author-only paper records.</p>
      </div>
      <NuxtLink class="submit-link" to="/papers/submit">Submit a paper</NuxtLink>
    </header>

    <p v-if="pending" class="state-message">Loading your submissions...</p>
    <p v-else-if="error" class="state-message error">Unable to load submissions.</p>
    <template v-else>
      <div v-if="submittedPaper" class="submission-success" role="status">
        <div>
          <strong>Submission received</strong>
          <p>Your paper has been submitted and is now in initial screening. This page is your private author workspace.</p>
        </div>
        <NuxtLink :to="`/papers/${submittedPaper.id}`">Open submission</NuxtLink>
      </div>
      <section v-if="allDrafts.length" class="draft-list" aria-labelledby="draft-workspace-title">
        <div class="draft-list-heading">
          <div>
            <span>Private workspace</span>
            <h2 id="draft-workspace-title">Saved Drafts</h2>
            <p>New submissions and requested revisions are kept separate.</p>
          </div>
          <small>{{ allDrafts.length }} saved</small>
        </div>
        <div v-for="group in draftGroups" :key="group.key" class="draft-group">
          <div class="draft-group-heading">
            <strong>{{ group.label }}</strong>
            <span>{{ group.description }}</span>
          </div>
          <PaperDraftRow v-for="savedDraft in group.recent" :key="savedDraft.id" :draft="savedDraft" @updated="updateDraftRecord" @deleted="removeDraftRecord" />
          <details v-if="group.older.length" class="older-drafts">
            <summary>{{ group.older.length }} older draft{{ group.older.length === 1 ? '' : 's' }}</summary>
            <PaperDraftRow v-for="savedDraft in group.older" :key="savedDraft.id" :draft="savedDraft" @updated="updateDraftRecord" @deleted="removeDraftRecord" />
          </details>
        </div>
      </section>
      <section v-if="papers.length" class="submission-list">
      <article v-for="paper in papers" :key="paper.id" class="submission-row">
        <NuxtLink :to="`/papers/${paper.id}`" class="submission-main">
          <span class="type">
            {{ paper.paperType || 'Research Article' }}
            <template v-if="paper.revisionNumber > 1"> · Revision {{ paper.revisionNumber }}</template>
          </span>
          <h2>{{ paper.title }}</h2>
          <p>{{ paper.subjectArea || 'General Research' }}</p>
        </NuxtLink>
        <div class="status-column">
          <strong :class="statusClass(paper.publicationStatus)">{{ formatStatus(paper.publicationStatus) }}</strong>
          <span>{{ formatStatus(paper.screeningStatus) }}</span>
          <button
            v-if="paper.publicationStatus === 'NEEDS_REVISION' && !paper.latestRevisionPaperId"
            type="button"
            :disabled="isCreatingRevisionId === paper.id"
            @click="openRevision(paper)"
          >{{ isCreatingRevisionId === paper.id ? 'Opening...' : (revisionDraftFor(paper.id) ? 'Continue Revision' : 'Revise Submission') }}</button>
          <NuxtLink
            v-else-if="paper.latestRevisionPaperId"
            class="revision-link"
            :to="`/papers/${paper.latestRevisionPaperId}`"
          >View Latest Revision</NuxtLink>
        </div>
      </article>
      </section>
      <p v-else-if="!allDrafts.length" class="state-message">You have not submitted a paper yet.</p>
    </template>
  </main>
</template>

<script setup>
import { toast } from '~/main'
import { partitionDraftsByAge } from '~/utils/paperDraftPresentation'

definePageMeta({ middleware: 'auth-client', keepalive: false })
useHead({ title: 'My Submissions - OpenIsle' })

const { listMyPapers, listSubmissionDrafts, createRevisionDraft } = usePaperApi()
const route = useRoute()
const { data, pending, error } = await useAsyncData('my-paper-submissions', async () => {
  const [papers, drafts] = await Promise.all([listMyPapers(), listSubmissionDrafts('ANY')])
  return { papers, drafts }
}, { server: false })
const papers = computed(() => data.value?.papers || [])
const allDrafts = computed(() => data.value?.drafts || [])
const originalDrafts = computed(() => allDrafts.value.filter((draft) => !draft.revisionSourcePaperId))
const revisionDrafts = computed(() => allDrafts.value.filter((draft) => draft.revisionSourcePaperId))
const draftGroups = computed(() => [
  {
    key: 'original',
    label: 'New submission drafts',
    description: 'Independent manuscripts that have not been submitted.',
    ...partitionDraftsByAge(originalDrafts.value),
  },
  {
    key: 'revision',
    label: 'Revision drafts',
    description: 'Prefilled workspaces linked to papers that need revision.',
    ...partitionDraftsByAge(revisionDrafts.value),
  },
].filter((group) => group.recent.length || group.older.length))
const submittedPaper = computed(() => {
  const submittedId = String(route.query.submitted || '')
  return papers.value.find((paper) => String(paper.id) === submittedId)
})
const formatStatus = (value) => String(value || 'NOT_SCREENED').replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase())
const statusClass = (value) => `status-${String(value || '').toLowerCase()}`
const isCreatingRevisionId = ref(null)
const revisionDraftFor = (paperId) => revisionDrafts.value.find((draft) => String(draft.revisionSourcePaperId) === String(paperId))
const updateDraftRecord = (updated) => {
  data.value = {
    ...data.value,
    drafts: allDrafts.value.map((draft) => String(draft.id) === String(updated.id) ? updated : draft),
  }
}
const removeDraftRecord = (draftId) => {
  data.value = { ...data.value, drafts: allDrafts.value.filter((draft) => String(draft.id) !== String(draftId)) }
}
const openRevision = async (paper) => {
  if (!paper?.id || isCreatingRevisionId.value) return
  isCreatingRevisionId.value = paper.id
  try {
    const draft = await createRevisionDraft(paper.id)
    await navigateTo(`/papers/submit?draft=${draft.id}`)
  } catch (revisionError) {
    toast.error(revisionError?.data?.error || revisionError?.message || 'Unable to open the revision draft.')
  } finally {
    isCreatingRevisionId.value = null
  }
}
</script>

<style scoped>
.submission-list-page { max-width: 980px; margin: 0 auto; padding: 42px 28px 64px; color: #1a2a33; }
header { display: flex; align-items: end; justify-content: space-between; gap: 24px; padding-bottom: 24px; border-bottom: 2px solid #2f505e; }
header a { color: #24617d; font-size: 13px; text-decoration: none; }
h1 { margin: 8px 0 6px; font-size: 30px; }
header p { margin: 0; color: #65747b; }
.submit-link { padding: 10px 14px; border: 1px solid #2f6178; background: #2f6178; color: #fff; white-space: nowrap; }
.submission-list { border-top: 1px solid #d7dee1; }
.draft-list { margin: 24px 0 30px; border: 1px solid #cad6db; background: #f7fafb; }
.draft-list-heading { display: flex; align-items: end; justify-content: space-between; gap: 20px; padding: 16px 18px; border-bottom: 1px solid #d7e0e4; }
.draft-list-heading span { color: #2f657c; font-size: 11px; font-weight: 800; letter-spacing: .07em; text-transform: uppercase; }
.draft-list-heading h2 { margin: 4px 0 0; font-family: Georgia, serif; font-size: 21px; font-weight: 500; }
.draft-list-heading p { margin: 5px 0 0; color: #65747b; font-size: 12px; }
.draft-list-heading small { color: #6a777e; }
.draft-group + .draft-group { border-top: 2px solid #cad6db; }
.draft-group-heading { display: flex; align-items: baseline; gap: 10px; padding: 12px 18px; background: #edf3f5; }
.draft-group-heading strong { color: #263a44; font-size: 13px; }
.draft-group-heading span { color: #69777e; font-size: 12px; }
.older-drafts { border-top: 1px solid #d8e0e3; }
.older-drafts summary { padding: 11px 18px; color: #526b77; font-size: 12px; font-weight: 700; cursor: pointer; }
.submission-success { display: flex; align-items: center; justify-content: space-between; gap: 20px; margin: 24px 0; padding: 16px 18px; border: 1px solid #9fc7ad; background: #f1f8f3; color: #214b2e; }
.submission-success strong { font-size: 15px; }
.submission-success p { margin: 5px 0 0; color: #40624a; font-size: 13px; line-height: 1.5; }
.submission-success a { flex: 0 0 auto; padding: 8px 10px; border: 1px solid #327044; background: #327044; color: #fff; font-size: 13px; font-weight: 700; text-decoration: none; white-space: nowrap; }
.submission-row { display: grid; grid-template-columns: minmax(0, 1fr) 190px; gap: 24px; padding: 20px 0; border-bottom: 1px solid #d7dee1; color: inherit; }
.submission-main { color: inherit; text-decoration: none; }
.submission-main:hover h2 { color: #1f617f; }
.type, .status-column span { color: #68777e; font-size: 12px; }
h2 { margin: 7px 0; font-size: 18px; line-height: 1.35; }
.submission-row p { margin: 0; color: #596970; font-size: 13px; }
.status-column { display: grid; align-content: center; justify-items: end; gap: 5px; text-align: right; }
.status-column strong { padding: 4px 7px; font-size: 11px; text-transform: uppercase; }
.status-column button, .revision-link { margin-top: 7px; padding: 7px 10px; border: 1px solid #2f6178; background: #fff; color: #245f7d; font: inherit; font-size: 12px; font-weight: 700; text-decoration: none; cursor: pointer; }
.status-column button:hover, .revision-link:hover { background: #edf4f7; }
.status-column button:disabled { cursor: wait; opacity: .65; }
.status-published { color: #24633c; background: #e8f3ec; }.status-needs_revision { color: #8a560d; background: #fff3dd; }.status-screening { color: #245f7d; background: #e6f0f5; }.status-rejected { color: #983632; background: #f9e8e7; }
.state-message { padding: 36px 0; color: #65747b; }.state-message.error { color: #9b3b35; }
@media (max-width: 640px) { .submission-list-page { padding: 28px 18px; } header, .submission-success { align-items: start; flex-direction: column; }.submission-row { grid-template-columns: 1fr; gap: 12px; }.status-column { justify-items: start; text-align: left; } }
</style>
