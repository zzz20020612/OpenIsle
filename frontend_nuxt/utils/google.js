import { toast } from '../main'
import { setToken } from './auth'
import { registerPush } from './push'

export async function googleGetIdToken() {
  const config = useRuntimeConfig()
  const GOOGLE_CLIENT_ID = config.public.googleClientId

  return new Promise((resolve, reject) => {
    if (!window.google || !GOOGLE_CLIENT_ID) {
      toast.error('Google sign-in is unavailable. Check your network connection.')
      reject()
      return
    }
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: ({ credential }) => resolve(credential),
      use_fedcm: true,
    })
    window.google.accounts.id.prompt()
  })
}

export function googleAuthorize(inviteToken = '') {
  const config = useRuntimeConfig()
  const GOOGLE_CLIENT_ID = config.public.googleClientId
  const WEBSITE_BASE_URL = config.public.websiteBaseUrl

  if (!GOOGLE_CLIENT_ID) {
    toast.error('Google sign-in is unavailable. Check your network connection.')
    return
  }

  const redirectUri = `${WEBSITE_BASE_URL}/google-callback`
  const nonce = Math.random().toString(36).slice(2)

  // 明文放在 state（推荐；Google 会原样回传）
  const state = new URLSearchParams({ invite_token: inviteToken }).toString()

  const url =
    `https://accounts.google.com/o/oauth2/v2/auth` +
    `?client_id=${encodeURIComponent(GOOGLE_CLIENT_ID)}` +
    `&redirect_uri=${encodeURIComponent(redirectUri)}` +
    `&response_type=id_token` +
    `&scope=${encodeURIComponent('openid email profile')}` +
    `&nonce=${encodeURIComponent(nonce)}` +
    `&state=${encodeURIComponent(state)}`

  window.location.href = url
}

export async function googleAuthWithToken(
  idToken,
  redirect_success,
  redirect_not_approved,
  options = {}, // { inviteToken?: string }
) {
  try {
    if (!idToken) {
      toast.error('Google did not return an identity token.')
      return
    }

    const config = useRuntimeConfig()
    const API_BASE_URL = config.public.apiBaseUrl

    const payload = { idToken }
    if (options && options.inviteToken) {
      payload.inviteToken = options.inviteToken
    }

    const res = await fetch(`${API_BASE_URL}/api/auth/google`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    })

    const data = await res.json().catch(() => ({}))

    if (res.ok && data && data.token) {
      await setToken(data.token)
      toast.success('Logged in successfully.')
      registerPush?.()
      if (typeof redirect_success === 'function') redirect_success()
      return
    }

    if (data && data.reason_code === 'NOT_APPROVED') {
      toast.info('Registration review is enabled. Please provide a reason for joining.')
      if (typeof redirect_not_approved === 'function') redirect_not_approved(data.token)
      return
    }

    if (data && data.reason_code === 'IS_APPROVING') {
      toast.info('Your registration request is under review.')
      if (typeof redirect_success === 'function') redirect_success()
      return
    }
    toast.error(data?.message || 'Sign-in failed.')
  } catch (e) {
    console.error(e)
    toast.error('Sign-in failed.')
  }
}

export async function googleSignIn(redirect_success, redirect_not_approved) {
  try {
    const token = await googleGetIdToken()
    await googleAuthWithToken(token, redirect_success, redirect_not_approved)
  } catch {
    /* ignore */
  }
}

export function loginWithGoogle() {
  googleSignIn(
    () => {
      navigateTo('/', { replace: true })
    },
    (token) => {
      navigateTo(`/signup-reason?token=${token}`, { replace: true })
    },
  )
}
