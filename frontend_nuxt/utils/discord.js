import { toast } from '../main'
import { setToken } from './auth'
import { registerPush } from './push'

export function discordAuthorize(inviteToken = '') {
  const config = useRuntimeConfig()
  const WEBSITE_BASE_URL = config.public.websiteBaseUrl
  const DISCORD_CLIENT_ID = config.public.discordClientId
  if (!DISCORD_CLIENT_ID) {
    toast.error('Discord 登录不可用')
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
      toast.info('当前为注册审核模式，请填写注册理由')
      return { success: false, needReason: true, token: data.token }
    } else if (data.reason_code === 'IS_APPROVING') {
      toast.info('您的注册理由正在审批中')
      return { success: true, needReason: false }
    } else {
      toast.error(data.error || '登录失败')
      return { success: false, needReason: false, error: data.error || '登录失败' }
    }
  } catch (e) {
    console.error(e)
    toast.error('登录失败')
    return { success: false, needReason: false, error: '登录失败' }
  }
}
