<template>
  <div class="forgot-page">
    <main class="forgot-content" aria-labelledby="forgot-title">
      <header class="forgot-header">
        <span>ACCOUNT RECOVERY</span>
        <h1 id="forgot-title">Reset your password</h1>
        <p>{{ stepDescription }}</p>
      </header>

      <div v-if="step === 0" class="step-content">
        <BaseInput icon="mail" v-model="email" placeholder="Email address" />
        <div v-if="emailError" class="error-message">{{ emailError }}</div>
        <button class="primary-button" type="button" :disabled="isSending" @click="sendCode">{{ isSending ? 'Sending…' : 'Send verification code' }}</button>
      </div>
      <div v-else-if="step === 1" class="step-content">
        <BaseInput icon="mail" v-model="code" placeholder="Verification code" />
        <button class="primary-button" type="button" :disabled="isVerifying" @click="verifyCode">{{ isVerifying ? 'Verifying…' : 'Verify code' }}</button>
      </div>
      <div v-else class="step-content">
        <BaseInput icon="lock" v-model="password" type="password" placeholder="New password" />
        <div v-if="passwordError" class="error-message">{{ passwordError }}</div>
        <button class="primary-button" type="button" :disabled="isResetting" @click="resetPassword">{{ isResetting ? 'Saving…' : 'Reset password' }}</button>
      </div>
      <div class="hint-message">
        <info-icon />
        Accounts created with Google can be recovered using the same email address.
      </div>
      <NuxtLink class="back-link" to="/login">Return to sign in</NuxtLink>
    </main>
  </div>
</template>

<script setup>
import { toast } from '~/main'
import BaseInput from '~/components/BaseInput.vue'
import { useRoute } from 'vue-router'

const config = useRuntimeConfig()
const API_BASE_URL = config.public.apiBaseUrl

const step = ref(0)
const email = ref('')
const code = ref('')
const password = ref('')
const token = ref('')
const emailError = ref('')
const passwordError = ref('')
const isSending = ref(false)
const isVerifying = ref(false)
const isResetting = ref(false)
const route = useRoute()
const stepDescription = computed(() => [
  'Enter the email address associated with your OpenIsle account.',
  `Enter the verification code sent to ${email.value || 'your email address'}.`,
  'Choose a new password for your account.',
][step.value])

onMounted(() => {
  if (route.query.email) {
    email.value = decodeURIComponent(route.query.email)
  }
})
const sendCode = async () => {
  if (!email.value) {
    emailError.value = 'Email address is required.'
    return
  }
  try {
    isSending.value = true
    const res = await fetch(`${API_BASE_URL}/api/auth/forgot/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.value }),
    })
    isSending.value = false
    if (res.ok) {
      toast.success('A verification code has been sent to your email.')
      step.value = 1
    } else {
      toast.error('Enter an email address registered with OpenIsle.')
    }
  } catch (e) {
    isSending.value = false
    toast.error('The verification code could not be sent.')
  }
}
const verifyCode = async () => {
  try {
    isVerifying.value = true
    const res = await fetch(`${API_BASE_URL}/api/auth/forgot/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.value, code: code.value }),
    })
    isVerifying.value = false
    const data = await res.json()
    if (res.ok) {
      token.value = data.token
      step.value = 2
    } else {
      toast.error(data.error || 'The verification code is invalid or expired.')
    }
  } catch (e) {
    isVerifying.value = false
    toast.error('The verification code could not be verified.')
  }
}
const resetPassword = async () => {
  if (!password.value) {
    passwordError.value = 'A new password is required.'
    return
  }
  try {
    isResetting.value = true
    const res = await fetch(`${API_BASE_URL}/api/auth/forgot/reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: token.value, password: password.value }),
    })
    isResetting.value = false
    const data = await res.json()
    if (res.ok) {
      toast.success('Your password has been reset.')
      navigateTo('/login', { replace: true })
    } else if (data.field === 'password') {
      passwordError.value = data.error
    } else {
      toast.error(data.error || 'The password could not be reset.')
    }
  } catch (e) {
    isResetting.value = false
    toast.error('The password could not be reset.')
  }
}
</script>

<style scoped>
.forgot-page {
  min-height: 640px;
  display: grid;
  place-items: center;
  padding: 52px 20px 72px;
  background: #f4f6f6;
}
.forgot-content {
  width: min(500px, 100%);
  display: grid;
  gap: 20px;
  padding: 38px 42px;
  border: 1px solid #bdcbd0;
  border-top: 5px solid #009edb;
  background: #fff;
}
.forgot-header span { color: #176582; font-size: 12px; font-weight: 800; letter-spacing: .1em; }
.forgot-header h1 { margin: 8px 0 9px; color: #24343d; font-family: Georgia, 'Times New Roman', serif; font-size: 34px; font-weight: 400; }
.forgot-header p { margin: 0; color: #5d6d75; font-size: 14px; line-height: 1.6; }

.forgot-content .hint-message {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  font-size: 13px;
  color: var(--blockquote-text-color);
}

.hint-message i {
  color: var(--primary-color);
  font-size: 14px;
}
.step-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.primary-button {
  border: 0;
  background: #0065a8;
  color: white;
  padding: 10px 20px;
  min-height: 46px;
  border-radius: 0;
  font-size: 14px;
  font-weight: 750;
  text-align: center;
  cursor: pointer;
}
.primary-button:hover {
  background-color: var(--primary-color-hover);
}
.primary-button:disabled { background: #8a9aa2; cursor: wait; }
.error-message {
  color: #a3312d;
  font-size: 13px;
}
.back-link { color: #176582; font-size: 13px; font-weight: 700; }
@media (max-width: 768px) {
  .forgot-page { padding: 28px 14px 50px; }
  .forgot-content { padding: 30px 24px; }
}
</style>
