import { toast } from '../main'
import { setToken } from './auth'
import { registerPush } from './push'

function generateCodeVerifier() {
  const array = new Uint8Array(32)
  window.crypto.getRandomValues(array)
  return Array.from(array)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

async function generateCodeChallenge(codeVerifier) {
  const encoder = new TextEncoder()
  const data = encoder.encode(codeVerifier)
  const digest = await window.crypto.subtle.digest('SHA-256', data)
  return btoa(String.fromCharCode(...new Uint8Array(digest)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
}

// 邀请码明文放入 state；同时生成 csrf 放入 state 并在回调校验
export async function twitterAuthorize(inviteToken = '') {
  const config = useRuntimeConfig()
  const WEBSITE_BASE_URL = config.public.websiteBaseUrl
  const TWITTER_CLIENT_ID = config.public.twitterClientId
  if (!TWITTER_CLIENT_ID) {
    toast.error('X sign-in is unavailable.')
    return
  }

  const redirectUri = `${WEBSITE_BASE_URL}/twitter-callback`

  // PKCE
  const codeVerifier = generateCodeVerifier()
  sessionStorage.setItem('twitter_code_verifier', codeVerifier)
  const codeChallenge = await generateCodeChallenge(codeVerifier)

  // CSRF + 邀请码一起放入 state
  const csrf = Math.random().toString(36).slice(2)
  sessionStorage.setItem('twitter_csrf_state', csrf)
  const state = new URLSearchParams({
    csrf,
    invite_token: inviteToken || '',
  }).toString()

  const url =
    `https://x.com/i/oauth2/authorize?response_type=code&client_id=${encodeURIComponent(TWITTER_CLIENT_ID)}` +
    `&redirect_uri=${encodeURIComponent(redirectUri)}` +
    `&scope=${encodeURIComponent('tweet.read users.read')}` +
    `&state=${encodeURIComponent(state)}` +
    `&code_challenge=${encodeURIComponent(codeChallenge)}` +
    `&code_challenge_method=S256`

  window.location.href = url
}

export async function twitterExchange(code, state, reason) {
  try {
    const config = useRuntimeConfig()
    const API_BASE_URL = config.public.apiBaseUrl

    // 取出并清理 PKCE/CSRF
    const codeVerifier = sessionStorage.getItem('twitter_code_verifier')
    sessionStorage.removeItem('twitter_code_verifier')

    const savedCsrf = sessionStorage.getItem('twitter_csrf_state')
    sessionStorage.removeItem('twitter_csrf_state')

    // 从 state 解析 csrf 与 invite_token
    let parsedCsrf = ''
    let inviteToken = ''
    try {
      const sp = new URLSearchParams(state || '')
      parsedCsrf = sp.get('csrf') || ''
      inviteToken = sp.get('invite_token') || sp.get('invitetoken') || ''
    } catch {}

    // 简单 CSRF 校验（存在才校验，避免误杀老会话）
    if (savedCsrf && parsedCsrf && savedCsrf !== parsedCsrf) {
      toast.error('The sign-in session could not be verified. Please try again.')
      return { success: false, needReason: false, error: 'state mismatch' }
    }

    const res = await fetch(`${API_BASE_URL}/api/auth/twitter`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code,
        redirectUri: `${window.location.origin}/twitter-callback`,
        reason,
        state,
        codeVerifier,
        inviteToken,
      }),
    })

    const data = await res.json()
    if (res.ok && data.token) {
      await setToken(data.token)
      toast.success('Logged in successfully.')
      registerPush()
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
