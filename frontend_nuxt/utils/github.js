import { toast } from '../main'
import { setToken } from './auth'
import { registerPush } from './push'

export function githubAuthorize(inviteToken = '') {
  const config = useRuntimeConfig()
  const WEBSITE_BASE_URL = config.public.websiteBaseUrl
  const GITHUB_CLIENT_ID = config.public.githubClientId
  if (!GITHUB_CLIENT_ID) {
    toast.error('GitHub sign-in is unavailable.')
    return
  }

  const redirectUri = `${WEBSITE_BASE_URL}/github-callback`
  const state = new URLSearchParams({ invite_token: inviteToken }).toString()

  const url =
    `https://github.com/login/oauth/authorize` +
    `?client_id=${encodeURIComponent(GITHUB_CLIENT_ID)}` +
    `&redirect_uri=${encodeURIComponent(redirectUri)}` +
    `&scope=${encodeURIComponent('user:email')}` +
    `&state=${encodeURIComponent(state)}`

  window.location.href = url
}

export async function githubExchange(code, inviteToken = '', reason = '') {
  try {
    const config = useRuntimeConfig()
    const API_BASE_URL = config.public.apiBaseUrl

    const payload = {
      code,
      redirectUri: `${window.location.origin}/github-callback`,
      reason,
    }
    if (inviteToken) payload.inviteToken = inviteToken

    const res = await fetch(`${API_BASE_URL}/api/auth/github`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const data = await res.json()

    if (res.ok && data.token) {
      await setToken(data.token)
      toast.success('Logged in successfully.')
      registerPush?.()
      return { success: true, needReason: false }
    } else if (data.reason_code === 'NOT_APPROVED') {
      toast.info('Registration review is enabled. Please provide a reason for joining.')
      return { success: false, needReason: true, token: data.token }
    } else if (data.reason_code === 'IS_APPROVING') {
      toast.info('Your registration request is under review.')
      return { success: true, needReason: false }
    } else {
      toast.error(data.error || 'Sign-in failed.')
      return { success: false, needReason: false, error: data.error || 'Sign-in failed.' }
    }
  } catch (e) {
    console.error(e)
    toast.error('Sign-in failed.')
    return { success: false, needReason: false, error: 'Sign-in failed.' }
  }
}
