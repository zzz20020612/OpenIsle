import { getToken } from '~/utils/auth'

export const usePaperApi = () => {
  const config = useRuntimeConfig()
  const publicApiBaseUrl = process.server
    ? (process.env.NUXT_PUBLIC_API_BASE_URL || config.public.apiBaseUrl)
    : config.public.apiBaseUrl
  const apiBaseUrl =
    process.server && config.public.apiBaseUrlSsr
      ? config.public.apiBaseUrlSsr
      : config.public.apiBaseUrl

  const authHeaders = () => {
    const token = getToken()
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  const listPapers = (params = {}) =>
    $fetch(`${apiBaseUrl}/api/papers`, {
      params: {
        page: params.page ?? 0,
        pageSize: params.pageSize ?? 20,
        subject: params.subject || undefined,
        minScore: params.minScore ?? undefined,
        sort: params.sort || 'latest',
      },
    })

  const getPaperFilters = () => $fetch(`${apiBaseUrl}/api/papers/filters`)

  const listMyPapers = () =>
    $fetch(`${apiBaseUrl}/api/papers/mine`, { headers: authHeaders() })

  const getPaper = (paperId) =>
    $fetch(`${apiBaseUrl}/api/papers/${paperId}`, {
      headers: authHeaders(),
    })

  const submitPaper = (payload) =>
    $fetch(`${apiBaseUrl}/api/papers`, {
      method: 'POST',
      headers: authHeaders(),
      body: payload,
    })

  const createSubmissionDraft = () =>
    $fetch(`${apiBaseUrl}/api/paper-submission-drafts`, {
      method: 'POST',
      headers: authHeaders(),
    })

  const createRevisionDraft = (paperId) =>
    $fetch(`${apiBaseUrl}/api/paper-submission-drafts/revisions/${paperId}`, {
      method: 'POST',
      headers: authHeaders(),
    })

  const getCurrentSubmissionDraft = (kind = 'ANY') =>
    $fetch(`${apiBaseUrl}/api/paper-submission-drafts/current`, {
      headers: authHeaders(),
      params: { kind },
    })

  const listSubmissionDrafts = (kind = 'ANY') =>
    $fetch(`${apiBaseUrl}/api/paper-submission-drafts`, {
      headers: authHeaders(),
      params: { kind },
    })

  const getSubmissionDraft = (draftId) =>
    $fetch(`${apiBaseUrl}/api/paper-submission-drafts/${draftId}`, {
      headers: authHeaders(),
    })

  const updateSubmissionDraft = (draftId, payload) =>
    $fetch(`${apiBaseUrl}/api/paper-submission-drafts/${draftId}`, {
      method: 'PATCH',
      headers: authHeaders(),
      body: payload,
    })

  const renameSubmissionDraft = (draftId, displayName) =>
    $fetch(`${apiBaseUrl}/api/paper-submission-drafts/${draftId}/name`, {
      method: 'PATCH',
      headers: authHeaders(),
      body: { displayName },
    })

  const discardSubmissionDraft = (draftId) =>
    $fetch(`${apiBaseUrl}/api/paper-submission-drafts/${draftId}`, {
      method: 'DELETE',
      headers: authHeaders(),
    })

  const validateSubmissionDraft = (draftId) =>
    $fetch(`${apiBaseUrl}/api/paper-submission-drafts/${draftId}/validate`, {
      method: 'POST',
      headers: authHeaders(),
    })

  const submitSubmissionDraft = (draftId, payload) =>
    $fetch(`${apiBaseUrl}/api/paper-submission-drafts/${draftId}/submit`, {
      method: 'POST',
      headers: authHeaders(),
      body: payload,
    })

  const presignSubmissionFile = (draftId, payload) =>
    $fetch(`${apiBaseUrl}/api/paper-submission-drafts/${draftId}/files/presign`, {
      method: 'POST',
      headers: authHeaders(),
      body: payload,
    })

  const updateSubmissionFile = (draftId, fileId, payload) =>
    $fetch(`${apiBaseUrl}/api/paper-submission-drafts/${draftId}/files/${fileId}`, {
      method: 'PATCH',
      headers: authHeaders(),
      body: payload,
    })

  const removeSubmissionFile = (draftId, fileId) =>
    $fetch(`${apiBaseUrl}/api/paper-submission-drafts/${draftId}/files/${fileId}`, {
      method: 'DELETE',
      headers: authHeaders(),
    })

  const getDraftArticle = (draftId) =>
    $fetch(`${apiBaseUrl}/api/paper-submission-drafts/${draftId}/article`, {
      headers: authHeaders(),
    })

  const updateDraftArticle = (draftId, payload) =>
    $fetch(`${apiBaseUrl}/api/paper-submission-drafts/${draftId}/article`, {
      method: 'PUT',
      headers: authHeaders(),
      body: payload,
    })

  const validateDraftArticle = (draftId) =>
    $fetch(`${apiBaseUrl}/api/paper-submission-drafts/${draftId}/article/validate`, {
      method: 'POST',
      headers: authHeaders(),
    })

  const markDraftArticleReady = (draftId, payload) =>
    $fetch(`${apiBaseUrl}/api/paper-submission-drafts/${draftId}/article/ready`, {
      method: 'POST',
      headers: authHeaders(),
      body: payload,
    })

  const reopenDraftArticle = (draftId) =>
    $fetch(`${apiBaseUrl}/api/paper-submission-drafts/${draftId}/article/reopen`, {
      method: 'POST',
      headers: authHeaders(),
    })

  const getPaperArticle = (paperId) =>
    $fetch(`${apiBaseUrl}/api/papers/${paperId}/article`, {
      headers: authHeaders(),
    })

  const paperFileContentUrl = (paperId, fileId, mode = 'download') =>
    `${publicApiBaseUrl}/api/papers/${paperId}/files/${fileId}/content?mode=${encodeURIComponent(mode)}`

  const draftFileContentUrl = (draftId, fileId, inline = true) =>
    `${publicApiBaseUrl}/api/paper-submission-drafts/${draftId}/files/${fileId}/content?inline=${inline}`

  const ratePaper = (paperId, payload) =>
    $fetch(`${apiBaseUrl}/api/papers/${paperId}/ratings`, {
      method: 'POST',
      headers: authHeaders(),
      body: payload,
    })

  const getTopRatedPapers = (limit = 20) =>
    $fetch(`${apiBaseUrl}/api/papers/rankings/top-rated`, {
      params: { limit },
    })

  const getAuthorRankings = (limit = 20) =>
    $fetch(`${apiBaseUrl}/api/papers/rankings/authors`, {
      params: { limit },
    })

  const getInstitutionRankings = (limit = 20) =>
    $fetch(`${apiBaseUrl}/api/papers/rankings/institutions`, {
      params: { limit },
    })

  const getExpert = (expertId) => $fetch(`${apiBaseUrl}/api/experts/${expertId}`)

  const listAdminPapers = (params = {}) =>
    $fetch(`${apiBaseUrl}/api/admin/papers`, {
      headers: authHeaders(),
      params: {
        page: params.page ?? 0,
        pageSize: params.pageSize ?? 30,
        status: params.status || undefined,
      },
    })

  const runAdminPaperAction = (paperId, action) =>
    $fetch(`${apiBaseUrl}/api/admin/papers/${paperId}/${action}`, {
      method: 'POST',
      headers: authHeaders(),
    })

  const clearPublicPaperCache = () => {
    clearNuxtData((key) =>
      [
        'papers:feed',
        'papers:top-rated:sidebar',
        'rankings:papers',
        'rankings:authors',
        'rankings:institutions',
      ].includes(key),
    )
  }

  const runAdminPostAction = (postId, action) =>
    $fetch(`${apiBaseUrl}/api/admin/posts/${postId}/${action}`, {
      method: 'POST',
      headers: authHeaders(),
    })

  const runPostAction = (postId, action) =>
    $fetch(`${apiBaseUrl}/api/posts/${postId}/${action}`, {
      method: 'POST',
      headers: authHeaders(),
    })

  return {
    listPapers,
    listMyPapers,
    getPaperFilters,
    getPaper,
    submitPaper,
    createSubmissionDraft,
    createRevisionDraft,
    getCurrentSubmissionDraft,
    listSubmissionDrafts,
    getSubmissionDraft,
    updateSubmissionDraft,
    renameSubmissionDraft,
    discardSubmissionDraft,
    validateSubmissionDraft,
    submitSubmissionDraft,
    presignSubmissionFile,
    updateSubmissionFile,
    removeSubmissionFile,
    getDraftArticle,
    updateDraftArticle,
    validateDraftArticle,
    markDraftArticleReady,
    reopenDraftArticle,
    getPaperArticle,
    paperFileContentUrl,
    draftFileContentUrl,
    ratePaper,
    getTopRatedPapers,
    getAuthorRankings,
    getInstitutionRankings,
    getExpert,
    listAdminPapers,
    runAdminPaperAction,
    clearPublicPaperCache,
    runAdminPostAction,
    runPostAction,
  }
}
