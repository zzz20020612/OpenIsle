<template>
  <main class="paper-shell">
    <div class="paper-container">
      <header class="paper-workspace-header">
        <div>
          <div class="paper-page-eyebrow">Submit Paper</div>
          <h1 class="paper-page-title">New research record</h1>
          <p class="paper-page-description">
            A structured submission flow for paper metadata, contributors, manuscript text, and declarations.
          </p>
        </div>
        <div class="paper-toolbar">
          <NuxtLink class="paper-button" to="/papers">Cancel</NuxtLink>
        </div>
      </header>

      <form class="paper-submit-layout" @submit.prevent="submit">
        <aside class="paper-submit-steps paper-panel">
          <button
            v-for="(step, index) in steps"
            :key="step.key"
            class="paper-step-item"
            :class="{ active: activeStep === index, complete: isStepComplete(index) }"
            type="button"
            @click="activeStep = index"
          >
            <span class="paper-step-index">{{ index + 1 }}</span>
            <span>
              <span class="paper-step-title">{{ step.label }}</span>
              <span class="paper-step-note">{{ step.note }}</span>
            </span>
          </button>
        </aside>

        <section class="paper-submit-main">
          <section v-if="activeStep === 0" class="paper-block">
            <h2 class="paper-block-title">Before You Begin</h2>
            <p class="paper-section-note">
              This step follows the same idea as OJS submission requirements: the author confirms
              basic readiness before entering metadata.
            </p>
            <div class="paper-checklist">
              <label v-for="item in requirements" :key="item.key" class="paper-check-row">
                <input v-model="item.checked" type="checkbox" />
                <span>{{ item.label }}</span>
              </label>
            </div>
          </section>

          <section v-if="activeStep === 1" class="paper-block">
            <h2 class="paper-block-title">Manuscript</h2>
            <div class="paper-field-stack">
              <label class="paper-field">
                Manuscript text
                <textarea
                  v-model.trim="form.content"
                  required
                  rows="18"
                  placeholder="Paste the current manuscript text for indexing, preview, and knowledge extraction."
                />
              </label>

              <div class="paper-file-section">
                <div>
                  <div class="paper-field-label">Main manuscript file</div>
                  <p class="paper-section-note">
                    Add the primary manuscript record. The MVP stores file metadata first; binary upload can be connected to storage next.
                  </p>
                </div>
                <label class="paper-file-drop">
                  <input type="file" accept=".pdf,.doc,.docx,.tex,.md" @change="handleManuscriptFile" />
                  <span>Choose manuscript file</span>
                </label>
                <div v-if="manuscriptFiles.length" class="paper-file-list">
                  <div v-for="(file, index) in manuscriptFiles" :key="`${file.fileName}-${index}`" class="paper-file-row">
                    <span>
                      <strong>{{ file.fileName }}</strong>
                      <small>{{ file.fileRole }} - {{ formatFileSize(file.fileSize) }}</small>
                    </span>
                    <button class="paper-inline-action" type="button" @click="removeManuscriptFile(index)">
                      Remove
                    </button>
                  </div>
                </div>
              </div>

              <div class="paper-file-section">
                <div>
                  <div class="paper-field-label">Supplementary files</div>
                  <p class="paper-section-note">
                    Optional records for appendices, datasets, code, instruments, or additional figures.
                  </p>
                </div>
                <label class="paper-file-drop">
                  <input type="file" multiple @change="handleSupplementaryFiles" />
                  <span>Add supplementary files</span>
                </label>
                <div v-if="supplementaryFiles.length" class="paper-file-list">
                  <div v-for="(file, index) in supplementaryFiles" :key="`${file.fileName}-${index}`" class="paper-file-row">
                    <span>
                      <strong>{{ file.fileName }}</strong>
                      <small>{{ file.fileRole }} - {{ formatFileSize(file.fileSize) }}</small>
                    </span>
                    <button class="paper-inline-action" type="button" @click="removeSupplementaryFile(index)">
                      Remove
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section v-if="activeStep === 2" class="paper-block">
            <h2 class="paper-block-title">Metadata</h2>
            <div class="paper-field-stack">
              <label class="paper-field">
                Title
                <input v-model.trim="form.title" required placeholder="Enter the full paper title" />
              </label>

              <label class="paper-field">
                Abstract
                <textarea
                  v-model.trim="form.abstractText"
                  required
                  rows="7"
                  placeholder="Summarize the research question, method, findings, and contribution."
                />
              </label>

              <div class="paper-two-column">
                <label class="paper-field">
                  Subject area
                  <input v-model.trim="form.subjectArea" required placeholder="e.g. Information Systems" />
                </label>
                <label class="paper-field">
                  Paper type
                  <select v-model="form.paperType">
                    <option>Research Article</option>
                    <option>Review Article</option>
                    <option>Method Paper</option>
                    <option>Dataset Paper</option>
                    <option>Case Study</option>
                  </select>
                </label>
              </div>

              <div class="paper-system-note">
                <strong>Institution handling</strong>
                <span>
                  The paper's primary institution is derived from the author list, starting with
                  the first author's affiliation. This avoids conflicting institution metadata.
                </span>
              </div>

              <div>
                <div class="paper-field-label">Keywords</div>
                <p class="paper-section-note">
                  Add each keyword separately. This avoids the common problem of treating a keyword list as one long string.
                </p>
                <div class="paper-chip-input">
                  <span v-for="keyword in keywords" :key="keyword" class="paper-pill subject">
                    {{ keyword }}
                    <button type="button" @click="removeKeyword(keyword)">x</button>
                  </span>
                  <input
                    v-model.trim="keywordDraft"
                    placeholder="Type keyword and press Enter"
                    @keydown="handleKeywordKeydown"
                  />
                </div>
              </div>
            </div>
          </section>

          <section v-if="activeStep === 3" class="paper-block">
            <h2 class="paper-block-title">Contributors</h2>
            <p class="paper-section-note">
              Contributors are stored as structured author records for author, institution, and
              future expert-profile data.
            </p>
            <div class="paper-author-editor">
              <div class="paper-author-table">
                <div class="paper-author-table-header">
                  <span>Order</span>
                  <span>Author</span>
                  <span>Edit</span>
                </div>
                <div v-for="(author, index) in authors" :key="index" class="paper-author-table-row">
                  <span class="paper-author-order">{{ index + 1 }}</span>
                  <span class="paper-author-list-name">
                    <strong>{{ author.displayName || `Author ${index + 1}` }}</strong>
                    <small>
                      <span v-if="index === 0">First author</span>
                      <span v-if="author.equalContribution">Co-first author</span>
                      <span v-if="author.correspondingAuthor">Corresponding author</span>
                      <span v-if="!index && !author.equalContribution && !author.correspondingAuthor">
                        Details in edit drawer
                      </span>
                    </small>
                  </span>
                  <span class="paper-author-actions compact">
                    <button class="paper-button small" type="button" @click="openAuthorDrawer(index)">
                      Edit
                    </button>
                    <button
                      class="paper-inline-action"
                      type="button"
                      :disabled="index === 0"
                      @click="moveAuthor(index, -1)"
                    >
                      Up
                    </button>
                    <button
                      class="paper-inline-action"
                      type="button"
                      :disabled="index === authors.length - 1"
                      @click="moveAuthor(index, 1)"
                    >
                      Down
                    </button>
                    <button
                      class="paper-inline-action danger"
                      type="button"
                      :disabled="authors.length === 1"
                      @click="removeAuthor(index)"
                    >
                      Remove
                    </button>
                  </span>
                </div>
              </div>
              <div class="paper-system-note">
                <strong>Co-first author rule</strong>
                <span>
                  Co-first authors must begin with author 1 and be continuous. For example:
                  author 1 and author 2 can both be co-first authors.
                </span>
              </div>
              <div v-if="!coFirstAuthorsValid" class="paper-readiness-panel">
                <div class="paper-readiness-title">Co-first author setup needs attention</div>
                <div class="paper-section-note">
                  Select at least two continuous authors from the start of the list, or clear the co-first marks.
                </div>
              </div>
            </div>
            <button class="paper-button" type="button" @click="addAuthor">Add contributor</button>

            <div v-if="activeAuthor" class="paper-drawer-backdrop" @click.self="closeAuthorDrawer">
              <aside class="paper-author-drawer">
                <div class="paper-author-drawer-header">
                  <div>
                    <div class="paper-page-eyebrow">Contributor Details</div>
                    <h3>Author {{ activeAuthorIndex + 1 }}</h3>
                  </div>
                  <button class="paper-inline-action" type="button" @click="closeAuthorDrawer">Close</button>
                </div>

                <div class="paper-field-stack">
                  <label class="paper-field">
                    Full name
                    <input v-model.trim="activeAuthor.displayName" required placeholder="e.g. Alice Researcher" />
                  </label>
                  <label class="paper-field">
                    Email
                    <input v-model.trim="activeAuthor.email" type="email" placeholder="author@example.edu" />
                  </label>
                  <label class="paper-field">
                    Affiliation
                    <input v-model.trim="activeAuthor.institutionName" placeholder="Example University" />
                  </label>
                  <label class="paper-field">
                    Country / Region
                    <select v-model="activeAuthor.country">
                      <option value="">Select country or region</option>
                      <option v-for="country in countryOptions" :key="country" :value="country">
                        {{ country }}
                      </option>
                    </select>
                  </label>
                  <div class="paper-author-flags">
                    <label class="paper-checkbox">
                      <input v-model="activeAuthor.correspondingAuthor" type="checkbox" />
                      Corresponding author
                    </label>
                    <label class="paper-checkbox">
                      <input v-model="activeAuthor.equalContribution" type="checkbox" />
                      Co-first author
                    </label>
                  </div>
                </div>
              </aside>
            </div>
          </section>

          <section v-if="activeStep === 4" class="paper-block">
            <h2 class="paper-block-title">Declarations</h2>
            <p class="paper-section-note">
              References remain inside the manuscript file in this MVP. These declarations are
              collected separately because they are author confirmations, not extracted metadata.
            </p>

            <div class="paper-declaration-grid">
              <label class="paper-field">
                Funding statement
                <textarea
                  v-model.trim="form.fundingStatement"
                  rows="3"
                  placeholder="State funding sources or write 'No external funding'."
                />
              </label>
              <label class="paper-field">
                Conflict of interest
                <textarea
                  v-model.trim="form.conflictOfInterest"
                  rows="3"
                  placeholder="Declare competing interests or write 'No competing interests declared'."
                />
              </label>
              <label class="paper-field">
                Data availability
                <textarea
                  v-model.trim="form.dataAvailability"
                  rows="3"
                  placeholder="Describe where data, code, or materials can be accessed."
                />
              </label>
              <label class="paper-field">
                Ethics statement
                <textarea
                  v-model.trim="form.ethicsStatement"
                  rows="3"
                  placeholder="State ethics approval, consent, or why it is not applicable."
                />
              </label>
            </div>
          </section>

          <section v-if="activeStep === 5" class="paper-block">
            <h2 class="paper-block-title">Review & Submit</h2>
            <div class="paper-review-grid">
              <div>
                <span class="paper-review-label">Title</span>
                <strong>{{ form.title || 'Missing title' }}</strong>
              </div>
              <div>
                <span class="paper-review-label">Subject</span>
                <strong>{{ form.subjectArea || 'Missing subject' }}</strong>
              </div>
              <div>
                <span class="paper-review-label">Keywords</span>
                <strong>{{ keywords.length }}</strong>
              </div>
              <div>
                <span class="paper-review-label">Contributors</span>
                <strong>{{ validAuthors.length }}</strong>
              </div>
              <div>
                <span class="paper-review-label">Files</span>
                <strong>{{ manuscriptFiles.length + supplementaryFiles.length }}</strong>
              </div>
              <div>
                <span class="paper-review-label">Submission readiness</span>
                <strong>{{ canSubmit ? 'Ready' : 'Incomplete' }}</strong>
              </div>
            </div>
            <div class="paper-readiness-panel" :class="{ ready: canSubmit }">
              <div class="paper-readiness-title">
                {{ canSubmit ? 'Ready for AI screening' : 'Missing before submission' }}
              </div>
              <div v-if="canSubmit" class="paper-section-note">
                This paper can be submitted. The prototype will run screening immediately and publish passed papers.
              </div>
              <div v-else class="paper-readiness-list">
                <span v-for="item in missingReadinessItems" :key="item" class="paper-pill warning">
                  {{ item }}
                </span>
              </div>
            </div>
            <p class="paper-section-note">
              The prototype runs screening immediately after submission. Passed papers appear in the public feed.
            </p>
          </section>

          <div class="paper-submit-footer paper-panel">
            <button class="paper-button" type="button" :disabled="activeStep === 0" @click="previousStep">
              Back
            </button>
            <button
              v-if="activeStep < steps.length - 1"
              class="paper-button primary"
              type="button"
              @click="nextStep"
            >
              Continue
            </button>
            <button
              v-else
              class="paper-button primary"
              type="submit"
              :disabled="submitting || !canSubmit"
            >
              {{ submitting ? 'Submitting...' : 'Submit paper' }}
            </button>
          </div>
        </section>

        <aside class="paper-sidebar">
          <section class="paper-card">
            <h3 class="paper-section-title">Submission Status</h3>
            <p class="paper-section-note">
              Required: checklist, manuscript text, title, abstract, subject, one keyword, one contributor,
              declarations.
            </p>
            <div class="paper-meta-row">
              <span class="paper-pill">{{ keywords.length }} keywords</span>
              <span class="paper-pill">{{ validAuthors.length }} contributors</span>
              <span class="paper-pill">{{ manuscriptFiles.length + supplementaryFiles.length }} files</span>
            </div>
          </section>

          <section class="paper-card">
            <h3 class="paper-section-title">Why this flow</h3>
            <p class="paper-section-note">
              The structure borrows from OJS: readiness check, manuscript, metadata, contributors,
              declarations, and final confirmation. The interface is simplified for a public paper platform.
            </p>
          </section>

          <section class="paper-card">
            <h3 class="paper-section-title">Current Step</h3>
            <p class="paper-section-note">{{ steps[activeStep].helper }}</p>
            <p v-if="message" class="paper-section-note">{{ message }}</p>
          </section>
        </aside>
      </form>
    </div>
  </main>
</template>

<script setup>
import '~/assets/paper-platform.css'
import { authState } from '~/utils/auth'

const router = useRouter()
const { submitPaper } = usePaperApi()

useHead({
  title: 'Submit Paper - Open Research Evaluation',
})

const steps = [
  {
    key: 'requirements',
    label: 'Requirements',
    note: 'Readiness check',
    helper: 'Confirm that the paper is ready to become a public research record.',
  },
  {
    key: 'manuscript',
    label: 'Manuscript',
    note: 'Text or file',
    helper: 'Provide manuscript text for indexing and attach the manuscript file record for the paper page.',
  },
  {
    key: 'metadata',
    label: 'Metadata',
    note: 'Title and keywords',
    helper: 'Enter discoverable metadata. Keywords are stored as separate values.',
  },
  {
    key: 'contributors',
    label: 'Contributors',
    note: 'Authors and institutions',
    helper: 'Add authors as structured contributor records for future author and institution rankings.',
  },
  {
    key: 'declarations',
    label: 'Declarations',
    note: 'Compliance statements',
    helper: 'Confirm standard academic declarations for public accountability.',
  },
  {
    key: 'review',
    label: 'Review',
    note: 'Final check',
    helper: 'Review the submission before creating the public paper record.',
  },
]

const activeStep = ref(0)
const form = reactive({
  title: '',
  abstractText: '',
  subjectArea: '',
  paperType: 'Research Article',
  content: '',
  fundingStatement: '',
  conflictOfInterest: '',
  dataAvailability: '',
  ethicsStatement: '',
})

const requirements = reactive([
  { key: 'original', label: 'The submission is original or properly authorized for public posting.', checked: false },
  { key: 'metadata', label: 'Title, abstract, contributors, and manuscript materials are ready to be entered.', checked: false },
  { key: 'ethics', label: 'Any ethics, data, or conflict-of-interest issues have been considered.', checked: false },
])

const keywordDraft = ref('')
const keywords = ref([])
const authors = ref([
  {
    displayName: '',
    email: '',
    institutionName: '',
    country: '',
    correspondingAuthor: true,
    equalContribution: false,
    contributionRoles: [],
  },
])
const manuscriptFiles = ref([])
const supplementaryFiles = ref([])
const submitting = ref(false)
const message = ref('')
const activeAuthorIndex = ref(-1)

const countryOptions = [
  'United States',
  'United Kingdom',
  'China',
  'Germany',
  'France',
  'Japan',
  'Singapore',
  'Australia',
  'Canada',
  'Netherlands',
  'Switzerland',
  'Sweden',
  'South Korea',
  'India',
  'Other',
]

const validAuthors = computed(() => authors.value.filter((author) => author.displayName))
const hasCorrespondingAuthor = computed(() =>
  validAuthors.value.some((author) => author.correspondingAuthor),
)
const correspondingAuthorsHaveEmail = computed(() =>
  validAuthors.value
    .filter((author) => author.correspondingAuthor)
    .every((author) => Boolean(author.email)),
)
const activeAuthor = computed(() => authors.value[activeAuthorIndex.value] || null)
const coFirstAuthorsValid = computed(() => {
  const coFirstIndexes = authors.value
    .map((author, index) => (author.equalContribution ? index : -1))
    .filter((index) => index >= 0)
  if (coFirstIndexes.length === 0) return true
  if (coFirstIndexes.length === 1) return false
  return coFirstIndexes.every((index, position) => index === position)
})
const requirementsComplete = computed(() => requirements.every((item) => item.checked))
const declarationsComplete = computed(
  () =>
    Boolean(form.fundingStatement) &&
    Boolean(form.conflictOfInterest) &&
    Boolean(form.dataAvailability) &&
    Boolean(form.ethicsStatement),
)
const missingReadinessItems = computed(() => {
  const missing = []
  if (!authState.loggedIn) missing.push('Sign in')
  if (!requirementsComplete.value) missing.push('Requirements checklist')
  if (!form.content) missing.push('Manuscript text')
  if (!form.title) missing.push('Title')
  if (!form.abstractText) missing.push('Abstract')
  if (!form.subjectArea) missing.push('Subject area')
  if (keywords.value.length === 0) missing.push('Keywords')
  if (validAuthors.value.length === 0) missing.push('Contributors')
  if (!hasCorrespondingAuthor.value) missing.push('Corresponding author')
  if (!correspondingAuthorsHaveEmail.value) missing.push('Corresponding author email')
  if (!coFirstAuthorsValid.value) missing.push('Co-first author order')
  if (!form.fundingStatement) missing.push('Funding statement')
  if (!form.conflictOfInterest) missing.push('Conflict of interest')
  if (!form.dataAvailability) missing.push('Data availability')
  if (!form.ethicsStatement) missing.push('Ethics statement')
  return missing
})

const canSubmit = computed(
  () =>
    authState.loggedIn &&
    requirementsComplete.value &&
    form.title &&
    form.abstractText &&
    form.subjectArea &&
    form.content &&
    keywords.value.length > 0 &&
    validAuthors.value.length > 0 &&
    hasCorrespondingAuthor.value &&
    correspondingAuthorsHaveEmail.value &&
    coFirstAuthorsValid.value &&
    declarationsComplete.value,
)

const isStepComplete = (index) => {
  if (index === 0) return requirementsComplete.value
  if (index === 1) return Boolean(form.content)
  if (index === 2) return Boolean(form.title && form.abstractText && form.subjectArea && keywords.value.length)
  if (index === 3) {
    return (
      validAuthors.value.length > 0 &&
      hasCorrespondingAuthor.value &&
      correspondingAuthorsHaveEmail.value &&
      coFirstAuthorsValid.value
    )
  }
  if (index === 4) return declarationsComplete.value
  return canSubmit.value
}

const nextStep = () => {
  addKeyword()
  if (!isStepComplete(activeStep.value)) {
    message.value = stepErrorMessage(activeStep.value)
    return
  }
  message.value = ''
  if (activeStep.value < steps.length - 1) {
    activeStep.value += 1
  }
}

const previousStep = () => {
  if (activeStep.value > 0) {
    activeStep.value -= 1
  }
}

const addKeyword = () => {
  const value = keywordDraft.value.trim().replace(/,$/, '')
  if (!value) return
  if (!keywords.value.includes(value)) {
    keywords.value.push(value)
  }
  keywordDraft.value = ''
}

const handleKeywordKeydown = (event) => {
  if (event.key !== 'Enter' && event.key !== ',') return
  event.preventDefault()
  addKeyword()
}

const removeKeyword = (keyword) => {
  keywords.value = keywords.value.filter((item) => item !== keyword)
}

const addAuthor = () => {
  authors.value.push({
    displayName: '',
    email: '',
    institutionName: '',
    country: '',
    correspondingAuthor: false,
    equalContribution: false,
    contributionRoles: [],
  })
  activeAuthorIndex.value = authors.value.length - 1
}

const openAuthorDrawer = (index) => {
  activeAuthorIndex.value = index
}

const closeAuthorDrawer = () => {
  activeAuthorIndex.value = -1
}

const moveAuthor = (index, direction) => {
  const targetIndex = index + direction
  if (targetIndex < 0 || targetIndex >= authors.value.length) return
  const nextAuthors = [...authors.value]
  const [author] = nextAuthors.splice(index, 1)
  nextAuthors.splice(targetIndex, 0, author)
  authors.value = nextAuthors
  activeAuthorIndex.value = targetIndex
}

const removeAuthor = (index) => {
  if (authors.value.length === 1) return
  authors.value.splice(index, 1)
  if (activeAuthorIndex.value >= authors.value.length) {
    activeAuthorIndex.value = authors.value.length - 1
  }
}

const toFileRecord = (file, fileRole) => ({
  fileName: file.name,
  fileType: file.type || 'application/octet-stream',
  fileSize: file.size,
  fileRole,
})

const handleManuscriptFile = (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  manuscriptFiles.value = [toFileRecord(file, 'Manuscript')]
  event.target.value = ''
}

const handleSupplementaryFiles = (event) => {
  const files = Array.from(event.target.files || [])
  supplementaryFiles.value.push(...files.map((file) => toFileRecord(file, 'Supplementary File')))
  event.target.value = ''
}

const removeManuscriptFile = (index) => {
  manuscriptFiles.value.splice(index, 1)
}

const removeSupplementaryFile = (index) => {
  supplementaryFiles.value.splice(index, 1)
}

const formatFileSize = (size) => {
  if (!size) return 'Unknown size'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

const stepErrorMessage = (index) => {
  if (index === 0) return 'Please confirm all requirements before continuing.'
  if (index === 1) return 'Please provide manuscript text before continuing.'
  if (index === 2) return 'Please complete title, abstract, subject area, and at least one keyword.'
  if (index === 3) {
    return 'Please add contributors, mark a corresponding author with email, and keep co-first authors continuous.'
  }
  if (index === 4) return 'Please complete the declaration fields.'
  return 'Please complete the submission before continuing.'
}

const submit = async () => {
  addKeyword()
  if (!canSubmit.value) {
    message.value = authState.loggedIn
      ? 'Please complete the required fields before submitting.'
      : 'Please sign in before submitting a paper.'
    return
  }

  submitting.value = true
  message.value = ''
  try {
    const paper = await submitPaper({
      ...form,
      keywords: keywords.value,
      references: [],
      manuscriptFiles: manuscriptFiles.value,
      supplementaryFiles: supplementaryFiles.value,
      authors: validAuthors.value,
    })
    await router.push(`/papers/${paper.id}`)
  } catch (error) {
    message.value = 'Unable to submit paper. Please check the required fields and try again.'
  } finally {
    submitting.value = false
  }
}
</script>
