export const useLiteratureApi = () => {
  const config = useRuntimeConfig()
  const apiBaseUrl =
    process.server && config.public.apiBaseUrlSsr
      ? config.public.apiBaseUrlSsr
      : config.public.apiBaseUrl

  const request = (path, options = {}) => $fetch(`${apiBaseUrl}/api/literature${path}`, options)

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
  }
}
