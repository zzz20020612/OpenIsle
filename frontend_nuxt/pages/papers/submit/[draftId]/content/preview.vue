<template>
  <main class="content-preview-page">
    <header class="preview-topbar">
      <div>
        <NuxtLink :to="`/papers/submit/${draftId}/content`">Back to editor</NuxtLink>
        <h1>Review Article Layout</h1>
        <p>This is the online article readers will see after publication.</p>
      </div>
      <div class="preview-actions">
        <span v-if="article.status === 'READY'" class="ready-label">Article content ready</span>
        <button v-if="article.status !== 'READY'" type="button" class="ready-button" :disabled="working" @click="markReady">Mark Content as Ready</button>
        <template v-else>
          <button type="button" class="reopen-button" :disabled="working" @click="reopen">Reopen in Editor</button>
          <NuxtLink class="review-button" :to="`/papers/submit/${draftId}/review`">Continue to Submission Review</NuxtLink>
        </template>
      </div>
    </header>

    <div v-if="message" class="preview-alert" :class="{ error: messageType === 'error' }">{{ message }}</div>
    <div v-if="issues.length" class="issue-list">
      <strong>Complete these items before continuing:</strong>
      <p v-for="issue in issues" :key="`${issue.code}-${issue.blockKey}`">{{ issue.message }}</p>
    </div>

    <article class="paper-preview">
      <header class="paper-preview-header">
        <span>{{ form.paperType || 'Research Article' }} · {{ form.subjectArea || 'Research' }}</span>
        <h2>{{ form.title || 'Untitled manuscript' }}</h2>
        <p class="preview-authors">{{ authorNames }}</p>
        <p v-if="form.abstractText" class="preview-abstract"><strong>Abstract.</strong> {{ form.abstractText }}</p>
        <div v-if="form.keywords?.length" class="preview-keywords"><span v-for="keyword in form.keywords" :key="keyword">{{ keyword }}</span></div>
      </header>
      <PaperArticleRenderer :article="article" :figure-source="figureSource" />
      <section v-if="form.references?.length" class="references-preview">
        <h2>References</h2>
        <ol><li v-for="reference in form.references" :key="reference">{{ reference }}</li></ol>
      </section>
      <section class="supporting-preview"><h2>Supporting Information</h2><p>The submitted supporting files will appear with the published article.</p></section>
    </article>
  </main>
</template>

<script setup>
definePageMeta({ middleware: 'auth-client', keepalive: false })
useHead({ title: 'Review Article Layout - OpenIsle' })
const route = useRoute()
const draftId = String(route.params.draftId)
const draftFileUrls = useDraftFileObjectUrls(draftId)
const articleDraft = usePaperArticleDraft(draftId)
const submission = usePaperSubmissionDraft()
const article = articleDraft.article
const form = submission.form
const message = ref('')
const messageType = ref('')
const working = ref(false)
const issues = computed(() => articleDraft.validation.value?.issues || [])
const authorNames = computed(() => (form.authors || []).map((author) => [author.givenName, author.middleName, author.familyName].filter(Boolean).join(' ')).filter(Boolean).join(', '))

onMounted(async () => {
  await Promise.all([articleDraft.load(), submission.loadOrCreate(draftId)])
})

const markReady = async () => {
  working.value = true
  message.value = ''
  try {
    await articleDraft.markReady()
    messageType.value = 'success'
    message.value = 'Article content is ready. You can now complete the submission review.'
  } catch (cause) {
    try { await articleDraft.validate() } catch {}
    messageType.value = 'error'
    message.value = cause?.data?.error || cause?.message || 'Review the highlighted article issues.'
  } finally { working.value = false }
}
const reopen = async () => {
  working.value = true
  try { await articleDraft.reopen(); await navigateTo(`/papers/submit/${draftId}/content`) } finally { working.value = false }
}
const figureSource = (block) => draftFileUrls.source(block.fileId)
</script>

<style scoped>
.content-preview-page { min-height: 100vh; padding: 34px 20px 80px; background: #f4f6f5; color: #17232c; }
.preview-topbar { max-width: 980px; display: flex; align-items: end; justify-content: space-between; gap: 24px; margin: 0 auto 22px; }
.preview-topbar a { color: #1f5b78; font-size: 13px; text-decoration: none; }
h1 { margin: 8px 0 5px; font-family: Georgia, serif; font-size: 38px; font-weight: 500; }
.preview-topbar p { margin: 0; color: #68747c; }
.preview-actions { display: flex; align-items: center; gap: 12px; }
.ready-button, .reopen-button, .review-button { min-height: 42px; display: inline-flex; align-items: center; justify-content: center; border: 1px solid #1f5b78; background: #1f617f; color: #fff; padding: 9px 14px; font-size: 13px; font-weight: 750; text-decoration: none; cursor: pointer; }
.reopen-button { background: #fff; color: #1f526b; }
.ready-button:disabled, .reopen-button:disabled { opacity: .55; cursor: wait; }
.ready-label { color: #2f6b4f; font-size: 13px; font-weight: 750; }
.preview-alert, .issue-list { max-width: 980px; margin: 0 auto 16px; padding: 12px 14px; border: 1px solid #bdd6c6; background: #f2faf4; color: #2f6b4f; }
.preview-alert.error, .issue-list { border-color: #e0b5af; background: #fff7f6; color: #923b32; }
.issue-list p { margin: 7px 0 0; }
.paper-preview { max-width: 980px; margin: 0 auto; padding: 50px clamp(24px, 6vw, 86px); border-top: 4px solid #0065a8; background: #fff; }
.paper-preview-header { margin-bottom: 42px; text-align: center; }
.paper-preview-header > span { color: #65727b; font-size: 13px; }
.paper-preview-header h2 { margin: 12px 0 14px; font-family: Georgia, serif; font-size: clamp(27px, 4vw, 42px); font-weight: 500; line-height: 1.2; }
.preview-authors { color: #35454f; font-size: 15px; }
.preview-abstract { margin: 28px auto 0; max-width: 760px; color: #35454f; font-size: 15px; line-height: 1.75; text-align: left; }
.preview-keywords { display: flex; flex-wrap: wrap; justify-content: center; gap: 7px; margin-top: 18px; }
.preview-keywords span { padding: 4px 8px; background: #eef3f4; color: #49616c; font-size: 12px; }
.references-preview, .supporting-preview { margin-top: 40px; padding-top: 24px; border-top: 1px solid #d9e0e2; }
.references-preview h2, .supporting-preview h2 { font-family: Georgia, serif; font-size: 23px; font-weight: 500; }
.references-preview li { margin-bottom: 9px; color: #35454f; font-size: 14px; line-height: 1.5; }
.supporting-preview p { color: #68747c; }
@media (max-width: 700px) { .content-preview-page { padding: 20px 10px 50px; } .preview-topbar { align-items: flex-start; flex-direction: column; } .preview-actions { width: 100%; justify-content: flex-end; } .paper-preview { padding: 30px 18px; } }
</style>
