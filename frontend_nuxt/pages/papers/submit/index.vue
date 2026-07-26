<template>
  <main class="submission-page">
    <div class="submission-container">
      <header class="submission-header">
        <div>
          <NuxtLink class="submission-back-link" to="/papers">Papers</NuxtLink>
          <h1>Submit a Manuscript</h1>
          <p>Prepare the files, metadata, authors, funding, and declarations for one research record.</p>
        </div>
        <div class="submission-save-state" :class="saveState">
          <span class="submission-save-dot" aria-hidden="true"></span>
          <span>{{ saveStatusLabel }}</span>
        </div>
      </header>

      <div v-if="loading" class="submission-loading">Opening your submission draft...</div>

      <template v-else-if="draft">
        <div v-if="conflict" class="submission-alert warning" role="alert">
          <Attention :size="20" />
          <div>
            <strong>This draft changed in another tab.</strong>
            <span>Your local edits are still here, but they have not been saved.</span>
          </div>
          <button type="button" @click="reloadDraft"><Refresh :size="17" /> Reload saved copy</button>
        </div>

        <div v-if="lastError && !conflict" class="submission-alert error" role="alert">
          <Attention :size="20" />
          <span>{{ lastError }}</span>
        </div>

        <form novalidate @submit.prevent="continueToReview">
          <div class="submission-workspace">
            <div class="submission-main-column">
              <section
                id="manuscript-type"
                class="submission-section"
                data-submission-section
              >
                <SectionHeading
                  number="1"
                  title="Manuscript Type"
                  description="Select the publication format that best matches the work."
                  :issues="issuesForSection('manuscript-type')"
                />
                <div class="submission-type-options">
                  <label
                    v-for="type in MANUSCRIPT_TYPES"
                    :key="type.value"
                    class="submission-type-option"
                    :class="{ selected: form.paperType === type.value }"
                  >
                    <input v-model="form.paperType" type="radio" :value="type.value" />
                    <span>
                      <strong>{{ type.label }}</strong>
                      <small>{{ type.description }}</small>
                    </span>
                  </label>
                </div>
              </section>

              <section id="file-upload" class="submission-section" data-submission-section>
                <SectionHeading
                  number="2"
                  title="File Upload"
                  description="Upload the manuscript source, cover letter, TOC graphic, and any supporting material."
                  :issues="issuesForSection('file-upload')"
                />
                <PaperSubmissionFileUploader
                  :files="files"
                  :upload-state="uploadState"
                  @upload="handleUpload"
                  @update="handleFileUpdate"
                  @remove="handleFileRemove"
                />
              </section>

              <section
                id="manuscript-information"
                class="submission-section"
                data-submission-section
              >
                <SectionHeading
                  number="3"
                  title="Manuscript Information"
                  description="This information becomes the structured HTML record shown to readers."
                  :issues="issuesForSection('manuscript-information')"
                />
                <div class="submission-fields">
                  <label class="submission-field full">
                    <span>Title *</span>
                    <input
                      v-model.trim="form.title"
                      placeholder="Enter the full manuscript title"
                      autocomplete="off"
                    />
                  </label>
                  <label class="submission-field full">
                    <span>Abstract *</span>
                    <textarea
                      v-model.trim="form.abstractText"
                      rows="8"
                      placeholder="State the research context, approach, principal findings, and contribution."
                    ></textarea>
                  </label>
                  <label class="submission-field">
                    <span>Subject area *</span>
                    <input
                      v-model.trim="form.subjectArea"
                      list="paper-subject-options"
                      placeholder="e.g. Environmental Chemistry"
                    />
                    <datalist id="paper-subject-options">
                      <option value="Environmental Chemistry" />
                      <option value="Environmental Engineering" />
                      <option value="Climate and Atmospheric Science" />
                      <option value="Water Research" />
                      <option value="Sustainability" />
                      <option value="Information Systems" />
                      <option value="Computer Science" />
                      <option value="Social Sciences" />
                    </datalist>
                  </label>
                  <div class="submission-field full">
                    <span>Keywords *</span>
                    <div class="submission-keyword-input" @click="keywordInput?.focus()">
                      <span v-for="keyword in form.keywords" :key="keyword" class="submission-keyword">
                        {{ keyword }}
                        <button
                          type="button"
                          :aria-label="`Remove keyword ${keyword}`"
                          :title="`Remove keyword ${keyword}`"
                          @click.stop="removeKeyword(keyword)"
                        ><CloseOne :size="13" /></button>
                      </span>
                      <input
                        ref="keywordInput"
                        v-model.trim="keywordDraft"
                        placeholder="Type a keyword and press Enter"
                        @keydown="handleKeywordKeydown"
                        @blur="addKeyword"
                      />
                    </div>
                    <small class="submission-help">Add at least one precise, searchable keyword.</small>
                  </div>
                </div>
              </section>

              <section id="article-content" class="submission-section" data-submission-section>
                <SectionHeading
                  number="4"
                  title="Article Content"
                  description="Build the online HTML article with sections, figures, equations, and tables."
                  :issues="issuesForSection('article-content')"
                />
                <div class="article-content-launch">
                  <div>
                    <strong>{{ articleStatus === 'READY' ? 'Online article ready' : 'Prepare the online article' }}</strong>
                    <span>{{ articleStatus === 'READY' ? 'The article preview is ready for final submission review.' : 'The DOCX remains archived, while this structured version becomes the reader-facing article.' }}</span>
                  </div>
                  <NuxtLink class="submission-secondary-button" :to="`/papers/submit/${draft.id}/content`">
                    {{ articleStatus === 'READY' ? 'Edit Article' : 'Open Article Editor' }}
                    <Right :size="16" />
                  </NuxtLink>
                </div>
              </section>

              <section
                id="author-information"
                class="submission-section"
                data-submission-section
              >
                <SectionHeading
                  number="5"
                  title="Author Information"
                  description="Add every author in publication order and assign exactly one corresponding author."
                  :issues="issuesForSection('author-information')"
                />
                <PaperAuthorEditor v-model="form.authors" />
              </section>

              <section
                id="funding-information"
                class="submission-section"
                data-submission-section
              >
                <SectionHeading
                  number="6"
                  title="Funding Information"
                  description="Record each funder and grant identifier, or confirm that no funding was received."
                  :issues="issuesForSection('funding-information')"
                />

                <label class="submission-check-row standalone">
                  <input v-model="form.noFundingReceived" type="checkbox" />
                  <span>
                    <strong>No funding was received for this work</strong>
                    <small>Select this only when there are no funders to report.</small>
                  </span>
                </label>

                <div v-if="!form.noFundingReceived" class="submission-funding-list">
                  <article
                    v-for="(funding, index) in form.funding"
                    :key="index"
                    class="submission-funding-row"
                  >
                    <label class="submission-field">
                      <span>Funder name *</span>
                      <input v-model.trim="funding.funderName" placeholder="Funding organization" />
                    </label>
                    <label class="submission-field">
                      <span>Grant ID</span>
                      <input v-model.trim="funding.grantId" placeholder="Optional award number" />
                    </label>
                    <button
                      class="submission-icon-button danger"
                      type="button"
                      title="Remove funder"
                      aria-label="Remove funder"
                      @click="removeFunding(index)"
                    ><Delete :size="17" /></button>
                  </article>
                  <button class="submission-secondary-button" type="button" @click="addFunding">
                    <AddOne :size="17" /> Add funder
                  </button>
                </div>
              </section>

              <section
                id="details-comments"
                class="submission-section"
                data-submission-section
              >
                <SectionHeading
                  number="7"
                  title="Details & Comments"
                  description="Complete the public declarations and final author confirmations."
                  :issues="issuesForSection('details-comments')"
                />
                <div class="submission-fields declarations">
                  <label class="submission-field full">
                    <span>Conflict of Interest *</span>
                    <textarea
                      v-model.trim="form.conflictOfInterest"
                      rows="4"
                      placeholder="Declare competing interests or state that none exist."
                    ></textarea>
                  </label>
                  <label class="submission-field full">
                    <span>Data Availability *</span>
                    <textarea
                      v-model.trim="form.dataAvailability"
                      rows="4"
                      placeholder="Explain where data, code, and research materials can be accessed."
                    ></textarea>
                  </label>
                  <label class="submission-field full">
                    <span>Ethics Statement *</span>
                    <textarea
                      v-model.trim="form.ethicsStatement"
                      rows="4"
                      placeholder="State approval and consent details, or explain why they are not applicable."
                    ></textarea>
                  </label>
                  <label class="submission-field full">
                    <span>Preprint or Prior Posting *</span>
                    <textarea
                      v-model.trim="form.preprintStatement"
                      rows="3"
                      placeholder="Describe any preprint or prior public posting, or enter None."
                    ></textarea>
                  </label>
                  <label class="submission-field full">
                    <span>AI Tool Use Disclosure *</span>
                    <textarea
                      v-model.trim="form.aiUseDisclosure"
                      rows="3"
                      placeholder="Disclose AI-assisted work, or state that no AI tools were used."
                    ></textarea>
                  </label>
                  <label class="submission-field full">
                    <span>Comments to the Platform</span>
                    <textarea
                      v-model.trim="form.privateComments"
                      rows="4"
                      placeholder="Optional private comments for platform administrators."
                    ></textarea>
                    <small class="submission-help">This field is never displayed on the public paper page.</small>
                  </label>
                </div>

                <div class="submission-confirmations">
                  <label class="submission-check-row">
                    <input v-model="form.allAuthorsConsent" type="checkbox" />
                    <span>All authors have reviewed and agreed to this submission.</span>
                  </label>
                  <label class="submission-check-row">
                    <input v-model="form.originalityConfirmed" type="checkbox" />
                    <span>The work is original and any prior publication is disclosed above.</span>
                  </label>
                  <label class="submission-check-row">
                    <input v-model="form.rightsConfirmed" type="checkbox" />
                    <span>I have the rights and authorization required to submit these materials.</span>
                  </label>
                  <label class="submission-check-row">
                    <input v-model="form.correspondingAuthorContactConfirmed" type="checkbox" />
                    <span>The corresponding author's email may be displayed with the published paper.</span>
                  </label>
                </div>
              </section>
            </div>

            <aside class="submission-progress-rail" aria-label="Submission progress">
              <div class="submission-progress-inner">
                <div class="submission-progress-title">
                  <span>Submission Progress</span>
                  <small>{{ completedCount }}/{{ SUBMISSION_SECTIONS.length }} complete</small>
                </div>
                <nav>
                  <button
                    v-for="section in SUBMISSION_SECTIONS"
                    :key="section.id"
                    type="button"
                    :class="{
                      active: activeSection === section.id,
                      complete: sectionStatus(section.id) === 'complete',
                      invalid: sectionStatus(section.id) === 'invalid',
                    }"
                    @click="scrollTo(section.id)"
                  >
                    <span class="submission-progress-node">
                      <CheckOne v-if="sectionStatus(section.id) === 'complete'" :size="13" />
                      <Attention v-else-if="sectionStatus(section.id) === 'invalid'" :size="13" />
                    </span>
                    <span>{{ section.label }}</span>
                  </button>
                </nav>

                <div v-if="validation.issues?.length" class="submission-error-summary">
                  <strong>{{ validation.issues.length }} item{{ validation.issues.length === 1 ? '' : 's' }} to fix</strong>
                  <button
                    v-for="issue in validation.issues.slice(0, 5)"
                    :key="`${issue.field}-${issue.code}`"
                    type="button"
                    @click="scrollTo(issue.section)"
                  >{{ issue.message }}</button>
                </div>
              </div>
            </aside>
          </div>

          <footer class="submission-action-bar">
            <div>
              <button class="submission-text-button danger" type="button" @click="discardCurrentDraft">
                Discard draft
              </button>
              <span v-if="draft.updatedAt">Last saved {{ formatSavedTime(draft.updatedAt) }}</span>
            </div>
            <button
              class="submission-primary-button"
              type="submit"
              :disabled="saveState === 'saving' || uploadState.active > 0 || continuing"
            >
              {{ continuing ? 'Checking submission...' : 'Continue to Review' }}
              <Right :size="18" />
            </button>
          </footer>
        </form>
      </template>

      <div v-else class="submission-loading error">{{ lastError || 'Unable to open a submission draft.' }}</div>
    </div>
  </main>
</template>

<script setup>
import {
  AddOne,
  Attention,
  CheckOne,
  CloseOne,
  Delete,
  Refresh,
  Right,
} from '@icon-park/vue-next'
import {
  MANUSCRIPT_TYPES,
  SUBMISSION_SECTIONS,
} from '~/config/paperSubmissionConfig'

const SectionHeading = defineComponent({
  props: {
    number: { type: String, required: true },
    title: { type: String, required: true },
    description: { type: String, required: true },
    issues: { type: Array, default: () => [] },
  },
  setup(props) {
    return () => h('header', { class: 'submission-section-heading' }, [
      h('span', { class: 'submission-section-number' }, props.number),
      h('div', [
        h('h2', props.title),
        h('p', props.description),
        props.issues.length
          ? h('p', { class: 'submission-section-error' }, props.issues[0].message)
          : null,
      ]),
    ])
  },
})

definePageMeta({ middleware: 'auth-client', keepalive: false })

useHead({ title: 'Submit a Manuscript - OpenIsle' })

const route = useRoute()
const router = useRouter()
const keywordInput = ref(null)
const keywordDraft = ref('')
const continuing = ref(false)
const articleStatus = ref('NOT_STARTED')
const articleApi = usePaperApi()

const {
  draft,
  files,
  form,
  loading,
  saveState,
  saveStatusLabel,
  uploadState,
  validation,
  conflict,
  lastError,
  loadOrCreate,
  setCurrentSection,
  uploadFile,
  updateFile,
  removeFile,
  validate,
  discard,
  issuesForSection,
} = usePaperSubmissionDraft()

const sectionIds = SUBMISSION_SECTIONS.map((section) => section.id)
const { activeSection, start: startScrollspy, scrollTo } = useSubmissionScrollspy(sectionIds)

watch(activeSection, (sectionId) => setCurrentSection(sectionId))
watch(
  () => form.noFundingReceived,
  (noFunding) => {
    if (noFunding) form.funding = []
  },
)

onMounted(async () => {
  try {
    const record = await loadOrCreate(route.query.draft || null)
    try {
      articleStatus.value = (await articleApi.getDraftArticle(record.id))?.status || 'NOT_STARTED'
    } catch {
      articleStatus.value = 'NOT_STARTED'
    }
    if (String(route.query.draft || '') !== String(record.id)) {
      await router.replace({ query: { ...route.query, draft: record.id } })
    }
    await nextTick()
    startScrollspy()
    const hashSection = route.hash?.replace('#', '')
    if (hashSection && sectionIds.includes(hashSection)) {
      setTimeout(() => scrollTo(hashSection), 50)
    } else if (record.currentSection && sectionIds.includes(record.currentSection)) {
      setTimeout(() => scrollTo(record.currentSection), 50)
    }
  } catch {
    // The composable exposes the actionable error in the page.
  }
})

const uploadedRole = (role) =>
  files.value.filter((file) => file.role === role && file.uploadStatus === 'UPLOADED').length

const localSectionComplete = (sectionId) => {
  if (sectionId === 'manuscript-type') return ['Research Article', 'Review'].includes(form.paperType)
  if (sectionId === 'file-upload') {
    return uploadedRole('MANUSCRIPT') === 1 &&
      uploadedRole('COVER_LETTER') === 1
  }
  if (sectionId === 'manuscript-information') {
    return Boolean(form.title && form.abstractText && form.subjectArea && form.keywords.length)
  }
  if (sectionId === 'article-content') return articleStatus.value === 'READY'
  if (sectionId === 'author-information') {
    if (!form.authors.length) return false
    const corresponding = form.authors.filter((author) => author.correspondingAuthor).length
    return corresponding === 1 && form.authors.every((author) => {
      const affiliations = author.affiliations || []
      return author.givenName && author.familyName && author.email && author.authorRole &&
        affiliations.length > 0 &&
        affiliations.filter((item) => item.primaryAffiliation).length === 1 &&
        affiliations.every((item) => item.organizationName && item.country && item.city)
    })
  }
  if (sectionId === 'funding-information') {
    return form.noFundingReceived || (
      form.funding.length > 0 && form.funding.every((item) => item.funderName)
    )
  }
  if (sectionId === 'details-comments') {
    return Boolean(
      form.conflictOfInterest &&
      form.dataAvailability &&
      form.ethicsStatement &&
      form.preprintStatement &&
      form.aiUseDisclosure &&
      form.allAuthorsConsent &&
      form.originalityConfirmed &&
      form.rightsConfirmed &&
      form.correspondingAuthorContactConfirmed
    )
  }
  return false
}

const sectionStatus = (sectionId) => {
  if (issuesForSection(sectionId).length) return 'invalid'
  return localSectionComplete(sectionId) ? 'complete' : 'pending'
}

const completedCount = computed(() =>
  SUBMISSION_SECTIONS.filter((section) => sectionStatus(section.id) === 'complete').length,
)

const addKeyword = () => {
  const value = keywordDraft.value.trim().replace(/,$/, '')
  if (value && !form.keywords.some((keyword) => keyword.toLowerCase() === value.toLowerCase())) {
    form.keywords.push(value)
  }
  keywordDraft.value = ''
}

const handleKeywordKeydown = (event) => {
  if (event.key !== 'Enter' && event.key !== ',') return
  event.preventDefault()
  addKeyword()
}

const removeKeyword = (keyword) => {
  form.keywords = form.keywords.filter((item) => item !== keyword)
}

const addFunding = () => {
  form.noFundingReceived = false
  form.funding.push({ funderName: '', grantId: '' })
}

const removeFunding = (index) => form.funding.splice(index, 1)

const handleUpload = async (file, metadata) => {
  lastError.value = ''
  try {
    await uploadFile(file, metadata)
  } catch {
    // Upload state already contains the specific message.
  }
}

const handleFileUpdate = async (fileId, payload) => {
  lastError.value = ''
  try {
    await updateFile(fileId, payload)
  } catch (error) {
    lastError.value = error?.data?.error || error?.message || 'Unable to update file details.'
  }
}

const handleFileRemove = async (fileId) => {
  lastError.value = ''
  try {
    await removeFile(fileId)
  } catch (error) {
    lastError.value = error?.data?.error || error?.message || 'Unable to remove this file.'
  }
}

const continueToReview = async () => {
  addKeyword()
  continuing.value = true
  lastError.value = ''
  try {
    const result = await validate()
    if (!result.valid) {
      const firstIssue = result.issues?.[0]
      if (firstIssue?.section) scrollTo(firstIssue.section)
      lastError.value = 'Complete the highlighted items before continuing to review.'
      return
    }
    await router.push(`/papers/submit/${draft.value.id}/review`)
  } catch (error) {
    lastError.value = error?.data?.error || error?.message || 'Unable to validate this submission.'
  } finally {
    continuing.value = false
  }
}

const discardCurrentDraft = async () => {
  if (!window.confirm('Discard this submission draft? This action cannot be undone.')) return
  await discard()
  await router.push('/papers')
}

const reloadDraft = async () => {
  try {
    await loadOrCreate(draft.value.id)
  } catch {
    // The composable keeps the error visible.
  }
}

const formatSavedTime = (value) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat('en', { hour: '2-digit', minute: '2-digit' }).format(date)
}
</script>

<style scoped>
.submission-page { min-height: 100vh; background: #eef1f2; color: #19252d; padding: 26px 20px 130px; }
.submission-container { width: min(1320px, 100%); margin: 0 auto; }
.submission-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; margin-bottom: 20px; padding: 0 2px; }
.submission-back-link { display: inline-block; margin-bottom: 8px; color: #315f75; font-size: 13px; font-weight: 700; text-decoration: none; }
.submission-back-link::before { content: '← '; }
.submission-header h1 { margin: 0; color: #17242c; font-size: 30px; line-height: 1.15; letter-spacing: 0; }
.submission-header p { max-width: 720px; margin: 7px 0 0; color: #5b6871; font-size: 14px; line-height: 1.5; }
.submission-save-state { display: inline-flex; align-items: center; gap: 8px; flex: 0 0 auto; color: #5c6870; font-size: 13px; font-weight: 700; }
.submission-save-dot { width: 8px; height: 8px; border-radius: 50%; background: #6c9a78; }
.submission-save-state.dirty .submission-save-dot { background: #c28b30; }
.submission-save-state.saving .submission-save-dot { background: #367da1; animation: submission-pulse 1s infinite; }
.submission-save-state.error .submission-save-dot, .submission-save-state.conflict .submission-save-dot { background: #b5483d; }
.submission-loading { min-height: 280px; display: grid; place-items: center; border: 1px solid #d4dade; background: #fff; color: #5f6b73; }
.submission-loading.error { color: #a33b33; }
.submission-alert { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; padding: 12px 14px; border: 1px solid; background: #fff; font-size: 13px; }
.submission-alert > div { display: grid; gap: 2px; flex: 1; }
.submission-alert.warning { border-color: #d7b36c; color: #684d20; background: #fffaf0; }
.submission-alert.error { border-color: #d7a29d; color: #8d3028; background: #fff7f6; }
.submission-alert button { min-height: 38px; display: inline-flex; align-items: center; gap: 7px; border: 1px solid currentColor; background: transparent; padding: 7px 10px; color: inherit; font-weight: 700; cursor: pointer; }
.submission-workspace { display: grid; grid-template-columns: minmax(0, 1fr) 260px; gap: 24px; align-items: start; }
.submission-main-column { display: grid; gap: 16px; min-width: 0; }
.submission-section { scroll-margin-top: 92px; padding: 24px; border: 1px solid #d2d9dd; background: #fff; }
:deep(.submission-section-heading) { display: grid; grid-template-columns: 34px minmax(0, 1fr); gap: 12px; margin-bottom: 22px; padding-bottom: 16px; border-bottom: 1px solid #e0e4e7; }
:deep(.submission-section-number) { width: 30px; height: 30px; display: grid; place-items: center; background: #e8eff2; color: #28566d; font-weight: 800; font-size: 13px; }
:deep(.submission-section-heading h2) { margin: 0; font-size: 19px; line-height: 1.3; letter-spacing: 0; }
:deep(.submission-section-heading p) { margin: 4px 0 0; color: #65717a; font-size: 13px; line-height: 1.45; }
:deep(.submission-section-heading .submission-section-error) { color: #a63c33; font-weight: 700; }
.submission-type-options { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.submission-type-option { display: flex; align-items: flex-start; gap: 11px; min-height: 96px; padding: 16px; border: 1px solid #cbd3d8; background: #fff; cursor: pointer; }
.submission-type-option.selected { border-color: #2c6c8a; box-shadow: inset 3px 0 #2c6c8a; background: #f7fafb; }
.submission-type-option input { margin-top: 3px; }
.submission-type-option span { display: grid; gap: 5px; }
.submission-type-option strong { color: #1d2a32; }
.submission-type-option small { color: #64717a; font-size: 12px; line-height: 1.45; }
.submission-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.submission-fields.declarations { grid-template-columns: 1fr; }
.submission-field { display: grid; gap: 7px; min-width: 0; }
.submission-field.full { grid-column: 1 / -1; }
.submission-field > span { color: #35444d; font-size: 13px; font-weight: 750; }
.submission-field input, .submission-field textarea, .submission-field select { width: 100%; border: 1px solid #b9c3c9; background: #fff; padding: 10px 11px; color: #17242c; font: inherit; line-height: 1.45; }
.submission-field input, .submission-field select { min-height: 44px; }
.submission-field textarea { resize: vertical; min-height: 108px; }
.submission-help { color: #6a757d; font-size: 12px; line-height: 1.4; }
.submission-keyword-input { display: flex; flex-wrap: wrap; align-items: center; gap: 7px; min-height: 48px; padding: 6px 8px; border: 1px solid #b9c3c9; background: #fff; cursor: text; }
.submission-keyword-input > input { flex: 1 1 210px; min-width: 120px; min-height: 34px; padding: 4px; border: 0; outline: 0; }
.submission-keyword { display: inline-flex; align-items: center; gap: 5px; max-width: 100%; padding: 5px 7px; border: 1px solid #c9d5da; background: #edf3f5; color: #294c5d; font-size: 12px; font-weight: 700; }
.submission-keyword button { width: 22px; height: 22px; display: grid; place-items: center; border: 0; background: transparent; color: inherit; cursor: pointer; }
.submission-check-row { display: flex; align-items: flex-start; gap: 10px; color: #33424b; font-size: 13px; line-height: 1.45; }
.submission-check-row input { width: 17px; height: 17px; flex: 0 0 auto; margin-top: 1px; }
.submission-check-row.standalone { padding: 14px; border: 1px solid #d4dadd; background: #f8f9fa; }
.submission-check-row span { display: grid; gap: 2px; }
.submission-check-row small { color: #68747c; }
.submission-funding-list { display: grid; gap: 12px; margin-top: 14px; }
.submission-funding-row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, .7fr) 38px; gap: 12px; align-items: end; padding: 14px; border: 1px solid #d6dde1; background: #f8f9fa; }
.submission-icon-button { width: 38px; height: 38px; display: inline-grid; place-items: center; border: 1px solid #c5ced3; background: #fff; color: #34454f; cursor: pointer; }
.submission-icon-button.danger { color: #a43b33; }
.submission-secondary-button { min-height: 40px; width: fit-content; display: inline-flex; align-items: center; gap: 8px; padding: 8px 13px; border: 1px solid #275f79; background: #fff; color: #1f526b; font-weight: 750; cursor: pointer; }
.submission-confirmations { display: grid; gap: 12px; margin-top: 22px; padding: 16px; border: 1px solid #d4dade; background: #f7f9fa; }
.submission-progress-rail { position: sticky; top: 88px; }
.submission-progress-inner { border-left: 2px solid #cbd4d9; padding-left: 18px; }
.submission-progress-title { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 12px; color: #293943; font-size: 13px; font-weight: 800; }
.submission-progress-title small { color: #6c777e; font-size: 11px; font-weight: 650; }
.submission-progress-inner nav { display: grid; }
.submission-progress-inner nav button { position: relative; display: grid; grid-template-columns: 20px minmax(0, 1fr); align-items: center; gap: 9px; min-height: 43px; margin-left: -29px; padding: 6px 8px; border: 0; background: transparent; color: #68747c; text-align: left; font-size: 12px; font-weight: 700; cursor: pointer; }
.submission-progress-inner nav button.active { color: #1f566f; background: #e9f0f3; }
.submission-progress-inner nav button.complete { color: #3e7250; }
.submission-progress-inner nav button.invalid { color: #a43b33; }
.submission-progress-node { width: 20px; height: 20px; display: grid; place-items: center; border: 2px solid #aeb9bf; border-radius: 50%; background: #eef1f2; }
button.active .submission-progress-node { border-color: #276985; background: #fff; }
button.complete .submission-progress-node { border-color: #4d825e; background: #4d825e; color: #fff; }
button.invalid .submission-progress-node { border-color: #b34a40; background: #fff; }
.submission-error-summary { display: grid; gap: 7px; margin-top: 18px; padding-top: 14px; border-top: 1px solid #d1d8dc; }
.submission-error-summary strong { color: #9d3830; font-size: 12px; }
.submission-error-summary button { padding: 0; border: 0; background: transparent; color: #6d4743; text-align: left; font-size: 11px; line-height: 1.35; cursor: pointer; }
.submission-action-bar { position: fixed; z-index: 20; left: 0; right: 0; bottom: 0; min-height: 74px; display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 12px max(20px, calc((100vw - 1320px) / 2 + 20px)); border-top: 1px solid #c9d1d5; background: rgba(255, 255, 255, .97); box-shadow: 0 -6px 18px rgba(31, 48, 58, .08); }
.submission-action-bar > div { display: flex; align-items: center; gap: 16px; color: #68747c; font-size: 12px; }
.submission-text-button { border: 0; background: transparent; padding: 8px 0; color: #4e5b63; font-weight: 700; cursor: pointer; }
.submission-text-button.danger { color: #a23c34; }
.submission-primary-button { min-height: 46px; display: inline-flex; align-items: center; justify-content: center; gap: 9px; padding: 10px 18px; border: 1px solid #164d67; background: #1f617f; color: #fff; font-weight: 800; cursor: pointer; }
.submission-primary-button:disabled { opacity: .55; cursor: not-allowed; }
.article-content-launch { display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 18px; border: 1px solid #d0dce0; background: #f5f8f8; }
.article-content-launch > div { display: grid; gap: 5px; }
.article-content-launch span { color: #68747c; font-size: 13px; line-height: 1.5; }
.article-content-launch .submission-secondary-button { flex: 0 0 auto; text-decoration: none; }
input:focus-visible, textarea:focus-visible, select:focus-visible, button:focus-visible, a:focus-visible { outline: 3px solid rgba(32, 109, 147, .25); outline-offset: 1px; }
@keyframes submission-pulse { 50% { opacity: .35; } }
@media (prefers-reduced-motion: reduce) { .submission-save-state.saving .submission-save-dot { animation: none; } }
@media (max-width: 1020px) {
  .submission-workspace { grid-template-columns: 1fr; }
  .submission-progress-rail { z-index: 10; top: 64px; order: -1; overflow-x: auto; border: 1px solid #d2d9dd; background: #fff; }
  .submission-progress-inner { width: max-content; min-width: 100%; display: flex; align-items: center; gap: 12px; border-left: 0; padding: 10px 12px; }
  .submission-progress-title { margin: 0; white-space: nowrap; }
  .submission-progress-inner nav { display: flex; }
  .submission-progress-inner nav button { grid-template-columns: 18px auto; min-height: 38px; margin: 0; white-space: nowrap; }
  .submission-progress-node { width: 18px; height: 18px; }
  .submission-error-summary { display: none; }
}
@media (max-width: 700px) {
  .submission-page { padding: 18px 12px 126px; }
  .submission-header { align-items: flex-start; flex-direction: column; gap: 12px; }
  .submission-header h1 { font-size: 25px; }
  .submission-section { padding: 18px 14px; }
  .submission-type-options, .submission-fields { grid-template-columns: 1fr; }
  .submission-field.full { grid-column: auto; }
  .submission-funding-row { grid-template-columns: 1fr; }
  .submission-action-bar { min-height: 88px; padding: 10px 12px; }
  .submission-action-bar > div span { display: none; }
  .submission-primary-button { flex: 1; max-width: 240px; }
  .article-content-launch { align-items: stretch; flex-direction: column; }
  .article-content-launch .submission-secondary-button { justify-content: center; }
}
</style>
