import { getToken } from '~/utils/auth'

export const usePaperApi = () => {
  const config = useRuntimeConfig()
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
    getPaperFilters,
    getPaper,
    submitPaper,
    ratePaper,
    getTopRatedPapers,
    getAuthorRankings,
    getInstitutionRankings,
    listAdminPapers,
    runAdminPaperAction,
    runAdminPostAction,
    runPostAction,
  }
}
