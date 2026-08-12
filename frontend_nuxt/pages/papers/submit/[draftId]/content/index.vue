<template>
  <main class="article-editor-page">
    <header class="article-editor-topbar">
      <div>
        <NuxtLink class="back-link" :to="`/papers/submit?draft=${draftId}`">Back to submission</NuxtLink>
        <h1>Article Content</h1>
        <p>Build the online version of your manuscript with sections, figures, equations, and tables.</p>
      </div>
      <div class="editor-actions">
        <span class="save-status" :class="saveState">{{ saveLabel }}</span>
        <NuxtLink class="preview-button" :to="`/papers/submit/${draftId}/content/preview`">Preview Article</NuxtLink>
      </div>
    </header>

    <div v-if="error" class="article-alert error">{{ error }}</div>
    <div v-if="loading" class="article-loading">Loading article editor...</div>
    <section v-else class="article-editor-workspace">
      <ArticleOutline :sections="article.sections" :selected-key="selectedKey" @select="selectedKey = $event" @add="addSection" />
      <article class="article-editor-main">
        <div class="article-workspace-heading">
          <div><strong>Structured manuscript</strong><span>Changes are saved to your private submission draft.</span></div>
          <div class="article-import-actions">
            <label class="article-command-button" :class="{ disabled: importingManuscript }">
              <UploadOne :size="16" /> {{ importingManuscript ? 'Importing...' : 'Import DOCX or PDF' }}
              <input type="file" accept=".docx,.pdf" :disabled="importingManuscript" @change="handleManuscriptImport" />
            </label>
            <label class="article-command-button secondary">
              <UploadOne :size="16" /> Upload figure
              <input type="file" accept=".png,.jpg,.jpeg,.webp" @change="uploadFigure" />
            </label>
          </div>
        </div>
        <p v-if="importProgress" class="docx-import-status">{{ importProgress }}</p>
        <div v-if="showImportReview" class="article-import-review" role="status">
          <strong>Author review required</strong>
          <span>Automatic import is a starting point. Check equations, complex tables, section headings, figures, and two-column reading order in the live preview before submission.</span>
          <button type="button" @click="showImportReview = false">Dismiss</button>
        </div>
        <ArticleBlockEditor
          :section="selectedSection"
          :figure-files="figureFiles"
          @change="scheduleChange"
          @add="addBlock"
          @remove="removeBlock"
          @move="moveBlock"
          @remove-section="removeSection"
        />
      </article>
      <aside class="article-live-preview">
        <div class="preview-heading"><strong>Live preview</strong><span>{{ article.sections.length }} sections</span></div>
        <div class="preview-scroll">
          <h2>{{ form.title || 'Untitled manuscript' }}</h2>
          <p v-if="form.abstractText" class="preview-abstract">{{ form.abstractText }}</p>
          <PaperArticleRenderer :article="article" :figure-source="figureSource" />
        </div>
      </aside>
    </section>
  </main>
</template>

<script setup>
import { UploadOne } from '@icon-park/vue-next'
import ArticleBlockEditor from '~/components/paper-article/ArticleBlockEditor.vue'
import ArticleOutline from '~/components/paper-article/ArticleOutline.vue'
import { createArticleBlock, createArticleSection } from '~/config/paperArticleConfig'
import { cleanupImportedDraftFiles } from '~/utils/docxImportRecovery'

definePageMeta({ middleware: 'auth-client', keepalive: false })
useHead({ title: 'Article Content - OpenIsle' })

const route = useRoute()
const router = useRouter()
const draftId = String(route.params.draftId)
const draftFileUrls = useDraftFileObjectUrls(draftId)
const {
  article, loading, saveLabel, saveState, error, load, scheduleSave, flush,
} = usePaperArticleDraft(draftId)
const submission = usePaperSubmissionDraft()
const docxImport = useDocxArticleImport()
const pdfImport = usePdfArticleImport()
const form = submission.form
const selectedKey = ref('')
const showImportReview = ref(false)

const selectedSection = computed(() => article.value.sections.find((section) => section.key === selectedKey.value) || article.value.sections[0] || null)
const figureFiles = computed(() => submission.files.value.filter((file) => file.role === 'FIGURE' && file.uploadStatus === 'UPLOADED'))
const importingDocx = docxImport.importing
const docxProgress = docxImport.progress
const importingManuscript = computed(() => importingDocx.value || pdfImport.importing.value)
const importProgress = computed(() => pdfImport.progress.value || docxProgress.value)
let importedFigureIds = []

onMounted(async () => {
  await Promise.all([load(), submission.loadOrCreate(draftId)])
  selectedKey.value = article.value.sections[0]?.key || ''
})

const scheduleChange = () => scheduleSave()
const addSection = () => {
  const section = createArticleSection(`Section ${article.value.sections.length + 1}`)
  section.displayOrder = article.value.sections.length
  article.value.sections.push(section)
  selectedKey.value = section.key
  scheduleSave()
}
const removeSection = (key) => {
  if (!window.confirm('Remove this section and its content?')) return
  article.value.sections = article.value.sections.filter((section) => section.key !== key)
  selectedKey.value = article.value.sections[0]?.key || ''
  scheduleSave()
}
const addBlock = (type) => {
  if (!selectedSection.value) return
  const block = createArticleBlock(type)
  block.displayOrder = selectedSection.value.blocks.length
  selectedSection.value.blocks.push(block)
  scheduleSave()
}
const removeBlock = (index) => {
  selectedSection.value?.blocks.splice(index, 1)
  scheduleSave()
}
const moveBlock = (index, direction) => {
  const blocks = selectedSection.value?.blocks
  const target = index + direction
  if (!blocks || target < 0 || target >= blocks.length) return
  const [block] = blocks.splice(index, 1)
  blocks.splice(target, 0, block)
  blocks.forEach((item, order) => { item.displayOrder = order })
  scheduleSave()
}
const uploadFigure = async (event) => {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  try {
    await submission.uploadFile(file, {
      role: 'FIGURE',
      visibility: 'PUBLIC',
      description: 'Article figure',
      displayName: file.name,
    })
  } catch (cause) {
    error.value = cause?.data?.error || cause?.message || 'Unable to upload the figure.'
  }
}
const uploadImportedFigure = async (file) => {
  const existingIds = new Set(submission.files.value.map((item) => item.id))
  try {
    const uploaded = await submission.uploadFile(file, {
      role: 'FIGURE',
      visibility: 'PUBLIC',
      description: 'Figure imported from the manuscript DOCX',
      displayName: file.name,
    })
    if (uploaded?.id) importedFigureIds.push(uploaded.id)
    return uploaded
  } catch (cause) {
    submission.files.value
      .filter((item) => item.role === 'FIGURE' && !existingIds.has(item.id))
      .forEach((item) => importedFigureIds.push(item.id))
    throw cause
  }
}
const handleManuscriptImport = async (event) => {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  if (article.value.sections.length && !window.confirm('Importing the manuscript will replace the current online article. Continue?')) return
  error.value = ''
  importedFigureIds = []
  try {
    pdfImport.progress.value = ''
    docxImport.progress.value = ''
    const imported = file.name.toLowerCase().endsWith('.pdf')
      ? await pdfImport.importPdf(file)
      : await docxImport.importDocx(file, uploadImportedFigure)
    article.value.sections = imported.sections
    showImportReview.value = true
    selectedKey.value = imported.sections[0]?.key || ''
    scheduleSave()
    await flush()
    importedFigureIds = []
  } catch (cause) {
    const failedCleanupIds = await cleanupImportedDraftFiles(importedFigureIds, submission.removeFile)
    importedFigureIds = []
    const message = cause?.data?.error || cause?.message || 'Unable to import the manuscript.'
    error.value = failedCleanupIds.length
      ? `${message} Some imported figure files could not be removed; review the Files section before submitting.`
      : `${message} The existing article was kept unchanged.`
  }
}
const figureSource = (block) => {
  if (!block.fileId) return ''
  return draftFileUrls.source(block.fileId)
}
</script>

<style scoped>
.article-editor-page { min-height: 100vh; padding: 34px max(20px, calc((100vw - 1460px) / 2)); padding-bottom: 50px; background: #f4f6f5; color: #17232c; }
.article-editor-topbar { display: flex; align-items: end; justify-content: space-between; gap: 24px; margin-bottom: 22px; }
.back-link { color: #1f5b78; font-size: 13px; text-decoration: none; }
h1 { margin: 8px 0 5px; font-family: Georgia, serif; font-size: clamp(28px, 3vw, 42px); font-weight: 500; }
.article-editor-topbar p { margin: 0; color: #68747c; }
.editor-actions { display: flex; align-items: center; gap: 12px; }
.save-status { color: #68747c; font-size: 12px; }
.save-status.error, .save-status.conflict { color: #a33d34; font-weight: 700; }
.preview-button { min-height: 42px; display: inline-flex; align-items: center; padding: 9px 14px; background: #1f617f; color: #fff; font-weight: 750; text-decoration: none; }
.article-alert { margin-bottom: 16px; padding: 12px 14px; border: 1px solid #e0b5af; background: #fff7f6; color: #923b32; }
.article-loading, .empty-editor { display: grid; place-items: center; min-height: 420px; color: #68747c; }
.article-editor-workspace { display: grid; grid-template-columns: 230px minmax(0, 1fr) minmax(300px, .75fr); min-height: 680px; border: 1px solid #d1dade; background: #fff; }
.article-editor-main { min-width: 0; padding: 20px; }
.article-workspace-heading { display: flex; justify-content: space-between; gap: 16px; margin-bottom: 18px; padding-bottom: 14px; border-bottom: 1px solid #d7dfe2; }
.article-workspace-heading > div { display: grid; gap: 4px; }
.article-workspace-heading span, .preview-heading span { color: #68747c; font-size: 12px; }
.article-import-actions { display: flex; align-items: center; gap: 8px; }
.article-command-button { min-height: 36px; display: inline-flex; align-items: center; gap: 6px; border: 1px solid #1f617f; background: #1f617f; color: #fff; padding: 7px 10px; font-size: 12px; font-weight: 750; cursor: pointer; }
.article-command-button.secondary { border-color: #9eb5c0; background: #f5f8f9; color: #1f526b; }
.article-command-button.disabled { opacity: .58; cursor: wait; }
.article-command-button input { position: absolute; width: 1px; height: 1px; opacity: 0; }
.docx-import-status { margin: -7px 0 16px; color: #47616d; font-size: 12px; }
.article-import-review { position: relative; display: grid; gap: 4px; margin: -4px 0 18px; padding: 12px 108px 12px 14px; border-left: 3px solid #a56a16; background: #fff8e8; color: #594318; font-size: 12px; line-height: 1.5; }
.article-import-review strong { font-size: 13px; }
.article-import-review button { position: absolute; top: 12px; right: 12px; border: 1px solid #bcae8c; background: #fff; color: #594318; padding: 5px 9px; font-size: 11px; font-weight: 700; cursor: pointer; }
.article-live-preview { min-width: 0; border-left: 1px solid #d5dde1; background: #fbfcfb; }
.preview-heading { display: flex; justify-content: space-between; gap: 12px; padding: 16px; border-bottom: 1px solid #d5dde1; }
.preview-scroll { max-height: 640px; overflow: auto; padding: 20px; }
.preview-scroll h2 { margin: 0 0 16px; font-family: Georgia, serif; font-size: 24px; font-weight: 500; line-height: 1.25; }
.preview-abstract { padding-bottom: 14px; border-bottom: 1px solid #d9e0e2; color: #52636d; font-size: 13px; line-height: 1.6; }
@media (max-width: 1050px) { .article-editor-workspace { grid-template-columns: 210px minmax(0, 1fr); } .article-live-preview { display: none; } }
@media (max-width: 700px) { .article-editor-page { padding: 22px 12px; } .article-editor-topbar { align-items: flex-start; flex-direction: column; } .editor-actions { width: 100%; justify-content: space-between; } .article-editor-workspace { display: block; } .article-outline { border-right: 0; border-bottom: 1px solid #d5dde1; } .article-editor-main { padding: 14px; } .article-workspace-heading { align-items: flex-start; flex-direction: column; } .article-import-actions { width: 100%; flex-wrap: wrap; } }
</style>
