<template>
  <div class="third-party-auth">
    <button
      v-for="provider in providers"
      :key="provider.name"
      class="third-party-button"
      type="button"
      @click="provider.action"
    >
      <img class="third-party-button-icon" :src="provider.icon" :alt="provider.alt" />
      <span>{{ provider.label }}</span>
    </button>
  </div>
</template>

<script setup>
import googleIcon from '~/assets/icons/google.svg'
import githubIcon from '~/assets/icons/github.svg'
import discordIcon from '~/assets/icons/discord.svg'
import twitterIcon from '~/assets/icons/twitter.svg'
import telegramIcon from '~/assets/icons/telegram.svg'
import { googleAuthorize } from '~/utils/google'
import { githubAuthorize } from '~/utils/github'
import { discordAuthorize } from '~/utils/discord'
import { twitterAuthorize } from '~/utils/twitter'
import { telegramAuthorize } from '~/utils/telegram'

const props = defineProps({
  mode: { type: String, default: 'login' },
  inviteToken: { type: String, default: '' },
})

const actionText = computed(() => (props.mode === 'signup' ? 'Sign up with' : 'Continue with'))

const providers = computed(() => [
  { name: 'google', icon: googleIcon, action: () => googleAuthorize(props.inviteToken), alt: '', label: `${actionText.value} Google` },
  { name: 'github', icon: githubIcon, action: () => githubAuthorize(props.inviteToken), alt: '', label: `${actionText.value} GitHub` },
  { name: 'discord', icon: discordIcon, action: () => discordAuthorize(props.inviteToken), alt: '', label: `${actionText.value} Discord` },
  { name: 'twitter', icon: twitterIcon, action: () => twitterAuthorize(props.inviteToken), alt: '', label: `${actionText.value} X` },
  { name: 'telegram', icon: telegramIcon, action: () => telegramAuthorize(props.inviteToken), alt: '', label: `${actionText.value} Telegram` },
])
</script>

<style scoped>
.third-party-auth {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 9px;
}

.third-party-button {
  min-height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  gap: 9px;
  padding: 8px 11px;
  border: 1px solid #cbd5d8;
  border-radius: 2px;
  background: #fff;
  color: #31424b;
  font: inherit;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.third-party-button:hover { border-color: #8fa8b3; background: #f3f7f8; }
.third-party-button:focus-visible { outline: 2px solid #2b6b87; outline-offset: 2px; }
.third-party-button:last-child:nth-child(odd) { grid-column: 1 / -1; }
.third-party-button-icon { width: 18px; height: 18px; flex: 0 0 auto; }

@media (max-width: 520px) {
  .third-party-auth { grid-template-columns: 1fr; }
  .third-party-button:last-child:nth-child(odd) { grid-column: auto; }
}
</style>
