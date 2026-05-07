<template>
  <div class="login-overlay">
    <div class="login-overlay-blur"></div>
    <div class="login-overlay-content">
      <user-icon class="login-overlay-icon" />
      <div class="login-overlay-text">{{ props.text }}</div>
      <div class="login-overlay-button" @click="goLogin">{{ props.buttonText }}</div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  text: {
    type: String,
    default: 'Please sign in to continue.',
  },
  buttonText: {
    type: String,
    default: 'Log in',
  },
  buttonLink: {
    type: String,
    default: '/login',
  },
})

const goLogin = () => {
  navigateTo(props.buttonLink, { replace: true })
}
</script>

<style scoped>
.login-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 15;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.login-overlay-blur {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  backdrop-filter: var(--blur-4);
  z-index: 1;
}

.login-overlay-content {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  border-radius: 10px;
  padding: 24px 32px;
  flex-wrap: wrap;
  justify-content: center;
  row-gap: 20px;
}

.login-overlay-icon {
  margin-right: 10px;
}

.login-overlay-button {
  padding: 4px 12px;
  border-radius: 5px;
  background-color: var(--primary-color);
  color: white;
  cursor: pointer;
  margin-left: 10px;
  cursor: pointer;
}

.login-overlay-button:hover {
  background-color: var(--primary-color-hover);
}
</style>
