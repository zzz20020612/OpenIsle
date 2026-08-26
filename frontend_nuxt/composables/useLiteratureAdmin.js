import { getToken } from '~/utils/auth'

export const useLiteratureAdmin = () => {
  const config = useRuntimeConfig()
  const base = `${config.public.apiBaseUrl}/api/literature/admin`
  const headers = () => ({ Authorization: `Bearer ${getToken()}` })
  const request = (path, options = {}) => $fetch(`${base}${path}`, {
    ...options,
    headers: { ...headers(), ...(options.headers || {}) },
  })
  return {
    get: (path, params) => request(path, { params }),
    post: (path, body = {}) => request(path, { method: 'POST', body }),
  }
}
