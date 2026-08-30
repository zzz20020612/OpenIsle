import { toast } from '../main'
import { setToken } from './auth'
import { registerPush } from './push'

export function discordAuthorize(inviteToken = '') {
  const config = useRuntimeConfig()
  const WEBSITE_BASE_URL = config.public.websiteBaseUrl
  const DISCORD_CLIENT_ID = config.public.discordClientId
  if (!DISCORD_CLIENT_ID) {
    toast.error('Discord sign-in is unavailable.')
    return
  }

  const redirectUri = `${WEBSITE_BASE_URL}/discord-callback`
  // 用 state 明文携带 invite_token（仅用于回传，不再透传给后端）
  const state = new URLSearchParams({ invite_token: inviteToken }).toString()

  const url =
    `https://discord.com/api/oauth2/authorize` +
    `?client_id=${encodeURIComponent(DISCORD_CLIENT_ID)}` +
    `&redirect_uri=${encodeURIComponent(redirectUri)}` +
    `&response_type=code` +
    `&scope=${encodeURIComponent('identify email')}` +
    `&state=${encodeURIComponent(state)}`

  window.location.href = url
}

export async function discordExchange(code, inviteToken = '', reason = '') {
  try {
    const config = useRuntimeConfig()
    const API_BASE_URL = config.public.apiBaseUrl

    const payload = {
      code,
      redirectUri: `${window.location.origin}/discord-callback`,
      reason,
    }
    if (inviteToken) payload.inviteToken = inviteToken // 明文传给后端

    const res = await fetch(`${API_BASE_URL}/api/auth/discord`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
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
