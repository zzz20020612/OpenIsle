<template>
  <div id="app" class="institutional-app">
    <a v-if="!isFloatMode" class="skip-link" href="#main-content">Skip to main content</a>
    <HeaderComponent v-if="!isFloatMode" />
    <main id="main-content" class="institutional-main" :class="{ 'float-mode': isFloatMode }" tabindex="-1">
      <NuxtPage />
    </main>
    <InstitutionalFooter v-if="!isFloatMode" />
    <GlobalPopups />
    <ConfirmDialog />
    <MessageFloatWindow v-if="!isFloatMode" />
  </div>
</template>

<script setup>
import HeaderComponent from '~/components/HeaderComponent.vue'
import InstitutionalFooter from '~/components/InstitutionalFooter.vue'
import GlobalPopups from '~/components/GlobalPopups.vue'
import ConfirmDialog from '~/components/ConfirmDialog.vue'
import MessageFloatWindow from '~/components/MessageFloatWindow.vue'
import { checkToken } from '~/utils/auth'

const route = useRoute()
const isFloatMode = computed(() => route.query.float !== undefined)
onMounted(() => { checkToken().catch(() => {}) })
</script>

<style src="~/assets/global.css"></style>
<style>
.institutional-app { min-height: 100vh; display: flex; flex-direction: column; background: var(--background-color); }
.institutional-main { flex: 1 0 auto; width: 100%; }
.institutional-main.float-mode { min-height: 100vh; }
.skip-link { position: fixed; left: 16px; top: -60px; z-index: 5000; padding: 12px 18px; color: #fff; background: #0072bc; font-weight: 700; }
.skip-link:focus { top: 12px; }
.page-enter-active, .page-leave-active { transition: opacity .12s linear; }
.page-enter-from, .page-leave-to { opacity: 0; }
</style>
