import { createEmptyArticle } from '~/config/paperArticleConfig'

export const usePaperArticleDraft = (draftId) => {
  const api = usePaperApi()
  const article = ref(createEmptyArticle())
  const loading = ref(false)
  const saveState = ref('idle')
  const error = ref('')
  const validation = ref({ valid: false, issues: [] })
  const dirty = ref(false)
  let saveTimer = null
  let hydrating = false

  const replaceFromServer = (value) => {
    hydrating = true
    article.value = value
    hydrating = false
  }

  const saveLabel = computed(() => ({
    idle: 'All changes saved',
    dirty: 'Unsaved changes',
    saving: 'Saving...',
    saved: 'All changes saved',
    error: 'Changes not saved',
    conflict: 'Changes not saved',
  }[saveState.value] || ''))

  const load = async () => {
    loading.value = true
    error.value = ''
    try {
      hydrating = true
      replaceFromServer({ ...createEmptyArticle(), ...(await api.getDraftArticle(draftId)) })
      dirty.value = false
      saveState.value = 'idle'
    } catch (cause) {
      error.value = cause?.data?.error || cause?.message || 'Unable to open the article editor.'
      throw cause
    } finally {
      hydrating = false
      loading.value = false
    }
  }

  const saveNow = async () => {
    if (!dirty.value || hydrating || saveState.value === 'saving') return article.value
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = null
    saveState.value = 'saving'
    error.value = ''
    try {
      const saved = await api.updateDraftArticle(draftId, article.value)
      replaceFromServer(saved)
      dirty.value = false
      saveState.value = 'saved'
      return saved
    } catch (cause) {
      const status = cause?.statusCode || cause?.response?.status
      saveState.value = status === 409 ? 'conflict' : 'error'
      error.value = status === 409
        ? 'This article changed in another tab. Reload before continuing.'
        : 'Article autosave was interrupted. Check your connection and try again.'
      throw cause
    }
  }

  const scheduleSave = () => {
    if (hydrating) return
    dirty.value = true
    saveState.value = 'dirty'
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = setTimeout(() => saveNow().catch(() => {}), 800)
  }

  const flush = () => {
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = null
    return saveNow()
  }

  const validate = async () => {
    await flush()
    validation.value = await api.validateDraftArticle(draftId)
    return validation.value
  }

  const markReady = async () => {
    await flush()
    const result = await api.markDraftArticleReady(draftId, article.value)
    replaceFromServer(result)
    validation.value = { valid: true, issues: [] }
    dirty.value = false
    saveState.value = 'saved'
    return result
  }

  const reopen = async () => {
    replaceFromServer(await api.reopenDraftArticle(draftId))
    validation.value = { valid: false, issues: [] }
    return article.value
  }

  onBeforeUnmount(() => { if (saveTimer) clearTimeout(saveTimer) })

  return {
    article,
    loading,
    saveState,
    saveLabel,
    error,
    validation,
    dirty,
    load,
    saveNow,
    scheduleSave,
    flush,
    validate,
    markReady,
    reopen,
  }
}
