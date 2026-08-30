<template>
  <div class="settings-page">
    <AvatarCropper
      :src="tempAvatar"
      :show="showCropper"
      @close="showCropper = false"
      @crop="onCropped"
    />
    <div v-if="isLoadingPage" class="loading-page">
      <l-hatch size="28" stroke="4" speed="3.5" color="var(--primary-color)"></l-hatch>
    </div>
    <div v-else>
      <header class="settings-header">
        <p>ACCOUNT</p>
        <h1>Profile settings</h1>
        <span>Manage the identity shown on manuscripts, comments and scholarly discussions.</span>
      </header>
      <div class="profile-section">
        <div class="avatar-row">
          <!-- label 充当点击区域，内部隐藏 input -->
          <label class="avatar-container">
            <BaseUserAvatar
              :src="avatar"
              :user-id="userId"
              alt="avatar"
              class="avatar-preview"
              :disable-link="true"
            />
            <!-- 半透明蒙层：hover 时出现 -->
            <div class="avatar-overlay">Change photo</div>
            <input type="file" class="avatar-input" accept="image/*" @change="onAvatarChange" />
          </label>
        </div>
        <div class="form-row username-row">
          <BaseInput
            icon="user-icon"
            v-model="username"
            @input="usernameError = ''"
            placeholder="Username"
          />
          <div class="setting-description">Your username uniquely identifies you across OpenIsle.</div>
          <div v-if="usernameError" class="error-message">{{ usernameError }}</div>
        </div>
        <div class="form-row introduction-row">
          <div class="setting-title">Research profile</div>
          <BaseInput v-model="introduction" textarea rows="4" placeholder="Describe your research interests, methods or affiliation." />
          <div class="setting-description">This introduction appears on your public researcher profile.</div>
        </div>
        <div class="form-row switch-row">
          <div><div class="setting-title">Translucent interface</div><div class="setting-description">Use softened translucent surfaces where supported.</div></div>
          <BaseSwitch v-model="frosted" />
        </div>
      </div>
      <div v-if="role === 'ADMIN'" class="admin-section">
        <h2>Administration defaults</h2>
        <p class="admin-description">Platform-wide identity and access rules. Changes apply to all users.</p>
        <div class="form-row dropdown-row">
          <div class="setting-title">Password policy</div>
          <Dropdown v-model="passwordStrength" :fetch-options="fetchPasswordStrengths" />
        </div>
        <div class="form-row dropdown-row">
          <div class="setting-title">Account registration</div>
          <Dropdown v-model="registerMode" :fetch-options="fetchRegisterModes" />
        </div>
      </div>
      <div class="buttons">
        <button type="button" class="save-button" :disabled="isSaving" @click="save">{{ isSaving ? 'Saving…' : 'Save changes' }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import AvatarCropper from '~/components/AvatarCropper.vue'
import BaseInput from '~/components/BaseInput.vue'
import Dropdown from '~/components/Dropdown.vue'
import BaseSwitch from '~/components/BaseSwitch.vue'
import BaseUserAvatar from '~/components/BaseUserAvatar.vue'
import { toast } from '~/main'
import { fetchCurrentUser, getToken, setToken } from '~/utils/auth'
import { frostedState, setFrosted } from '~/utils/frosted'
const config = useRuntimeConfig()
const API_BASE_URL = config.public.apiBaseUrl
const username = ref('')
const introduction = ref('')
const usernameError = ref('')
const avatar = ref('')
const avatarFile = ref(null)
const tempAvatar = ref('')
const showCropper = ref(false)
const role = ref('')
const userId = ref(null)
const publishMode = ref('DIRECT')
const passwordStrength = ref('LOW')
const aiFormatLimit = ref(3)
const registerMode = ref('DIRECT')
const isLoadingPage = ref(false)
const isSaving = ref(false)
const frosted = ref(true)

onMounted(async () => {
  isLoadingPage.value = true
  const user = await fetchCurrentUser()

  if (user) {
    username.value = user.username
    introduction.value = user.introduction || ''
    avatar.value = user.avatar
    userId.value = user.id
    role.value = user.role
    if (role.value === 'ADMIN') {
      loadAdminConfig()
    }
  } else {
    toast.error('Please sign in to manage your profile.')
    navigateTo('/login', { replace: true })
  }
  isLoadingPage.value = false
  frosted.value = frostedState.enabled
})

const onAvatarChange = (e) => {
  const file = e.target.files[0]
  if (file) {
    const reader = new FileReader()
    reader.onload = () => {
      tempAvatar.value = reader.result
      showCropper.value = true
    }
    reader.readAsDataURL(file)
  }
}
watch(frosted, (val) => setFrosted(val))
const onCropped = ({ file, url }) => {
  avatarFile.value = file
  avatar.value = url
}
const fetchPasswordStrengths = () => {
  return Promise.resolve([
    { id: 'LOW', name: 'Basic', icon: 'unlock' },
    { id: 'MEDIUM', name: 'Standard', icon: 'lock-one' },
    { id: 'HIGH', name: 'Strong', icon: 'lock' },
  ])
}
const fetchRegisterModes = () => {
  return Promise.resolve([
    { id: 'DIRECT', name: 'Open registration', icon: 'send-icon' },
    { id: 'WHITELIST', name: 'Application review', icon: 'search-icon' },
  ])
}
const loadAdminConfig = async () => {
  try {
    const token = getToken()
    const res = await fetch(`${API_BASE_URL}/api/admin/config`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.ok) {
      const data = await res.json()
      publishMode.value = data.publishMode
      passwordStrength.value = data.passwordStrength
      aiFormatLimit.value = data.aiFormatLimit
      registerMode.value = data.registerMode
    }
  } catch (e) {
    // ignore
  }
}
const save = async () => {
  isSaving.value = true

  do {
    let token = getToken()
    usernameError.value = ''
    if (!username.value) {
      usernameError.value = 'Username is required.'
    }
    if (usernameError.value) {
      toast.error(usernameError.value)
      break
    }
    if (avatarFile.value) {
      const form = new FormData()
      form.append('file', avatarFile.value)
      const res = await fetch(`${API_BASE_URL}/api/users/me/avatar`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      })
      const data = await res.json()
      if (res.ok) {
        avatar.value = data.url
      } else {
        toast.error(data.error || 'The profile image could not be uploaded.')
        break
      }
    }
    const res = await fetch(`${API_BASE_URL}/api/users/me`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ username: username.value, introduction: introduction.value }),
    })

    const data = await res.json()
    if (!res.ok) {
      toast.error(data.error || 'Profile changes could not be saved.')
      break
    }
    if (data.token) {
      await setToken(data.token)
      token = data.token
    }
    if (role.value === 'ADMIN') {
      await fetch(`${API_BASE_URL}/api/admin/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          publishMode: publishMode.value,
          passwordStrength: passwordStrength.value,
          aiFormatLimit: aiFormatLimit.value,
          registerMode: registerMode.value,
        }),
      })
    }
    toast.success('Profile settings saved.')
  } while (!isSaving.value)

  isSaving.value = false
}
</script>

<style scoped>
.loading-page {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 300px;
}

.settings-page {
  width: min(920px, calc(100% - 40px));
  min-height: 620px;
  margin: 46px auto 70px;
  color: #2b3e47;
}

.settings-header { margin-bottom: 26px; padding-bottom: 22px; border-bottom: 1px solid #ccd6da; }
.settings-header p { margin: 0 0 7px; color: #176582; font-size: 12px; font-weight: 800; letter-spacing: .1em; }
.settings-header h1 { margin: 0 0 9px; font-family: Georgia, 'Times New Roman', serif; font-size: 38px; font-weight: 400; }
.settings-header span { color: #5d6d75; font-size: 14px; }
.profile-section, .admin-section { padding: 28px 32px; border: 1px solid #cad5d9; border-top: 4px solid #009edb; background: #fff; }

.avatar-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
}

.avatar-preview {
  width: 80px;
  height: 80px;
  border-radius: 40px;
}

.avatar-preview :deep(.base-user-avatar-img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.form-row {
  margin-bottom: 22px;
  display: flex;
  flex-direction: column;
}

.username-row {
  max-width: 420px;
}

.admin-section {
  margin-top: 24px;
  border-top-color: #0065a8;
}
.admin-section h2 { margin: 0 0 6px; font-family: Georgia, 'Times New Roman', serif; font-size: 25px; font-weight: 400; }
.admin-description { margin: 0 0 24px; color: #66767d; font-size: 13px; }

.setting-title {
  font-size: 14px;
  font-weight: bold;
  margin-bottom: 5px;
}

.setting-description {
  font-size: 12px;
  line-height: 1.5;
  color: #66767d;
  margin-top: 5px;
}

.introduction-row {
  max-width: 650px;
}

.dropdown-row {
  max-width: 360px;
}

.switch-row {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  max-width: 460px;
  padding-top: 8px;
}

.profile-section {
  margin-bottom: 30px;
}

.buttons {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

.avatar-container {
  position: relative;
  width: 80px;
  height: 80px;
  border-radius: 40px;
  cursor: pointer;
}

/* 隐藏默认文件选择按钮 */
.avatar-input {
  display: none;
}

/* 蒙层：初始透明，hover 时渐显 */
.avatar-overlay {
  position: absolute;
  inset: 0;
  border-radius: 40px;
  background: rgba(0, 0, 0, 0.4);
  color: #fff;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s ease-in-out;
}

/* hover 触发 */
.avatar-container:hover .avatar-overlay {
  opacity: 1;
}

.error-message {
  color: red;
  font-size: 14px;
  width: calc(100% - 40px);
  margin-top: -10px;
  margin-bottom: 10px;
}

.save-button {
  border: 0;
  background: #0065a8;
  color: white;
  min-height: 44px;
  padding: 10px 22px;
  font-size: 14px;
  font-weight: 750;
  cursor: pointer;
  transition: background-color 0.2s ease-in-out;
}

.save-button:hover {
  background-color: var(--primary-color-hover);
}

.save-button:disabled { background: #8a9aa2; cursor: wait; }
@media (max-width: 640px) {
  .settings-page { width: min(100% - 28px, 920px); margin-top: 28px; }
  .profile-section, .admin-section { padding: 22px 20px; }
  .settings-header h1 { font-size: 32px; }
}
</style>
