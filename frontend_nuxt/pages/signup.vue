<template>
  <main class="signup-page">
    <section class="signup-page-content" aria-labelledby="signup-title">
      <header class="signup-page-header">
        <span>OpenIsle account</span>
        <h1 id="signup-title">Create a research account</h1>
        <p>Register once to submit manuscripts, access literature PDFs, and participate in evaluation.</p>
      </header>

      <div v-if="emailStep === 0" class="email-signup-page-content">
        <BaseInput icon="mail" v-model="email" @input="emailError = ''" placeholder="Email address" />
        <div v-if="emailError" class="error-message">{{ emailError }}</div>

        <BaseInput
          icon="user-icon"
          v-model="username"
          @input="usernameError = ''"
          placeholder="Username"
        />
        <div v-if="usernameError" class="error-message">{{ usernameError }}</div>

        <BaseInput
          icon="lock"
          v-model="password"
          @input="passwordError = ''"
          type="password"
          placeholder="Password"
        />
        <div v-if="passwordError" class="error-message">{{ passwordError }}</div>

        <button
          v-if="!isWaitingForEmailSent"
          class="signup-page-button-primary"
          type="button"
          @click="sendVerification"
        >
          <span class="signup-page-button-text">Verify and register</span>
        </button>
        <button v-else class="signup-page-button-primary disabled" type="button" disabled>
          <div class="signup-page-button-text">
            <loading-four class="loading-icon" />
            Sending…
          </div>
        </button>

        <div class="signup-page-button-secondary">
          Already registered? <NuxtLink class="signup-page-button-secondary-link" to="/login">Sign in</NuxtLink>
        </div>
      </div>

      <div v-if="emailStep === 1" class="email-signup-page-content">
        <BaseInput icon="mail" v-model="code" placeholder="Email verification code" />
        <button
          v-if="!isWaitingForEmailVerified"
          class="signup-page-button-primary"
          type="button"
          @click="verifyCode"
        >
          <span class="signup-page-button-text">Complete registration</span>
        </button>
        <button v-else class="signup-page-button-primary disabled" type="button" disabled>
          <div class="signup-page-button-text">
            <loading-four class="loading-icon" />
            Verifying…
          </div>
        </button>
      </div>
      <div class="signup-divider"><span>or continue with</span></div>
      <ThirdPartyAuth mode="signup" :invite-token="inviteToken" />
    </section>

  </main>
</template>

<script setup>
import BaseInput from '~/components/BaseInput.vue'
import { toast } from '~/main'
import { setToken } from '~/utils/auth'
import ThirdPartyAuth from '~/components/ThirdPartyAuth.vue'

const route = useRoute()
const config = useRuntimeConfig()
const API_BASE_URL = config.public.apiBaseUrl
const emailStep = ref(0)
const email = ref('')
const username = ref('')
const password = ref('')
const registerMode = ref('DIRECT')
const emailError = ref('')
const usernameError = ref('')
const passwordError = ref('')
const code = ref('')
const isWaitingForEmailSent = ref(false)
const isWaitingForEmailVerified = ref(false)
const inviteToken = ref('')

onMounted(async () => {
  username.value = route.query.u || ''
  inviteToken.value = route.query.invite_token || ''
  try {
    const res = await fetch(`${API_BASE_URL}/api/config`)
    if (res.ok) {
      const data = await res.json()
      registerMode.value = data.registerMode
    }
  } catch {
    /* ignore */
  }
  if (route.query.verify) {
    emailStep.value = 1
  }
})

const clearErrors = () => {
  emailError.value = ''
  usernameError.value = ''
  passwordError.value = ''
}

const sendVerification = async () => {
  clearErrors()
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(email.value)) {
    emailError.value = 'Enter a valid email address.'
  }
  if (!password.value || password.value.length < 6) {
    passwordError.value = 'Password must contain at least 6 characters.'
  }
  if (!username.value) {
    usernameError.value = 'Username is required.'
  }
  if (emailError.value || passwordError.value || usernameError.value) {
    return
  }
  try {
    isWaitingForEmailSent.value = true
    const res = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: username.value,
        email: email.value,
        password: password.value,
        inviteToken: inviteToken.value,
      }),
    })
    const data = await res.json().catch(() => ({}))
    if (res.ok) {
      emailStep.value = 1
      toast.success('A verification code has been sent to your email.')
    } else if (data.field) {
      if (data.field === 'username') usernameError.value = data.error
      if (data.field === 'email') emailError.value = data.error
      if (data.field === 'password') passwordError.value = data.error
    } else {
      const msg = data.error || data.message || res.statusText || 'The verification email could not be sent.'
      const reason = data.reason_code ? ` (${data.reason_code})` : ''
      toast.error(`${res.status} ${msg}${reason}`)
    }
  } catch (e) {
    toast.error(`The verification email could not be sent: ${e.message}`)
  } finally {
    isWaitingForEmailSent.value = false
  }
}

const verifyCode = async () => {
  try {
    isWaitingForEmailVerified.value = true
    const res = await fetch(`${API_BASE_URL}/api/auth/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code: code.value,
        username: username.value,
      }),
    })
    const data = await res.json()
    if (res.ok) {
      if (data.reason_code === 'VERIFIED_AND_APPROVED') {
        toast.success('Your OpenIsle account is ready.')
        await setToken(data.token)
        await navigateTo('/', { replace: true })
      } else if (data.reason_code === 'VERIFIED') {
        if (registerMode.value === 'WHITELIST') {
          navigateTo(`/signup-reason?token=${data.token}`, { replace: true })
        } else {
          toast.success('Registration complete. Please sign in.')
          navigateTo('/login', { replace: true })
        }
      }
    } else {
      toast.error(data.error || 'Registration could not be completed.')
    }
  } catch (e) {
    toast.error('Registration could not be completed.')
  } finally {
    isWaitingForEmailVerified.value = false
  }
}
</script>

<style scoped>
.signup-page {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  height: 100%;
  width: 100%;
  background-color: var(--background-color);
}

.signup-page-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: calc(40% - 120px);
  border-right: 1px solid var(--normal-border-color);
  padding-right: 120px;
}

.signup-page-header-title {
  font-family: 'Pacifico', 'Comic Sans MS', cursive, 'Roboto', sans-serif;
  font-size: 42px;
  font-weight: bold;
  width: 100%;
  opacity: 0.75;
}

.signup-page-header {
  font-size: 42px;
  font-weight: bold;
  width: 100%;
}

.email-signup-page-content {
  margin-top: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  gap: 20px;
}

.signup-page-input {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  width: calc(100% - 40px);
  padding: 15px 20px;
  border-radius: 10px;
  border: 1px solid var(--normal-border-color);
  gap: 10px;
  margin-bottom: 20px;
}

.signup-page-input-icon {
  opacity: 0.5;
  font-size: 16px;
}

.signup-page-input-text {
  border: none;
  outline: none;
  width: 100%;
  font-size: 16px;
}

.signup-page-button-primary {
  margin-top: 20px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  width: calc(100% - 40px);
  background-color: var(--primary-color);
  color: white;
  padding: 10px 20px;
  border-radius: 10px;
  cursor: pointer;
  gap: 10px;
}

.signup-page-button-primary.disabled {
  background-color: var(--primary-color-disabled);
  opacity: 0.5;
  cursor: not-allowed;
}

.signup-page-button-primary.disabled:hover {
  background-color: var(--primary-color-disabled);
}

.signup-page-button-primary:hover {
  background-color: var(--primary-color-hover);
}

.signup-page-button-text {
  font-size: 16px;
}

.signup-page-button-secondary {
  margin-top: 20px;
  font-size: 16px;
  opacity: 0.7;
}

.signup-page-button-secondary-link {
  color: var(--primary-color);
}

.error-message {
  color: red;
  font-size: 14px;
  width: calc(100% - 40px);
  margin-top: -10px;
  margin-bottom: 10px;
}

@media (max-width: 768px) {
  .signup-page {
    flex-direction: column;
    justify-content: flex-start;
  }

  .email-signup-page-content {
    margin-top: 20px;
    gap: 20px;
  }

  .signup-page-content {
    margin-top: 20px;
    width: calc(100% - 40px);
    border-right: none;
    padding-left: 20px;
    padding-right: 20px;
  }

  .signup-page-button-primary {
    margin-top: 0px;
  }

  .signup-page-button-secondary {
    margin-top: 0px;
    font-size: 13px;
  }
}
</style>

<style scoped>
.signup-page{min-height:600px;height:auto;padding:48px 20px 72px;color:#222;background:#f4f4f4}.signup-page-content{display:block;width:min(480px,100%);padding:38px 42px;border:1px solid #bbb;border-top:5px solid #0065a8;background:#fff}.signup-page-header{font-size:inherit}.signup-page-header>span{color:#0065a8;font-size:12px;font-weight:800;letter-spacing:.09em;text-transform:uppercase}.signup-page-header h1{margin:9px 0 0;font-family:Georgia,'Times New Roman',serif;font-size:32px;font-weight:400;line-height:1.2}.signup-page-header p{margin:11px 0 0;color:#595959;font-size:14px;line-height:1.6}.email-signup-page-content{align-items:stretch;margin-top:28px;gap:17px}.email-signup-page-content :deep(.base-input){width:100%;min-height:46px;box-sizing:border-box;border-radius:0}.signup-page-button-primary{box-sizing:border-box;width:100%;min-height:46px;margin-top:4px;padding:10px 18px;border:1px solid #0065a8;border-radius:0;background:#0065a8;font-weight:700}.signup-page-button-primary:hover{background:#004f85}.signup-page-button-secondary{margin-top:2px;color:#595959;font-size:13px}.error-message{width:100%;margin:-10px 0 0;color:#a51e22;font-size:13px}.signup-divider{display:flex;align-items:center;gap:12px;margin:27px 0 17px;color:#666;font-size:11px;letter-spacing:.05em;text-transform:uppercase}.signup-divider:before,.signup-divider:after{height:1px;flex:1;background:#ccc;content:''}.signup-page-content :deep(.third-party-auth){width:100%;margin:0}@media(max-width:600px){.signup-page{padding:24px 12px 50px}.signup-page-content{width:100%;margin:0;padding:28px 22px}.signup-page-header h1{font-size:28px}}
</style>
