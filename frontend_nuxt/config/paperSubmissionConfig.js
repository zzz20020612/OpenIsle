export const SUBMISSION_SECTIONS = [
  { id: 'manuscript-type', label: 'Manuscript Type' },
  { id: 'file-upload', label: 'File Upload' },
  { id: 'manuscript-information', label: 'Manuscript Information' },
  { id: 'author-information', label: 'Author Information' },
  { id: 'funding-information', label: 'Funding Information' },
  { id: 'details-comments', label: 'Details & Comments' },
]

export const MANUSCRIPT_TYPES = [
  {
    value: 'Research Article',
    label: 'Research Article',
    description: 'Original research with a defined question, method, results, and contribution.',
  },
  {
    value: 'Review',
    label: 'Review',
    description: 'A critical synthesis of an established or emerging research area.',
  },
]

export const REQUIRED_FILE_ROWS = [
  {
    role: 'MANUSCRIPT',
    label: 'Manuscript File',
    description: 'The editable manuscript source. DOCX is required for this release.',
    accept: '.docx',
    visibility: 'PUBLIC',
  },
  {
    role: 'COVER_LETTER',
    label: 'Cover Letter',
    description: 'A short letter introducing the work and its relevance.',
    accept: '.doc,.docx,.pdf,.rtf,.txt',
    visibility: 'PRIVATE',
  },
  {
    role: 'TOC_GRAPHIC',
    label: 'TOC Graphic',
    description: 'A clear raster image used in the paper record and discovery views.',
    accept: '.png,.jpg,.jpeg,.webp,.gif',
    visibility: 'PUBLIC',
  },
]

export const OPTIONAL_FILE_ROLES = [
  { value: 'SUPPORTING_INFORMATION', label: 'Supporting Information' },
  { value: 'REVIEW_ONLY', label: 'Review Only' },
  { value: 'PDF_VERSION', label: 'PDF Version' },
  { value: 'LATEX_SOURCE', label: 'LaTeX Source' },
  { value: 'DATASET', label: 'Dataset' },
  { value: 'CODE', label: 'Code' },
  { value: 'OTHER', label: 'Other' },
]

export const CONTRIBUTION_ROLES = [
  'Conceptualization',
  'Data Curation',
  'Formal Analysis',
  'Funding Acquisition',
  'Investigation',
  'Methodology',
  'Project Administration',
  'Resources',
  'Software',
  'Supervision',
  'Validation',
  'Visualization',
  'Writing - Original Draft',
  'Writing - Review & Editing',
]

export const AUTHOR_ROLES = ['Author', 'Corresponding Author']

export const COUNTRY_OPTIONS = [
  'Australia',
  'Canada',
  'China',
  'France',
  'Germany',
  'India',
  'Japan',
  'Netherlands',
  'Singapore',
  'South Korea',
  'Sweden',
  'Switzerland',
  'United Kingdom',
  'United States',
  'Other',
]

export const SAVE_STATUS_LABELS = {
  idle: 'All changes saved',
  dirty: 'Unsaved changes',
  saving: 'Saving...',
  saved: 'All changes saved',
  error: 'Changes not saved',
  conflict: 'Changes not saved',
}

export const createEmptyAffiliation = () => ({
  organizationName: '',
  department: '',
  addressLine1: '',
  addressLine2: '',
  country: '',
  region: '',
  city: '',
  postalCode: '',
  primaryAffiliation: true,
})

export const createEmptyAuthor = (correspondingAuthor = false) => ({
  displayName: '',
  givenName: '',
  middleName: '',
  familyName: '',
  email: '',
  orcid: '',
  authorRole: correspondingAuthor ? 'Corresponding Author' : 'Author',
  institutionName: '',
  country: '',
  correspondingAuthor,
  equalContribution: false,
  contributionRoles: [],
  affiliations: [createEmptyAffiliation()],
})

export const createEmptySubmissionForm = () => ({
  title: '',
  abstractText: '',
  subjectArea: '',
  paperType: 'Research Article',
  keywords: [],
  references: [],
  content: '',
  authors: [createEmptyAuthor(true)],
  funding: [],
  noFundingReceived: false,
  fundingStatement: '',
  conflictOfInterest: '',
  dataAvailability: '',
  ethicsStatement: '',
  preprintStatement: '',
  aiUseDisclosure: '',
  allAuthorsConsent: false,
  originalityConfirmed: false,
  rightsConfirmed: false,
  correspondingAuthorContactConfirmed: false,
  privateComments: '',
})
