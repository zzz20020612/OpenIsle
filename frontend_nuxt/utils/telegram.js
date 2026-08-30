import { toast } from '../main'
import { setToken } from './auth'
import { registerPush } from './push'

export function telegramAuthorize(inviteToken = '') {
  const config = useRuntimeConfig()
  const WEBSITE_BASE_URL = config.public.websiteBaseUrl
  const TELEGRAM_BOT_ID = config.public.telegramBotId
  if (!TELEGRAM_BOT_ID) {
    toast.error('Telegram sign-in is unavailable.')
    return
  }
  const redirectUri = `${WEBSITE_BASE_URL}/telegram-callback${inviteToken ? `?invite_token=${encodeURIComponent(inviteToken)}` : ''}`
  const url =
    `https://oauth.telegram.org/auth` +
    `?bot_id=${encodeURIComponent(TELEGRAM_BOT_ID)}` +
    `&origin=${encodeURIComponent(redirectUri)}` +
    `&request_access=write`
  // `&redirect_uri=${encodeURIComponent(redirectUri)}`
  window.location.href = url
}

export async function telegramExchange(authData, inviteToken = '', reason = '') {
  try {
    const config = useRuntimeConfig()
    const API_BASE_URL = config.public.apiBaseUrl
    const payload = { ...authData, reason }
    if (inviteToken) payload.inviteToken = inviteToken
    const res = await fetch(`${API_BASE_URL}/api/auth/telegram`, {
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
