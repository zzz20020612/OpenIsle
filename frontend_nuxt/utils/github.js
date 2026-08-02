import { toast } from '../main'
import { setToken } from './auth'
import { registerPush } from './push'

export function githubAuthorize(inviteToken = '') {
  const config = useRuntimeConfig()
  const WEBSITE_BASE_URL = config.public.websiteBaseUrl
  const GITHUB_CLIENT_ID = config.public.githubClientId
  if (!GITHUB_CLIENT_ID) {
    toast.error('GitHub 登录不可用')
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
