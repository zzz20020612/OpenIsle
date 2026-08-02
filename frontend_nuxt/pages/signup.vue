<template>
  <div class="signup-page">
    <div class="signup-page-content">
      <div class="signup-page-header">
        <div class="signup-page-header-title">Welcome :)</div>
      </div>

      <div v-if="emailStep === 0" class="email-signup-page-content">
        <BaseInput icon="mail" v-model="email" @input="emailError = ''" placeholder="邮箱" />
        <div v-if="emailError" class="error-message">{{ emailError }}</div>

        <BaseInput
          icon="user-icon"
          v-model="username"
          @input="usernameError = ''"
          placeholder="用户名"
        />
        <div v-if="usernameError" class="error-message">{{ usernameError }}</div>

        <BaseInput
          icon="lock"
          v-model="password"
          @input="passwordError = ''"
          type="password"
          placeholder="密码"
        />
        <div v-if="passwordError" class="error-message">{{ passwordError }}</div>

        <div
          v-if="!isWaitingForEmailSent"
          class="signup-page-button-primary"
          @click="sendVerification"
        >
          <div class="signup-page-button-text">验证并注册</div>
        </div>
        <div v-else class="signup-page-button-primary disabled">
          <div class="signup-page-button-text">
            <loading-four class="loading-icon" />
            发送中...
          </div>
        </div>

        <div class="signup-page-button-secondary">
          已经有账号？ <a class="signup-page-button-secondary-link" href="/login">登录</a>
        </div>
      </div>

      <div v-if="emailStep === 1" class="email-signup-page-content">
        <BaseInput icon="mail" v-model="code" placeholder="邮箱验证码" />
        <div
          v-if="!isWaitingForEmailVerified"
          class="signup-page-button-primary"
          @click="verifyCode"
        >
          <div class="signup-page-button-text">注册</div>
        </div>
        <div v-else class="signup-page-button-primary disabled">
          <div class="signup-page-button-text">
            <loading-four class="loading-icon" />
            验证中...
          </div>
        </div>
      </div>
    </div>

    <ThirdPartyAuth mode="signup" :invite-token="inviteToken" />
  </div>
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
    emailError.value = '邮箱格式不正确'
  }
  if (!password.value || password.value.length < 6) {
    passwordError.value = '密码至少6位'
  }
  if (!username.value) {
    usernameError.value = '用户名不能为空'
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
      toast.success('验证码已发送，请查看邮箱')
    } else if (data.field) {
      if (data.field === 'username') usernameError.value = data.error
      if (data.field === 'email') emailError.value = data.error
      if (data.field === 'password') passwordError.value = data.error
    } else {
      const msg = data.error || data.message || res.statusText || '发送失败'
      const reason = data.reason_code ? ` (${data.reason_code})` : ''
      toast.error(`${res.status} ${msg}${reason}`)
    }
  } catch (e) {
    toast.error(`发送失败: ${e.message}`)
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
        toast.success('注册成功')
        await setToken(data.token)
        await navigateTo('/', { replace: true })
      } else if (data.reason_code === 'VERIFIED') {
        if (registerMode.value === 'WHITELIST') {
          navigateTo(`/signup-reason?token=${data.token}`, { replace: true })
        } else {
          toast.success('注册成功，请登录')
          navigateTo('/login', { replace: true })
        }
      }
    } else {
      toast.error(data.error || '注册失败')
    }
  } catch (e) {
    toast.error('注册失败')
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
