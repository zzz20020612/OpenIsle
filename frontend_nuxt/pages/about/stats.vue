<template>
  <main class="site-stats-page">
    <header class="stats-header">
      <div><p>ADMINISTRATION</p><h1>Platform activity</h1><span>Thirty-day operational overview for the OpenIsle trial programme.</span></div>
      <NuxtLink to="/admin/papers">Return to administration</NuxtLink>
    </header>
    <div v-if="isLoading" class="loading-message">
      <l-hatch size="28" stroke="4" speed="3.5" color="var(--primary-color)"></l-hatch>
    </div>
    <div v-else-if="loadError" class="stats-error" role="alert">{{ loadError }}</div>
    <ClientOnly v-else>
      <div class="chart-grid">
      <VChart
        v-if="dauOption"
        :option="dauOption"
        :autoresize="true"
        class="stats-chart"
      />
      <VChart
        v-if="newUserOption"
        :option="newUserOption"
        :autoresize="true"
        class="stats-chart"
      />
      <VChart
        v-if="postOption"
        :option="postOption"
        :autoresize="true"
        class="stats-chart"
      />
      <VChart
        v-if="commentOption"
        :option="commentOption"
        :autoresize="true"
        class="stats-chart"
      />
      </div>
    </ClientOnly>
  </main>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getToken } from '~/utils/auth'
import { authState, loadCurrentUser } from '~/utils/auth'
definePageMeta({ middleware: 'auth-client' })
useHead({ title: 'Platform Activity - OpenIsle Administration' })
const config = useRuntimeConfig()
const API_BASE_URL = config.public.apiBaseUrl

const dauOption = ref(null)
const newUserOption = ref(null)
const postOption = ref(null)
const commentOption = ref(null)
const isLoading = ref(false)
const loadError = ref('')

async function loadData() {
  isLoading.value = true
  loadError.value = ''
  if (!authState.role) await loadCurrentUser()
  if (authState.role !== 'ADMIN') {
    await navigateTo('/about', { replace: true })
    return
  }
  const token = getToken()
  const headers = { Authorization: `Bearer ${token}` }

  try {
  const [dauRes, newUserRes, postRes, commentRes] = await Promise.all([
    fetch(`${API_BASE_URL}/api/stats/dau-range?days=30`, { headers }),
    fetch(`${API_BASE_URL}/api/stats/new-users-range?days=30`, { headers }),
    fetch(`${API_BASE_URL}/api/stats/posts-range?days=30`, { headers }),
    fetch(`${API_BASE_URL}/api/stats/comments-range?days=30`, { headers }),
  ])

  function toOption(title, data) {
    data.sort((a, b) => new Date(a.date) - new Date(b.date))
    const dates = data.map((d) => d.date)
    const values = data.map((d) => d.value)
    return {
      title: { text: title },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: dates },
      yAxis: { type: 'value' },
      dataZoom: [{ type: 'slider', start: 80 }, { type: 'inside' }],
      series: [{ type: 'line', areaStyle: {}, smooth: true, data: values }],
    }
  }

  if (dauRes.ok) {
    const data = await dauRes.json()
    dauOption.value = toOption('Daily active users', data)
  }
  if (newUserRes.ok) {
    const data = await newUserRes.json()
    newUserOption.value = toOption('New registered users', data)
  }
  if (postRes.ok) {
    const data = await postRes.json()
    postOption.value = toOption('New research discussions', data)
  }
  if (commentRes.ok) {
    const data = await commentRes.json()
    commentOption.value = toOption('Discussion comments', data)
  }
  if (![dauRes, newUserRes, postRes, commentRes].some(res => res.ok)) loadError.value = 'Activity statistics are currently unavailable.'
  } catch {
    loadError.value = 'Activity statistics are currently unavailable.'
  } finally {
    isLoading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.site-stats-page {
  width: min(1180px, calc(100% - 40px));
  margin: 0 auto;
  padding: 46px 0 72px;
  color: #2c424d;
}
.stats-header { display: flex; justify-content: space-between; gap: 30px; align-items: end; margin-bottom: 28px; padding-bottom: 22px; border-bottom: 1px solid #c5d0d4; }
.stats-header p { margin: 0 0 7px; color: #176582; font-size: 11px; font-weight: 800; letter-spacing: .1em; }
.stats-header h1 { margin: 0 0 7px; font-family: Georgia, 'Times New Roman', serif; font-size: 38px; font-weight: 400; }
.stats-header span { color: #607078; font-size: 14px; }
.stats-header a { padding: 10px 14px; border: 1px solid #0065a8; color: #0065a8; font-size: 13px; font-weight: 750; text-decoration: none; white-space: nowrap; }
.chart-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.stats-chart { height: 360px; border: 1px solid #cad4d8; border-top: 4px solid #009edb; background: #fff; }
.stats-error { padding: 20px; border-left: 4px solid #a3312d; background: #f7eeee; color: #7d2a27; }

.loading-message {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 400px;
}
@media(max-width:800px){.chart-grid{grid-template-columns:1fr}.stats-header{align-items:flex-start;flex-direction:column}.stats-chart{height:320px}}
</style>
