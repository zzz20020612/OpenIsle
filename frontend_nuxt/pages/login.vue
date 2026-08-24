<template>
  <main class="login-page">
    <section class="login-panel" aria-labelledby="login-title">
      <header class="login-heading">
        <span>Author account</span>
        <h1 id="login-title">Sign in to OpenIsle</h1>
        <p>Continue to your submissions, revisions, and research workspace.</p>
      </header>

      <form class="login-form" method="post" action="/login" @submit.prevent="submitLogin">
        <label class="login-field" for="login-username">
          <span>Email or username</span>
          <BaseInput
            id="login-username"
            v-model="username"
            icon="mail"
            name="username"
            autocomplete="username"
            placeholder="you@example.edu"
            :disabled="isWaitingForLogin"
            required
          />
        </label>

        <label class="login-field" for="login-password">
          <span>Password</span>
          <BaseInput
            id="login-password"
            v-model="password"
            icon="lock"
            type="password"
            name="password"
            autocomplete="current-password"
            placeholder="Enter your password"
            :disabled="isWaitingForLogin"
            required
          />
        </label>

        <p v-if="loginError" class="login-error" role="alert">{{ loginError }}</p>

        <button class="login-submit" type="submit" :disabled="isWaitingForLogin">
          <loading-four v-if="isWaitingForLogin" class="loading-icon" />
          {{ isWaitingForLogin ? 'Signing in...' : 'Sign in' }}
        </button>

        <button
          v-if="sessionUnavailable"
          class="login-retry"
          type="button"
          :disabled="isWaitingForLogin"
          @click="retryAccountConnection"
        >
          Retry account connection
        </button>
      </form>

      <div class="login-links">
        <NuxtLink to="/signup">Create an account</NuxtLink>
        <NuxtLink :to="`/forgot-password?email=${encodeURIComponent(username)}`">Reset password</NuxtLink>
      </div>

      <div class="login-divider"><span>or continue with</span></div>
      <ThirdPartyAuth mode="login" />
    </section>
  </main>
</template>

<script setup>
import { toast } from '~/main'
import { authState, loadCurrentUser, setToken } from '~/utils/auth'
import { AuthResultStatus } from '~/utils/authSessionCore'
import { toUserFacingError } from '~/utils/userFacingError'
import BaseInput from '~/components/BaseInput.vue'
import ThirdPartyAuth from '~/components/ThirdPartyAuth.vue'
import { registerPush } from '~/utils/push'

const config = useRuntimeConfig()
const route = useRoute()
const router = useRouter()
const API_BASE_URL = config.public.apiBaseUrl
const username = ref('')
const password = ref('')
const isWaitingForLogin = ref(false)
const loginError = ref('')
const sessionUnavailable = ref(false)
let redirecting = false

const loginRedirectPath = computed(() => {
  const redirect = Array.isArray(route.query.redirect)
    ? route.query.redirect[0]
    : route.query.redirect
  return typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//')
    ? redirect
    : '/papers'
})

const redirectAuthenticatedSession = async () => {
  if (redirecting || route.path !== '/login') return
  redirecting = true
  try {
    await router.replace(loginRedirectPath.value)
  } finally {
    redirecting = false
  }
}

watch(
  () => authState.status,
  (status) => {
    if (status === AuthResultStatus.AUTHENTICATED) void redirectAuthenticatedSession()
  },
  { immediate: true },
)

const finishLogin = async () => {
  sessionUnavailable.value = false
  loginError.value = ''
  toast.success('Logged in successfully.')
  await redirectAuthenticatedSession()
  void registerPush()
}

const handleSessionResult = async (result) => {
  if (result.status === AuthResultStatus.AUTHENTICATED) {
    await finishLogin()
    return true
  }
  if (result.status === AuthResultStatus.UNAVAILABLE) {
    sessionUnavailable.value = true
    loginError.value = 'Your credentials were accepted, but account details could not be loaded. Check the connection and retry.'
    return false
  }
  loginError.value = 'The new session could not be verified. Please sign in again.'
  return false
}

const retryAccountConnection = async () => {
  if (isWaitingForLogin.value) return
  isWaitingForLogin.value = true
  loginError.value = ''
  try {
    await handleSessionResult(await loadCurrentUser())
  } finally {
    isWaitingForLogin.value = false
  }
}

const submitLogin = async () => {
  if (isWaitingForLogin.value) return
  loginError.value = ''
  sessionUnavailable.value = false
  isWaitingForLogin.value = true

  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username.value.trim(), password: password.value }),
    })
    const data = await response.json().catch(() => ({}))

    if (response.ok && data.token) {
      await handleSessionResult(await setToken(data.token))
    } else if (data.reason_code === 'EMAIL_SEND_FAILED') {
      loginError.value = toUserFacingError(data, 'The verification email could not be sent.')
    } else if (data.reason_code === 'NOT_VERIFIED') {
      toast.info('This email is not verified. A new verification code has been sent.')
      await navigateTo(
        { path: '/signup', query: { verify: '1', u: username.value } },
        { replace: true },
      )
    } else if (data.reason_code === 'IS_APPROVING') {
      loginError.value = 'Your registration is still under review. Please check your email for updates.'
    } else if (data.reason_code === 'NOT_APPROVED') {
      await navigateTo({ path: '/signup-reason', query: { token: data.token } }, { replace: true })
    } else {
      loginError.value = toUserFacingError(data, 'The username or password was not accepted.')
    }
  } catch (error) {
    loginError.value = toUserFacingError(error, 'Unable to reach the sign-in service. Try again shortly.')
  } finally {
    isWaitingForLogin.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: calc(100vh - var(--header-height));
  display: grid;
  place-items: center;
  padding: 48px 20px 72px;
  background: #f1f4f3;
  color: #19272f;
}

.login-panel {
  width: min(460px, 100%);
  padding: 38px 42px;
  border: 1px solid #cbd5d8;
  border-top: 5px solid #0065a8;
  background: #fff;
}

.login-heading > span {
  color: #0065a8;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: .07em;
  text-transform: uppercase;
}

.login-heading h1 {
  margin: 9px 0 0;
  color: #17252d;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 32px;
  font-weight: 500;
  line-height: 1.2;
}

.login-heading p {
  margin: 11px 0 0;
  color: #627078;
  font-size: 14px;
  line-height: 1.55;
}

.login-form { display: grid; gap: 17px; margin-top: 28px; }
.login-field { display: grid; gap: 7px; }

.login-field > span {
  color: #35454e;
  font-size: 13px;
  font-weight: 750;
}

.login-field :deep(.base-input) {
  width: 100%;
  min-height: 46px;
  box-sizing: border-box;
  padding: 11px 13px;
  border-radius: 0;
  background: #fbfcfc;
}

.login-field :deep(.base-input-text) { font-size: 15px; }

.login-error {
  margin: 0;
  padding: 10px 12px;
  border-left: 3px solid #ad473e;
  background: #fff5f3;
  color: #8b352e;
  font-size: 13px;
  line-height: 1.45;
}

.login-submit,
.login-retry {
  min-height: 46px;
  border: 1px solid #0065a8;
  border-radius: 0;
  font: inherit;
  font-size: 14px;
  font-weight: 780;
  cursor: pointer;
}

.login-submit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 2px;
  background: #0065a8;
  color: #fff;
}

.login-submit:hover:not(:disabled) { background: #004f85; }
.login-submit:disabled, .login-retry:disabled { opacity: .58; cursor: wait; }
.login-retry { background: #fff; color: #245a72; }
.login-retry:hover:not(:disabled) { background: #edf4f6; }

.login-links {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  margin-top: 18px;
  font-size: 13px;
}

.login-links a { color: #285f77; text-decoration: none; }
.login-links a:hover { text-decoration: underline; }

.login-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 27px 0 17px;
  color: #738087;
  font-size: 11px;
  letter-spacing: .04em;
  text-transform: uppercase;
}

.login-divider::before,
.login-divider::after {
  height: 1px;
  flex: 1;
  background: #d7dfe1;
  content: '';
}

.login-panel :deep(.third-party-auth) { width: 100%; margin: 0; }

@media (max-width: 600px) {
  .login-page { align-items: start; padding: 24px 12px 50px; }
  .login-panel { padding: 28px 22px; }
  .login-heading h1 { font-size: 28px; }
}
</style>
