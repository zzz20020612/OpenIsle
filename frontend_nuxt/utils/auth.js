import { reactive } from 'vue'
import {
  AuthResultStatus,
  createSingleFlight,
  shouldInvalidateToken,
} from './authSessionCore.js'
import { toUserFacingError } from './userFacingError.js'

const TOKEN_KEY = 'token'
const singleFlight = createSingleFlight()

const initialToken = import.meta.client ? localStorage.getItem(TOKEN_KEY) : null

export const authState = reactive({
  loggedIn: Boolean(initialToken),
  status: initialToken ? 'checking' : 'anonymous',
  lastError: null,
  userId: null,
  username: null,
  role: null,
  avatar: null,
})

export function getToken() {
  return import.meta.client ? localStorage.getItem(TOKEN_KEY) : null
}

const authResult = (status, extra = {}) => ({ status, ...extra })

const readResponseData = (response) => response.json().catch(() => ({}))

const unavailableResult = (message = 'Unable to verify your session right now.') =>
  authResult(AuthResultStatus.UNAVAILABLE, { message })

export function setUserInfo(user) {
  if (!import.meta.client) return
  authState.userId = user.id
  authState.username = user.username
  authState.avatar = user.avatar
  authState.role = user.role
}

export function clearUserInfo() {
  if (!import.meta.client) return
  authState.userId = null
  authState.username = null
  authState.avatar = null
  authState.role = null
}

export function clearToken(expectedToken = null) {
  if (!import.meta.client) return false
  if (expectedToken && getToken() !== expectedToken) return false

  localStorage.removeItem(TOKEN_KEY)
  clearUserInfo()
  authState.loggedIn = false
  authState.status = 'anonymous'
  authState.lastError = null
  return true
}

const applySessionResult = (requestToken, result) => {
  if (requestToken !== getToken()) return authResult(AuthResultStatus.STALE)

  if (result.status === AuthResultStatus.AUTHENTICATED) {
    setUserInfo(result.user)
    authState.loggedIn = true
    authState.status = 'authenticated'
    authState.lastError = null
  } else if (result.status === AuthResultStatus.INVALID) {
    clearToken(requestToken)
  } else if (result.status === AuthResultStatus.UNAVAILABLE) {
    authState.loggedIn = true
    authState.status = 'unavailable'
    authState.lastError = result.message
  }

  return result
}

const requestCurrentUser = async (token) => {
  const config = useRuntimeConfig()
  const response = await fetch(`${config.public.apiBaseUrl}/api/users/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })

  if (response.ok) {
    return authResult(AuthResultStatus.AUTHENTICATED, { user: await response.json() })
  }

  const data = await readResponseData(response)
  if (shouldInvalidateToken({
    requestToken: token,
    currentToken: token,
    status: response.status,
    error: data?.error,
  })) {
    return authResult(AuthResultStatus.INVALID, { message: data.error })
  }

  return unavailableResult(toUserFacingError(data, `Account request failed (${response.status}).`))
}

export async function loadCurrentUser(requestToken = getToken()) {
  if (!requestToken) {
    clearUserInfo()
    authState.loggedIn = false
    authState.status = 'anonymous'
    return authResult(AuthResultStatus.ANONYMOUS)
  }

  if (requestToken === getToken()) {
    authState.loggedIn = true
    authState.status = 'checking'
    authState.lastError = null
  }

  let result
  try {
    result = await singleFlight(`user:${requestToken}`, () => requestCurrentUser(requestToken))
  } catch (error) {
    result = unavailableResult(error?.message)
  }
  return applySessionResult(requestToken, result)
}

export async function fetchCurrentUser() {
  const result = await loadCurrentUser()
  return result.status === AuthResultStatus.AUTHENTICATED ? result.user : null
}

export async function setToken(token) {
  if (!import.meta.client || !token) return authResult(AuthResultStatus.ANONYMOUS)

  localStorage.setItem(TOKEN_KEY, token)
  clearUserInfo()
  authState.loggedIn = true
  authState.status = 'checking'
  authState.lastError = null
  return loadCurrentUser(token)
}

export function isLogin() {
  return authState.loggedIn
}

const requestTokenCheck = async (token) => {
  const config = useRuntimeConfig()
  const response = await fetch(`${config.public.apiBaseUrl}/api/auth/check`, {
    headers: { Authorization: `Bearer ${token}` },
  })

  if (response.ok) return authResult(AuthResultStatus.AUTHENTICATED)

  const data = await readResponseData(response)
  if (shouldInvalidateToken({
    requestToken: token,
    currentToken: token,
    status: response.status,
    error: data?.error,
  })) {
    return authResult(AuthResultStatus.INVALID, { message: data.error })
  }

  return unavailableResult(toUserFacingError(data, `Session check failed (${response.status}).`))
}

export async function checkToken() {
  const requestToken = getToken()
  if (!requestToken) return authResult(AuthResultStatus.ANONYMOUS)

  let result
  try {
    result = await singleFlight(`check:${requestToken}`, () => requestTokenCheck(requestToken))
  } catch (error) {
    result = unavailableResult(error?.message)
  }

  if (requestToken !== getToken()) return authResult(AuthResultStatus.STALE)
  if (result.status === AuthResultStatus.INVALID) {
    clearToken(requestToken)
    return result
  }
  if (result.status === AuthResultStatus.UNAVAILABLE) {
    return applySessionResult(requestToken, result)
  }
  return loadCurrentUser(requestToken)
}
