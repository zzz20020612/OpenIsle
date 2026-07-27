<template>
  <div class="login-page">
    <div class="login-page-content">
      <div class="login-page-header">
        <div class="login-page-header-title">Welcome :)</div>
      </div>

      <div class="email-login-page-content">
        <BaseInput icon="mail" v-model="username" placeholder="邮箱/用户名" />

        <BaseInput icon="lock" v-model="password" type="password" placeholder="密码" />

        <div v-if="!isWaitingForLogin" class="login-page-button-primary" @click="submitLogin">
          <div class="login-page-button-text">登录</div>
        </div>

        <div v-else class="login-page-button-primary disabled">
          <div class="login-page-button-text">
            <loading-four class="loading-icon" />
            登录中...
          </div>
        </div>

        <div class="login-page-button-secondary">
          没有账号？ <a class="login-page-button-secondary-link" href="/signup">注册</a> |
          <a class="login-page-button-secondary-link" :href="`/forgot-password?email=${username}`"
            >找回密码</a
          >
        </div>
        <div class="hint-message">
          <info-icon />
          使用右侧第三方OAuth注册/登录的用户可使用对应的邮箱进行重设密码
        </div>
      </div>
    </div>

    <ThirdPartyAuth mode="login" />
  </div>
</template>

<script setup>
import { toast } from '~/main'
import { setToken } from '~/utils/auth'
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

const loginRedirectPath = computed(() => {
  const redirect = Array.isArray(route.query.redirect)
    ? route.query.redirect[0]
    : route.query.redirect
  return typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//')
    ? redirect
    : '/papers'
})

const submitLogin = async () => {
  try {
    isWaitingForLogin.value = true
    const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username.value, password: password.value }),
    })
    const data = await res.json().catch(() => ({}))
    if (res.ok && data.token) {
      await setToken(data.token)
      toast.success('登录成功')
      await router.replace(loginRedirectPath.value)
      void registerPush()
    } else if (data.reason_code === 'EMAIL_SEND_FAILED') {
      const msg = data.error || data.message || res.statusText || '登录失败'
      toast.error(`${res.status} ${msg} (${data.reason_code})`)
    } else if (data.reason_code === 'NOT_VERIFIED') {
      toast.info('当前邮箱未验证，已经为您重新发送验证码')
      await navigateTo(
        { path: '/signup', query: { verify: '1', u: username.value } },
        { replace: true },
      )
    } else if (data.reason_code === 'IS_APPROVING') {
      toast.info('您的注册正在审批中, 请留意邮件')
      await navigateTo('/', { replace: true })
    } else if (data.reason_code === 'NOT_APPROVED') {
      await navigateTo({ path: '/signup-reason', query: { token: data.token } }, { replace: true })
    } else {
      const msg = data.error || data.message || res.statusText || '登录失败'
      const reason = data.reason_code ? ` (${data.reason_code})` : ''
      toast.error(`${res.status} ${msg}${reason}`)
    }
  } catch (e) {
    toast.error(`登录失败: ${e.message}`)
  } finally {
    isWaitingForLogin.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  height: 100%;
  width: 100%;
  background-color: var(--background-color);
}

.login-page-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: calc(40% - 120px);
  border-right: 1px solid var(--normal-border-color);
  padding-right: 120px;
}

.login-page-header-title {
  font-family: 'Pacifico', 'Comic Sans MS', cursive, 'Roboto', sans-serif;
  font-size: 42px;
  font-weight: bold;
  width: 100%;
  opacity: 0.75;
}

.login-page-header {
  font-size: 42px;
  font-weight: bold;
  width: 100%;
}

.email-login-page-content {
  margin-top: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  gap: 20px;
}

.login-page-input {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  width: calc(100% - 40px);
  padding: 15px 20px;
  border-radius: 10px;
  border: 1px solid #ccc;
  gap: 10px;
  margin-bottom: 20px;
}

.login-page-input-icon {
  opacity: 0.5;
  font-size: 16px;
}

.login-page-input-text {
  border: none;
  outline: none;
  width: 100%;
  font-size: 16px;
}

.login-page-button-primary {
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

.login-page-button-primary:hover {
  background-color: var(--primary-color-hover);
}

.login-page-button-primary.disabled {
  background-color: var(--primary-color-disabled);
  opacity: 0.5;
  cursor: not-allowed;
}

.login-page-button-primary.disabled:hover {
  background-color: var(--primary-color-disabled);
}

.login-page-button-text {
  font-size: 16px;
}

.login-page-button-secondary {
  margin-top: 20px;
  font-size: 16px;
  opacity: 0.7;
}

.login-page-button-secondary-link {
  color: var(--primary-color);
}

.hint-message {
  font-size: 12px;
  opacity: 0.7;
}

@media (max-width: 768px) {
  .login-page {
    flex-direction: column;
    justify-content: flex-start;
  }

  .login-page-content {
    margin-top: 20px;
    width: calc(100% - 40px);
    border-right: none;
    padding-left: 20px;
    padding-right: 20px;
  }

  .login-page-button-primary {
    margin-top: 0px;
  }

  .login-page-button-secondary {
    margin-top: 0px;
    font-size: 13px;
  }
}
</style>
