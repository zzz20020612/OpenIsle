export const AuthResultStatus = Object.freeze({
  AUTHENTICATED: 'authenticated',
  INVALID: 'invalid',
  UNAVAILABLE: 'unavailable',
  ANONYMOUS: 'anonymous',
  STALE: 'stale',
})

export const isSameToken = (requestToken, currentToken) =>
  Boolean(requestToken) && requestToken === currentToken

export const shouldInvalidateToken = ({ requestToken, currentToken, status, error }) =>
  status === 401 &&
  error === 'Invalid or expired token' &&
  isSameToken(requestToken, currentToken)

export const createSingleFlight = () => {
  const requests = new Map()

  return (key, operation) => {
    if (requests.has(key)) return requests.get(key)

    const request = Promise.resolve()
      .then(operation)
      .finally(() => {
        if (requests.get(key) === request) requests.delete(key)
      })

    requests.set(key, request)
    return request
  }
}

