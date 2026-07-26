<template>
  <main class="review-page">
    <div class="review-container">
      <header class="review-header">
        <div>
          <NuxtLink :to="editUrl('manuscript-type')" class="review-back-link">Edit submission</NuxtLink>
          <h1>Review Your Submission</h1>
          <p>Check the public record and private submission material before final confirmation.</p>
        </div>
        <span v-if="draft" class="review-draft-id">Draft #{{ draft.id }}</span>
      </header>

      <div v-if="loading" class="review-loading">Loading submission review...</div>
      <div v-else-if="errorMessage && !draft" class="review-alert error" role="alert">
        <Attention :size="20" /> {{ errorMessage }}
      </div>

      <template v-else-if="draft">
        <div v-if="errorMessage" class="review-alert error" role="alert">
          <Attention :size="20" /> {{ errorMessage }}
        </div>
        <div v-if="validationIssues.length" class="review-alert warning" role="alert">
          <Attention :size="20" />
          <div>
            <strong>This submission still has {{ validationIssues.length }} incomplete item{{ validationIssues.length === 1 ? '' : 's' }}.</strong>
            <NuxtLink :to="editUrl(validationIssues[0].section)">Return to the first item</NuxtLink>
          </div>
        </div>

        <div class="review-layout">
          <div class="review-main">
            <ReviewSection title="Manuscript Type" :edit-url="editUrl('manuscript-type')">
              <p class="review-primary-value">{{ form.paperType }}</p>
            </ReviewSection>

            <ReviewSection title="Files" :edit-url="editUrl('file-upload')">
              <div class="review-file-list">
                <article v-for="file in files" :key="file.id" class="review-file-row">
                  <FileText :size="19" />
                  <div>
                    <strong>{{ file.displayName }}</strong>
                    <span>{{ roleLabel(file.role) }} · {{ formatFileSize(file.fileSize) }} · {{ file.visibility === 'PUBLIC' ? 'Public' : 'Private' }}</span>
                    <p v-if="file.description">{{ file.description }}</p>
                  </div>
                  <span class="review-file-status">{{ file.uploadStatus === 'UPLOADED' ? 'Ready' : file.uploadStatus }}</span>
                </article>
              </div>
            </ReviewSection>

            <ReviewSection title="Manuscript Information" :edit-url="editUrl('manuscript-information')">
              <div class="review-metadata">
                <div class="full">
                  <span>Title</span>
                  <h2>{{ form.title }}</h2>
                </div>
                <div class="full">
                  <span>Abstract</span>
                  <p class="review-abstract">{{ form.abstractText }}</p>
                </div>
                <div>
                  <span>Subject area</span>
                  <strong>{{ form.subjectArea }}</strong>
                </div>
                <div>
                  <span>Keywords</span>
                  <div class="review-keywords">
                    <span v-for="keyword in form.keywords" :key="keyword">{{ keyword }}</span>
                  </div>
                </div>
              </div>
            </ReviewSection>

            <ReviewSection title="Authors" :edit-url="editUrl('author-information')">
              <div class="review-author-list">
                <article v-for="(author, index) in form.authors" :key="index" class="review-author-row">
                  <div class="review-author-order">{{ index + 1 }}</div>
                  <div>
                    <strong>{{ author.displayName || fullName(author) }}</strong>
                    <span>
                      {{ author.correspondingAuthor ? 'Corresponding Author' : 'Author' }}
                      <template v-if="author.equalContribution"> · Co-first author</template>
                    </span>
                    <a v-if="author.correspondingAuthor" :href="`mailto:${author.email}`">{{ author.email }}</a>
                    <ul>
                      <li v-for="(affiliation, affiliationIndex) in author.affiliations" :key="affiliationIndex">
                        {{ affiliation.organizationName }}<template v-if="affiliation.department">, {{ affiliation.department }}</template>
                        · {{ affiliation.city }}, {{ affiliation.country }}
                        <strong v-if="affiliation.primaryAffiliation">Primary</strong>
                      </li>
                    </ul>
                  </div>
                </article>
              </div>
            </ReviewSection>

            <ReviewSection title="Funding" :edit-url="editUrl('funding-information')">
              <p v-if="form.noFundingReceived" class="review-primary-value">No funding was received for this work.</p>
              <div v-else class="review-funding-list">
                <div v-for="(funding, index) in form.funding" :key="index">
                  <strong>{{ funding.funderName }}</strong>
                  <span>{{ funding.grantId || 'No grant ID provided' }}</span>
                </div>
              </div>
            </ReviewSection>

            <ReviewSection title="Declarations" :edit-url="editUrl('details-comments')">
              <dl class="review-declarations">
                <div><dt>Conflict of Interest</dt><dd>{{ form.conflictOfInterest }}</dd></div>
                <div><dt>Data Availability</dt><dd>{{ form.dataAvailability }}</dd></div>
                <div><dt>Ethics Statement</dt><dd>{{ form.ethicsStatement }}</dd></div>
                <div><dt>Preprint or Prior Posting</dt><dd>{{ form.preprintStatement }}</dd></div>
                <div><dt>AI Tool Use</dt><dd>{{ form.aiUseDisclosure }}</dd></div>
                <div v-if="form.privateComments" class="private"><dt>Private Comments to the Platform</dt><dd>{{ form.privateComments }}</dd></div>
              </dl>
            </ReviewSection>
          </div>

          <aside class="review-confirmation">
            <div class="review-confirmation-inner">
              <h2>Final Confirmation</h2>
              <p>Submission creates the paper record and starts the platform screening process.</p>

              <label>
                <input v-model="confirmations.metadataMatchesManuscript" type="checkbox" />
                <span>The title, abstract, authors, and files match the manuscript.</span>
              </label>
              <label>
                <input v-model="confirmations.correspondingAuthorInformationConfirmed" type="checkbox" />
                <span>The corresponding author information is accurate.</span>
              </label>
              <label>
                <input v-model="confirmations.publicDisplayConfirmed" type="checkbox" />
                <span>I approve the public display of files and declarations marked public.</span>
              </label>

              <button
                class="review-submit-button"
                type="button"
                :disabled="!canSubmit || submitting || validationIssues.length > 0"
                @click="submitFinal"
              >
                <CheckOne :size="18" />
                {{ submitting ? 'Submitting...' : 'Confirm & Submit' }}
              </button>
              <NuxtLink :to="editUrl('manuscript-type')" class="review-edit-button">
                <Edit :size="17" /> Return to Edit
              </NuxtLink>
            </div>
          </aside>
        </div>
      </template>
    </div>
  </main>
</template>

<script setup>
import { Attention, CheckOne, Edit, FileText } from '@icon-park/vue-next'
import { OPTIONAL_FILE_ROLES, REQUIRED_FILE_ROWS } from '~/config/paperSubmissionConfig'

const ReviewSection = defineComponent({
  props: {
    title: { type: String, required: true },
    editUrl: { type: String, required: true },
  },
  setup(props, { slots }) {
    return () => h('section', { class: 'review-section' }, [
      h('header', [
        h('h2', props.title),
        h(resolveComponent('NuxtLink'), { to: props.editUrl }, () => 'Edit'),
      ]),
      h('div', { class: 'review-section-content' }, slots.default?.()),
    ])
  },
})

definePageMeta({ middleware: 'auth-client', keepalive: false })
useHead({ title: 'Review Your Submission - OpenIsle' })

const route = useRoute()
const router = useRouter()
const api = usePaperApi()
const draft = ref(null)
const validation = ref({ valid: false, issues: [] })
const loading = ref(true)
const submitting = ref(false)
const errorMessage = ref('')
const idempotencyKey = ref('')
const confirmations = reactive({
  metadataMatchesManuscript: false,
  correspondingAuthorInformationConfirmed: false,
  publicDisplayConfirmed: false,
})

const form = computed(() => draft.value?.formData || {})
const files = computed(() => draft.value?.files || [])
const validationIssues = computed(() => validation.value?.issues || [])
const canSubmit = computed(() => Object.values(confirmations).every(Boolean))

onMounted(async () => {
  idempotencyKey.value = globalThis.crypto?.randomUUID?.() ||
    `${Date.now()}-${Math.random().toString(36).slice(2)}`
  try {
    draft.value = await api.getSubmissionDraft(route.params.draftId)
    validation.value = await api.validateSubmissionDraft(route.params.draftId)
  } catch (error) {
    errorMessage.value = error?.data?.error || error?.message || 'Unable to load this submission.'
  } finally {
    loading.value = false
  }
})

const editUrl = (section) => `/papers/submit?draft=${route.params.draftId}#${section}`

const submitFinal = async () => {
  if (!canSubmit.value || submitting.value) return
  submitting.value = true
  errorMessage.value = ''
  try {
    const result = await api.submitSubmissionDraft(route.params.draftId, {
      version: draft.value.version,
      idempotencyKey: idempotencyKey.value,
      ...confirmations,
    })
    await router.push(`/papers/${result.paperId}`)
  } catch (error) {
    errorMessage.value = error?.data?.error || error?.message || 'Unable to submit this manuscript.'
    if (error?.statusCode === 409 || error?.response?.status === 409) {
      try {
        draft.value = await api.getSubmissionDraft(route.params.draftId)
      } catch {
        // Keep the original conflict message visible.
      }
    }
  } finally {
    submitting.value = false
  }
}

const fullName = (author) =>
  [author.givenName, author.middleName, author.familyName].filter(Boolean).join(' ')

const roleLabel = (role) =>
  REQUIRED_FILE_ROWS.find((item) => item.role === role)?.label ||
  OPTIONAL_FILE_ROLES.find((item) => item.value === role)?.label ||
  role?.replaceAll('_', ' ')

const formatFileSize = (size) => {
  if (!size) return '0 B'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}
</script>

<style scoped>
.review-page { min-height: 100vh; padding: 26px 20px 80px; background: #eef1f2; color: #19252d; }
.review-container { width: min(1280px, 100%); margin: 0 auto; }
.review-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; margin-bottom: 20px; }
.review-back-link { display: inline-block; margin-bottom: 8px; color: #315f75; font-size: 13px; font-weight: 700; text-decoration: none; }
.review-back-link::before { content: '← '; }
.review-header h1 { margin: 0; font-size: 30px; line-height: 1.15; letter-spacing: 0; }
.review-header p { margin: 7px 0 0; color: #5f6b73; font-size: 14px; }
.review-draft-id { color: #68747c; font-size: 12px; font-weight: 700; }
.review-loading { min-height: 280px; display: grid; place-items: center; border: 1px solid #d4dade; background: #fff; color: #5f6b73; }
.review-alert { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; padding: 12px 14px; border: 1px solid; font-size: 13px; }
.review-alert.error { border-color: #d6a19c; background: #fff6f5; color: #92342c; }
.review-alert.warning { border-color: #d6b36c; background: #fffaf0; color: #684d20; }
.review-alert > div { display: grid; gap: 3px; }
.review-alert a { color: inherit; font-weight: 700; }
.review-layout { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 24px; align-items: start; }
.review-main { display: grid; gap: 14px; min-width: 0; }
:deep(.review-section) { border: 1px solid #d2d9dd; background: #fff; }
:deep(.review-section > header) { display: flex; align-items: center; justify-content: space-between; gap: 16px; min-height: 58px; padding: 12px 18px; border-bottom: 1px solid #e0e4e7; }
:deep(.review-section > header h2) { margin: 0; font-size: 17px; letter-spacing: 0; }
:deep(.review-section > header a) { color: #285f79; font-size: 12px; font-weight: 750; text-decoration: none; }
:deep(.review-section-content) { padding: 18px; }
.review-primary-value { margin: 0; color: #24323a; font-weight: 700; }
.review-file-list, .review-author-list { display: grid; border: 1px solid #d8dee2; border-bottom: 0; }
.review-file-row { display: grid; grid-template-columns: 26px minmax(0, 1fr) auto; gap: 10px; align-items: start; padding: 12px; border-bottom: 1px solid #d8dee2; }
.review-file-row > div { display: grid; gap: 2px; min-width: 0; }
.review-file-row strong { overflow-wrap: anywhere; }
.review-file-row span, .review-file-row p { margin: 0; color: #68747c; font-size: 12px; line-height: 1.4; }
.review-file-status { color: #39704b !important; font-weight: 750; }
.review-metadata { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }
.review-metadata .full { grid-column: 1 / -1; }
.review-metadata > div { display: grid; gap: 6px; }
.review-metadata > div > span, .review-declarations dt { color: #68747c; font-size: 11px; font-weight: 800; text-transform: uppercase; }
.review-metadata h2 { margin: 0; font-size: 20px; line-height: 1.35; letter-spacing: 0; }
.review-abstract { max-width: 76ch; margin: 0; color: #34434c; line-height: 1.65; white-space: pre-line; }
.review-keywords { display: flex; flex-wrap: wrap; gap: 6px; }
.review-keywords span { padding: 4px 7px; border: 1px solid #cad6db; background: #edf3f5; color: #30566a; font-size: 12px; font-weight: 700; }
.review-author-row { display: grid; grid-template-columns: 38px minmax(0, 1fr); border-bottom: 1px solid #d8dee2; }
.review-author-order { display: grid; place-items: center; border-right: 1px solid #e0e5e8; color: #66737b; font-weight: 800; }
.review-author-row > div:last-child { display: grid; gap: 3px; padding: 12px; }
.review-author-row span, .review-author-row a { color: #61707a; font-size: 12px; }
.review-author-row ul { margin: 7px 0 0; padding-left: 18px; color: #46545d; font-size: 12px; line-height: 1.5; }
.review-author-row li strong { margin-left: 6px; color: #3d7150; font-size: 10px; text-transform: uppercase; }
.review-funding-list { display: grid; gap: 9px; }
.review-funding-list > div { display: flex; justify-content: space-between; gap: 16px; padding-bottom: 9px; border-bottom: 1px solid #e2e6e8; }
.review-funding-list span { color: #67737b; font-size: 12px; }
.review-declarations { display: grid; gap: 16px; margin: 0; }
.review-declarations > div { display: grid; gap: 5px; }
.review-declarations dd { max-width: 78ch; margin: 0; color: #34434c; line-height: 1.55; white-space: pre-line; }
.review-declarations .private { padding: 12px; border: 1px solid #d9cfae; background: #fffaf0; }
.review-confirmation { position: sticky; top: 88px; }
.review-confirmation-inner { display: grid; gap: 14px; padding: 18px; border: 1px solid #cbd4d9; background: #fff; }
.review-confirmation h2 { margin: 0; font-size: 18px; }
.review-confirmation p { margin: -5px 0 3px; color: #66727a; font-size: 12px; line-height: 1.5; }
.review-confirmation label { display: flex; align-items: flex-start; gap: 9px; color: #35434c; font-size: 12px; line-height: 1.45; }
.review-confirmation input { width: 17px; height: 17px; flex: 0 0 auto; margin-top: 1px; }
.review-submit-button, .review-edit-button { min-height: 44px; display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 9px 12px; font-weight: 800; text-decoration: none; cursor: pointer; }
.review-submit-button { border: 1px solid #164d67; background: #1f617f; color: #fff; }
.review-submit-button:disabled { opacity: .5; cursor: not-allowed; }
.review-edit-button { border: 1px solid #bcc7cd; background: #fff; color: #34454f; }
input:focus-visible, button:focus-visible, a:focus-visible { outline: 3px solid rgba(32, 109, 147, .25); outline-offset: 1px; }
@media (max-width: 920px) {
  .review-layout { grid-template-columns: 1fr; }
  .review-confirmation { position: static; }
}
@media (max-width: 620px) {
  .review-page { padding: 18px 12px 60px; }
  .review-header { align-items: flex-start; flex-direction: column; }
  .review-header h1 { font-size: 25px; }
  .review-metadata { grid-template-columns: 1fr; }
  .review-metadata .full { grid-column: auto; }
  :deep(.review-section-content) { padding: 14px; }
  .review-file-row { grid-template-columns: 24px minmax(0, 1fr); }
  .review-file-status { grid-column: 2; }
}
</style>
