<template>
  <header class="site-header">
    <div class="utility-bar">
      <div class="header-width utility-inner">
        <span>Open research infrastructure</span>
        <nav aria-label="Utility navigation">
          <NuxtLink to="/about">About</NuxtLink>
          <NuxtLink v-if="isLogin" to="/message">Notifications<span v-if="unreadNotificationCount"> ({{ unreadNotificationCount }})</span></NuxtLink>
          <NuxtLink v-if="isLogin" to="/message-box">Messages<span v-if="unreadMessageCount"> ({{ unreadMessageCount }})</span></NuxtLink>
          <NuxtLink v-if="isLogin" to="/settings">Settings</NuxtLink>
          <button type="button" @click="cycleTheme">Display</button>
        </nav>
      </div>
    </div>

    <div class="masthead">
      <div class="header-width masthead-inner">
        <NuxtLink class="identity" to="/papers" aria-label="OpenIsle home">
          <BaseImage class="identity-mark" alt="" src="https://openisle-1307107697.cos.ap-guangzhou.myqcloud.com/assert/image.png" width="58" height="58" />
          <span><strong>OpenIsle</strong><small>Research Submission, Knowledge and Evaluation</small></span>
        </NuxtLink>
        <div class="masthead-actions">
          <SearchDropdown v-if="!isMobile" />
          <template v-if="isLogin">
            <NuxtLink class="account-link" :to="`/users/${authState.username || authState.userId}`">My account</NuxtLink>
            <button class="signout-link" type="button" @click="logout">Log out</button>
          </template>
          <template v-else>
            <NuxtLink class="account-link" to="/login">Log in</NuxtLink>
            <NuxtLink class="primary-action" to="/signup">Create account</NuxtLink>
          </template>
        </div>
      </div>
    </div>

    <div class="navigation-bar">
      <div class="header-width nav-inner">
        <button class="mobile-toggle" type="button" :aria-expanded="mobileOpen" aria-controls="primary-nav" @click="mobileOpen = !mobileOpen">
          <application-menu /> <span>Menu</span>
        </button>
        <nav id="primary-nav" class="primary-nav" :class="{ open: mobileOpen }" aria-label="Primary navigation">
          <NuxtLink v-for="item in navItems" :key="item.to" :to="item.to" @click="mobileOpen = false">{{ item.label }}</NuxtLink>
        </nav>
        <NuxtLink v-if="isLogin" class="submit-action" :to="{ path: '/papers/submit', query: { entry: Date.now().toString() } }">Submit research</NuxtLink>
        <NuxtLink v-else class="submit-action" to="/login">Submit research</NuxtLink>
      </div>
    </div>
  </header>
</template>

<script setup>
import BaseImage from '~/components/BaseImage.vue'
import SearchDropdown from '~/components/SearchDropdown.vue'
import { authState, clearToken } from '~/utils/auth'
import { notificationState, fetchUnreadCount as fetchNotificationUnreadCount } from '~/utils/notification'
import { useUnreadCount } from '~/composables/useUnreadCount'
import { useIsMobile } from '~/utils/screen'
import { cycleTheme } from '~/utils/theme'

const isLogin = computed(() => authState.loggedIn)
const isMobile = useIsMobile()
const mobileOpen = ref(false)
const { count: unreadMessageCount, fetchUnreadCount } = useUnreadCount()
const unreadNotificationCount = computed(() => notificationState.unreadCount)
const navItems = computed(() => [
  { to: '/papers', label: 'Papers' },
  { to: '/literature', label: 'Knowledge Base' },
  { to: '/papers/rankings', label: 'Rankings' },
  ...(authState.loggedIn ? [
    { to: '/papers/review-tasks', label: 'Reviews' },
    { to: '/papers/submissions', label: 'My Submissions' },
  ] : []),
  ...(authState.role === 'ADMIN' ? [
    { to: '/literature/workflow', label: 'Literature Processing' },
    { to: '/admin/papers', label: 'Administration' },
  ] : []),
])
const logout = () => { clearToken(); navigateTo('/login') }
onMounted(() => {
  if (authState.loggedIn) Promise.allSettled([fetchUnreadCount(), fetchNotificationUnreadCount()])
})
</script>

<style scoped>
.site-header{position:relative;z-index:1000;color:#222;background:#fff;border-bottom:1px solid #d2d2d2}.header-width{width:min(1180px,calc(100% - 40px));margin:0 auto}.utility-bar{min-height:34px;color:#eee;background:#242424;font-size:12px}.utility-inner{min-height:34px;display:flex;align-items:center;justify-content:space-between;gap:20px}.utility-inner nav{display:flex;align-items:center;gap:22px}.utility-inner a,.utility-inner button{padding:0;border:0;color:inherit;background:transparent;font:inherit;text-decoration:none;cursor:pointer}.utility-inner a:hover,.utility-inner button:hover{text-decoration:underline}.masthead{border-bottom:1px solid #ddd}.masthead-inner{min-height:105px;display:flex;align-items:center;justify-content:space-between;gap:32px}.identity{display:flex;align-items:center;gap:16px;color:#1b1b1b;text-decoration:none}.identity-mark{width:58px;height:58px;object-fit:contain}.identity span{display:grid;gap:4px}.identity strong{font-family:Georgia,'Times New Roman',serif;font-size:37px;font-weight:400;line-height:1}.identity small{color:#555;font-size:12px;letter-spacing:.055em;text-transform:uppercase}.masthead-actions{display:flex;align-items:center;gap:16px}.account-link,.signout-link{padding:8px 0;border:0;color:#333;background:transparent;font-size:13px;text-decoration:none;cursor:pointer}.primary-action{padding:10px 14px;color:#fff;background:#0072bc;font-size:13px;font-weight:700;text-decoration:none}.navigation-bar{color:#fff;background:#0065a8;border-bottom:5px solid #009edb}.nav-inner{display:flex;align-items:stretch;min-height:50px}.primary-nav{display:flex;align-items:stretch}.primary-nav a,.submit-action{display:flex;align-items:center;padding:0 17px;color:#fff;font-size:14px;font-weight:700;text-decoration:none;border-left:1px solid rgba(255,255,255,.2)}.primary-nav a:hover,.primary-nav a.router-link-active{background:#004f85}.submit-action{margin-left:auto;border-right:1px solid rgba(255,255,255,.2);background:#004f85}.mobile-toggle{display:none}.primary-nav a:focus-visible,.submit-action:focus-visible{outline:3px solid #fff;outline-offset:-4px}@media(max-width:900px){.masthead-actions>:first-child{display:none}.identity small{display:none}.identity strong{font-size:31px}.masthead-inner{min-height:82px}.nav-inner{display:block;width:100%}.mobile-toggle{display:flex;width:calc(100% - 32px);height:48px;align-items:center;gap:8px;margin:0 16px;border:0;color:#fff;background:transparent;font-weight:700}.primary-nav{display:none;flex-direction:column;border-top:1px solid rgba(255,255,255,.25)}.primary-nav.open{display:flex}.primary-nav a{min-height:45px;border-left:0;border-bottom:1px solid rgba(255,255,255,.18)}.submit-action{display:none}}@media(max-width:560px){.header-width{width:min(100% - 28px,1180px)}.utility-inner>span{display:none}.utility-inner{justify-content:flex-end}.utility-inner nav{gap:14px}.masthead-actions{gap:10px}.primary-action{display:none}.identity-mark{width:46px;height:46px}}
</style>
