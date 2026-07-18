import {
  SAVE_STATUS_LABELS,
  createEmptyAffiliation,
  createEmptyAuthor,
  createEmptySubmissionForm,
} from '~/config/paperSubmissionConfig'

const clone = (value) => JSON.parse(JSON.stringify(value))

const normalizeAuthor = (author = {}, index = 0) => {
  const fallback = createEmptyAuthor(index === 0)
  const affiliations = Array.isArray(author.affiliations) && author.affiliations.length
    ? author.affiliations.map((item, affiliationIndex) => ({
      ...createEmptyAffiliation(),
      ...item,
      primaryAffiliation: item?.primaryAffiliation ?? affiliationIndex === 0,
    }))
    : [{
      ...createEmptyAffiliation(),
      organizationName: author.institutionName || '',
      country: author.country || '',
    }]
  return {
    ...fallback,
    ...author,
    authorRole: author.authorRole || (author.correspondingAuthor ? 'Corresponding Author' : 'Author'),
    contributionRoles: Array.isArray(author.contributionRoles) ? author.contributionRoles : [],
    affiliations,
  }
}

const normalizeForm = (value = {}) => {
  const fallback = createEmptySubmissionForm()
  return {
    ...fallback,
    ...value,
    keywords: Array.isArray(value.keywords) ? value.keywords : [],
    references: Array.isArray(value.references) ? value.references : [],
    authors: Array.isArray(value.authors) && value.authors.length
      ? value.authors.map(normalizeAuthor)
      : fallback.authors,
    funding: Array.isArray(value.funding) ? value.funding : [],
  }
}

export const usePaperSubmissionDraft = () => {
  const api = usePaperApi()
  const draft = ref(null)
  const files = ref([])
  const form = reactive(createEmptySubmissionForm())
  const currentSection = ref('manuscript-type')
  const loading = ref(false)
  const saveState = ref('idle')
  const uploadState = reactive({ active: 0, role: '', error: '' })
  const validation = ref({ valid: false, issues: [] })
  const conflict = ref(null)
  const lastError = ref('')
  const dirty = ref(false)
  let saveTimer = null
  let hydrating = false

  const saveStatusLabel = computed(() => SAVE_STATUS_LABELS[saveState.value] || '')
  const hasPendingWork = computed(() => dirty.value || uploadState.active > 0)

  const hydrate = (record) => {
    hydrating = true
    draft.value = record
    files.value = Array.isArray(record?.files) ? record.files : []
    currentSection.value = record?.currentSection || 'manuscript-type'
    const normalized = normalizeForm(record?.formData)
    Object.keys(form).forEach((key) => delete form[key])
    Object.assign(form, normalized)
    dirty.value = false
    saveState.value = 'idle'
    conflict.value = null
    nextTick(() => {
      hydrating = false
    })
  }

  const loadOrCreate = async (draftId) => {
    loading.value = true
    lastError.value = ''
    try {
      let record = draftId ? await api.getSubmissionDraft(draftId) : null
      if (!record) {
        record = await api.getCurrentSubmissionDraft()
      }
      if (!record) {
        record = await api.createSubmissionDraft()
      }
      hydrate(record)
      return record
    } catch (error) {
      lastError.value = error?.data?.error || error?.message || 'Unable to open the submission draft.'
      throw error
    } finally {
      loading.value = false
    }
  }

  const saveNow = async () => {
    if (!draft.value || hydrating || !dirty.value || saveState.value === 'saving') return draft.value
    if (saveTimer) {
      clearTimeout(saveTimer)
      saveTimer = null
    }
    saveState.value = 'saving'
    lastError.value = ''
    try {
      const updated = await api.updateSubmissionDraft(draft.value.id, {
        version: draft.value.version,
        currentSection: currentSection.value,
        formData: clone(form),
      })
      draft.value = { ...draft.value, ...updated }
      dirty.value = false
      conflict.value = null
      saveState.value = 'saved'
      return draft.value
    } catch (error) {
      const status = error?.statusCode || error?.response?.status
      if (status === 409) {
        conflict.value = {
          currentVersion: error?.data?.currentVersion,
          message: error?.data?.error || 'This draft changed in another tab.',
        }
        saveState.value = 'conflict'
      } else {
        saveState.value = 'error'
      }
      lastError.value = error?.data?.error || error?.message || 'Unable to save changes.'
      throw error
    }
  }

  const scheduleSave = () => {
    if (hydrating || !draft.value) return
    dirty.value = true
    saveState.value = 'dirty'
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = setTimeout(() => {
      saveNow().catch(() => {})
    }, 800)
  }

  const flush = async () => {
    if (saveTimer) {
      clearTimeout(saveTimer)
      saveTimer = null
    }
    return saveNow()
  }

  const setCurrentSection = (sectionId) => {
    if (!sectionId || currentSection.value === sectionId) return
    currentSection.value = sectionId
    scheduleSave()
  }

  const replaceFile = (nextFile) => {
    const index = files.value.findIndex((item) => item.id === nextFile.id)
    if (index >= 0) {
      files.value.splice(index, 1, nextFile)
    } else {
      files.value.push(nextFile)
    }
    files.value.sort((left, right) =>
      (left.sortOrder ?? 0) - (right.sortOrder ?? 0) || left.id - right.id,
    )
    validation.value = { valid: false, issues: [] }
  }

  const uploadFile = async (file, metadata) => {
    if (!draft.value) throw new Error('Submission draft is not ready.')
    uploadState.active += 1
    uploadState.role = metadata.role
    uploadState.error = ''
    let presign = null
    try {
      presign = await api.presignSubmissionFile(draft.value.id, {
        fileName: file.name,
        displayName: metadata.displayName || file.name,
        contentType: file.type || 'application/octet-stream',
        fileSize: file.size,
        role: metadata.role,
        description: metadata.description || null,
        visibility: metadata.visibility,
      })
      replaceFile(presign.file)
      const response = await fetch(presign.uploadUrl, {
        method: 'PUT',
        headers: presign.uploadHeaders || {},
        body: file,
      })
      if (!response.ok) {
        throw new Error(`Upload failed with status ${response.status}`)
      }
      const uploaded = await api.updateSubmissionFile(draft.value.id, presign.fileId, {
        uploadStatus: 'UPLOADED',
      })
      replaceFile(uploaded)
      return uploaded
    } catch (error) {
      uploadState.error = error?.data?.error || error?.message || 'Unable to upload this file.'
      if (presign?.fileId) {
        try {
          const failed = await api.updateSubmissionFile(draft.value.id, presign.fileId, {
            uploadStatus: 'FAILED',
          })
          replaceFile(failed)
        } catch {
          // Keep the original upload error as the actionable message.
        }
      }
      throw error
    } finally {
      uploadState.active -= 1
      if (uploadState.active === 0) uploadState.role = ''
    }
  }

  const updateFile = async (fileId, payload) => {
    const updated = await api.updateSubmissionFile(draft.value.id, fileId, payload)
    replaceFile(updated)
    return updated
  }

  const removeFile = async (fileId) => {
    await api.removeSubmissionFile(draft.value.id, fileId)
    files.value = files.value.filter((item) => item.id !== fileId)
    validation.value = { valid: false, issues: [] }
  }

  const validate = async () => {
    await flush()
    validation.value = await api.validateSubmissionDraft(draft.value.id)
    return validation.value
  }

  const discard = async () => {
    if (!draft.value) return
    await api.discardSubmissionDraft(draft.value.id)
    dirty.value = false
  }

  const issuesForSection = (sectionId) =>
    (validation.value?.issues || []).filter((issue) => issue.section === sectionId)

  const handleBeforeUnload = (event) => {
    if (!hasPendingWork.value) return
    event.preventDefault()
    event.returnValue = ''
  }

  const stopFormWatch = watch(form, scheduleSave, { deep: true })

  onMounted(() => window.addEventListener('beforeunload', handleBeforeUnload))
  onBeforeUnmount(() => {
    if (saveTimer) clearTimeout(saveTimer)
    stopFormWatch()
    window.removeEventListener('beforeunload', handleBeforeUnload)
  })

  return {
    draft,
    files,
    form,
    currentSection,
    loading,
    saveState,
    saveStatusLabel,
    uploadState,
    validation,
    conflict,
    lastError,
    dirty,
    loadOrCreate,
    saveNow,
    flush,
    setCurrentSection,
    uploadFile,
    updateFile,
    removeFile,
    validate,
    discard,
    issuesForSection,
  }
}
