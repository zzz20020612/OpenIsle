import { getToken } from '~/utils/auth'

export const useLiteratureApi = () => {
  const config = useRuntimeConfig()
  const apiBaseUrl =
    process.server && config.public.apiBaseUrlSsr
      ? config.public.apiBaseUrlSsr
      : config.public.apiBaseUrl

  const request = (path, options = {}) => $fetch(`${apiBaseUrl}/api/literature${path}`, options)
  const authHeaders = () => {
    const token = getToken()
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  return {
    listLiterature: (params = {}) =>
      request('/papers', {
        params: {
          q: params.q || undefined,
          sort: params.sort || 'year_desc',
          limit: params.limit ?? 30,
          offset: params.offset ?? 0,
        },
      }),
    getLiterature: (paperId) => request(`/papers/${paperId}`),
    getKnowledge: (paperId) => request(`/papers/${paperId}/knowledge`),
    getMethods: (paperId) => request(`/papers/${paperId}/methods`),
    getDataPoints: (paperId) => request(`/papers/${paperId}/data-points`),
    getScore: (paperId) => request(`/papers/${paperId}/score`),
    listRatings: (paperId) => request(`/papers/${paperId}/ratings`),
    getMyRating: (paperId) => request(`/papers/${paperId}/ratings/me`, { headers: authHeaders() }),
    rateLiterature: (paperId, payload) =>
      request(`/papers/${paperId}/ratings`, {
        method: 'POST',
        headers: authHeaders(),
        body: payload,
      }),
    getPaperRankings: (limit = 50) => request('/rankings/papers', { params: { limit } }),
    getAuthorRankings: (limit = 50) => request('/rankings/authors', { params: { limit } }),
  }
}
