import { clearToken, getToken } from '~/utils/auth'

const bearerTokenFromRequest = (input: RequestInfo | URL, init?: RequestInit) => {
  const headers = new Headers(input instanceof Request ? input.headers : undefined)
  if (init?.headers) {
    new Headers(init.headers).forEach((value, key) => headers.set(key, value))
  }

  const authorization = headers.get('Authorization')
  return authorization?.startsWith('Bearer ') ? authorization.slice(7) : null
}

export default defineNuxtPlugin(() => {
  if (import.meta.client) {
    const originalFetch = window.fetch
    window.fetch = async (input, init) => {
      const requestToken = bearerTokenFromRequest(input, init)
      const response = await originalFetch(input, init)
      if (response.status === 401) {
        try {
          const data = await response.clone().json()
          if (
            data?.error === 'Invalid or expired token' &&
            requestToken &&
            requestToken === getToken()
          ) {
            clearToken()
          }
        } catch (e) {
          // ignore JSON parsing errors
        }
      }
      return response
    }
  }
})
