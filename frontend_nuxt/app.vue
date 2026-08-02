<template>
  <div id="app">
    <div v-if="!isFloatMode" class="header-container">
      <HeaderComponent
        ref="header"
        @toggle-menu="menuVisible = !menuVisible"
        :show-menu-btn="!hideMenu"
      />
    </div>

    <div class="main-container">
      <div v-if="!isFloatMode" class="menu-container" v-click-outside="handleMenuOutside">
        <MenuComponent :visible="!hideMenu && menuVisible" @item-click="menuVisible = false" />
      </div>
      <div
        class="content"
        :class="{ 'menu-open': menuVisible && !hideMenu && !isFloatMode }"
        :style="isFloatMode ? { paddingTop: '0px', minHeight: '100vh' } : {}"
      >
        <NuxtPage />
      </div>

      <div
        v-if="showNewPostIcon && isMobile && !isFloatMode"
        class="app-new-post-icon"
        @click="goToNewPost"
      >
        <edit />
      </div>
    </div>
    <GlobalPopups />
    <ConfirmDialog />
    <MessageFloatWindow v-if="!isFloatMode" />
  </div>
</template>

<script setup>
import HeaderComponent from '~/components/HeaderComponent.vue'
import MenuComponent from '~/components/MenuComponent.vue'
import GlobalPopups from '~/components/GlobalPopups.vue'
import ConfirmDialog from '~/components/ConfirmDialog.vue'
import MessageFloatWindow from '~/components/MessageFloatWindow.vue'
import { useIsMobile } from '~/utils/screen'
import { checkToken } from '~/utils/auth'

const isMobile = useIsMobile()
const menuVisible = ref(!isMobile.value)

onMounted(() => {
  checkToken().catch(() => {})
})

const showNewPostIcon = computed(() => useRoute().path === '/')

const hideMenu = computed(() => {
  return [
    '/login',
    '/signup',
    '/404',
    '/signup-reason',
    '/github-callback',
    '/twitter-callback',
    '/discord-callback',
    '/forgot-password',
    '/google-callback',
    '/telegram-callback',
  ].includes(useRoute().path)
})

const header = useTemplateRef('header')
const isFloatMode = computed(() => useRoute().query.float !== undefined)
onMounted(() => {
  if (typeof window !== 'undefined') {
    menuVisible.value = window.innerWidth > 768
  }
})

const handleMenuOutside = (event) => {
  const btn = header.value.$refs.menuBtn
  if (btn && (btn === event.target || btn.contains(event.target))) {
    return // 如果是菜单按钮的点击，不处理关闭
  }

  if (isMobile.value) {
    menuVisible.value = false
  }
}

const goToNewPost = () => {
  navigateTo('/new-post', { replace: false })
}
</script>

<style src="~/assets/global.css"></style>
<style>
/* 页面过渡效果 */
.page-enter-active,
.page-leave-active {
  transition: all 0.4s;
}
.page-enter-from,
.page-leave-to {
  opacity: 0;
  filter: blur(10px);
}

.header-container {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
}

.menu-container {
}

.content {
  /* height: calc(100vh - var(--header-height)); */
  padding-top: var(--header-height);
  flex: 1;
  max-width: 100%;
  transition: max-width 0.3s ease;
  background-color: var(--background-color);
  min-height: calc(100vh - var(--header-height));
}

.content.menu-open {
  max-width: calc(100% - var(--menu-width));
}

.main-container {
  display: flex;
  flex-direction: row;
  max-width: var(--page-max-width);
  margin: 0 auto;
}

.app-new-post-icon {
  background-color: var(--new-post-icon-color);
  color: white;
  width: 60px;
  height: 60px;
  border-radius: 50%;
  position: fixed;
  bottom: 70px;
  right: 20px;
  font-size: 20px;
  cursor: pointer;
  z-index: 1000;
  display: flex;
  backdrop-filter: var(--blur-5);
  justify-content: center;
  align-items: center;
}

@media (max-width: 768px) {
  .content,
  .content.menu-open {
    max-width: 100% !important;
  }
}
</style>
