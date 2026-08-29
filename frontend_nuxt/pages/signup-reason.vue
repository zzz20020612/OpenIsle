<template>
  <div class="reason-page">
    <main class="reason-content" aria-labelledby="reason-title">
      <p class="reason-eyebrow">ACCOUNT APPLICATION</p>
      <h1 id="reason-title" class="reason-title">Tell us about your research interests</h1>
      <p class="reason-description">
        OpenIsle reviews new account requests to protect the integrity of scholarly discussion.
        Briefly describe your research background and how you plan to use the platform.
      </p>
      <div class="input-wrapper">
        <div class="reason-input-container">
          <BaseInput
            textarea
            rows="4"
            v-model="reason"
            placeholder="Research area, affiliation or intended use (at least 20 characters)"
          ></BaseInput>
          <div class="char-count">{{ reason.length }}/20</div>
        </div>
        <div v-if="error" class="error-message">{{ error }}</div>
      </div>
      <button class="signup-page-button-primary" type="button" :disabled="isWaitingForRegister" @click="submit">
        {{ isWaitingForRegister ? 'Submitting application…' : 'Submit application' }}
      </button>
      <p class="reason-note">Applications are reviewed by the OpenIsle administration team.</p>
    </main>
  </div>
</template>

<script setup>
import BaseInput from '~/components/BaseInput.vue'
import { toast } from '~/main'
const config = useRuntimeConfig()
const API_BASE_URL = config.public.apiBaseUrl

const reason = ref('')
const error = ref('')
const isWaitingForRegister = ref(false)
const token = ref('')
const route = useRoute()

onMounted(async () => {
  token.value = route.query.token || ''
  if (!token.value) {
    await navigateTo({ path: '/signup' }, { replace: true })
  }
})

const submit = async () => {
  const trimmedReason = reason.value.trim()
  if (!trimmedReason || trimmedReason.length < 20) {
    error.value = 'Please enter at least 20 characters.'
    return
  }

  try {
    isWaitingForRegister.value = true
    const res = await fetch(`${API_BASE_URL}/api/auth/reason`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        token: token.value,
        reason: reason.value,
      }),
    })
    isWaitingForRegister.value = false
    const data = await res.json()
    if (res.ok) {
      toast.success('Your account application has been submitted for review.')
      await navigateTo('/', { replace: true })
    } else if (data.reason_code === 'INVALID_CREDENTIALS') {
      toast.error('This sign-up session has expired. Please sign in again.')
      await navigateTo('/login', { replace: true })
    } else {
      toast.error(data.error || 'The application could not be submitted.')
    }
  } catch (e) {
    isWaitingForRegister.value = false
    toast.error('The application could not be submitted.')
  }
}
</script>

<style scoped>
.reason-page {
  min-height: 680px;
  display: grid;
  place-items: center;
  padding: 64px 20px;
  background: #f4f6f6;
}

.reason-title {
  margin: 0;
  color: #24343d;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: clamp(30px, 4vw, 42px);
  font-weight: 400;
  line-height: 1.15;
}

.reason-description {
  margin: 0;
  color: #53636b;
  font-size: 15px;
  line-height: 1.7;
}

.reason-content {
  width: min(620px, 100%);
  display: grid;
  gap: 20px;
  padding: 42px 46px;
  border: 1px solid #cbd5d9;
  border-top: 5px solid #009edb;
  background: #fff;
  box-shadow: 0 14px 36px rgba(31, 57, 69, .09);
}
.reason-eyebrow { margin: 0 0 -8px; color: #176582; font-size: 12px; font-weight: 800; letter-spacing: .1em; }

.input-wrapper {
  display: flex;
  flex-direction: column;
}

.reason-input-container {
  position: relative;
}

.char-count {
  position: absolute;
  bottom: 8px;
  right: 12px;
  font-size: 12px;
  color: #888;
  background-color: transparent;
  pointer-events: none;
}

.error-message {
  color: #a3312d;
  font-size: 13px;
  margin-top: 8px;
}

.signup-page-button-primary {
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

.signup-page-button-primary:hover {
  background-color: var(--primary-color-hover);
}

.signup-page-button-primary:disabled {
  background: #8a9aa2;
  cursor: wait;
}
.reason-note { margin: -4px 0 0; color: #68777e; font-size: 12px; text-align: center; }

@media (max-width: 768px) {
  .reason-page { padding: 28px 14px; }
  .reason-content { padding: 30px 24px; }
}
</style>
