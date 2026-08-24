<template>
  <main class="paper-shell">
    <div class="paper-container review-workspace">
      <header class="paper-workspace-header">
        <div>
          <div class="paper-page-eyebrow">Scholar衡 reviewer workspace</div>
          <h1 class="paper-page-title">Review Tasks</h1>
          <p class="paper-page-description">Claim a complete literature record, declare conflicts, and finish its six-dimensional evaluation within seven days.</p>
        </div>
        <NuxtLink class="paper-button" to="/papers/rankings">View rankings</NuxtLink>
      </header>

      <section class="review-profile" aria-label="Reviewer profile">
        <div><span>Reviewer level</span><strong>{{ profile.level || 'B' }}</strong><small>{{ profile.eligible === false ? 'Qualification paused' : 'Eligible to review' }}</small></div>
        <div><span>Points</span><strong>{{ profile.points || 0 }}</strong><small>Earned from completed tasks</small></div>
        <div><span>Credit</span><strong>{{ Number(profile.creditScore || 75).toFixed(0) }}</strong><small>Scholar衡 credit score</small></div>
        <div><span>Completed</span><strong>{{ profile.completedTasks || 0 }}</strong><small>{{ profile.onTimeRate || 0 }}% on time</small></div>
      </section>

      <div class="paper-tabs">
        <button v-for="tab in tabs" :key="tab.key" class="paper-tab" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">{{ tab.label }} <span>{{ countFor(tab.key) }}</span></button>
      </div>

      <p v-if="pending" class="review-state">Loading review tasks…</p>
      <p v-else-if="loadError" class="review-state error">Unable to load review tasks. Please refresh the page.</p>
      <section v-else class="review-list">
        <article v-for="task in visibleTasks" :key="`${task.status}-${task.id || task.literaturePaperId}`" class="review-row">
          <div>
            <span class="review-meta">{{ task.journal || 'Journal unavailable' }}<template v-if="task.year"> · {{ task.year }}</template></span>
            <h2>{{ task.title }}</h2>
            <p>{{ task.authors || 'Authors unavailable' }}</p>
            <small v-if="task.status === 'ACCEPTED' || task.status === 'OVERDUE'">Due {{ formatDate(task.dueAt) }}</small>
            <small v-else-if="task.status === 'COMPLETED'">Completed {{ formatDate(task.completedAt) }} · +{{ task.awardedPoints }} points</small>
          </div>
          <button v-if="task.status === 'AVAILABLE'" class="review-action" type="button" @click="openClaim(task)">Claim task</button>
          <NuxtLink v-else class="review-action" :to="`/literature/${task.literaturePaperId}`">{{ task.status === 'COMPLETED' ? 'View evaluation' : 'Review paper' }}</NuxtLink>
        </article>
        <p v-if="!visibleTasks.length" class="review-state">No tasks in this section.</p>
      </section>
    </div>

    <div v-if="claimTarget" class="review-modal-backdrop" @click.self="closeClaim">
      <section class="review-modal" role="dialog" aria-modal="true" aria-labelledby="conflict-title">
        <button class="review-modal-close" type="button" aria-label="Close" @click="closeClaim">×</button>
        <div class="paper-page-eyebrow">Required declaration</div>
        <h2 id="conflict-title">Conflict-of-interest check</h2>
        <p>Confirm each statement before claiming “{{ claimTarget.title }}”. A disclosed conflict prevents a scored review.</p>
        <label v-for="item in conflictItems" :key="item.key" class="conflict-row">
          <input v-model="declaration[item.key]" type="checkbox">
          <span>{{ item.label }}</span>
        </label>
        <label class="clean-confirm"><input v-model="cleanConfirmed" type="checkbox"> I confirm that none of the conflicts above applies to me.</label>
        <p v-if="claimError" class="claim-error">{{ claimError }}</p>
        <button class="claim-submit" type="button" :disabled="!cleanConfirmed || claiming" @click="claim">{{ claiming ? 'Claiming…' : 'Confirm and claim' }}</button>
      </section>
    </div>
  </main>
</template>

<script setup>
import '~/assets/paper-platform.css'

definePageMeta({ middleware: 'auth-client' })
useHead({ title: 'Review Tasks - OpenIsle' })

const { listAvailableReviewTasks, listMyReviewTasks, getReviewerProfile, claimReviewTask } = useLiteratureApi()
const activeTab = ref('available')
const tabs = [{ key: 'available', label: 'Available' }, { key: 'progress', label: 'In progress' }, { key: 'completed', label: 'Completed' }]
const available = ref([])
const mine = ref([])
const profile = ref({})
const pending = ref(true)
const loadError = ref(false)
const claimTarget = ref(null)
const claiming = ref(false)
const claimError = ref('')
const cleanConfirmed = ref(false)
const declaration = reactive({ authorOrCoauthor: false, sameInstitution: false, recentCollaborator: false, advisorOrStudent: false, otherDirectConflict: false })
const conflictItems = [
  { key: 'authorOrCoauthor', label: 'I am an author or co-author of this paper.' },
  { key: 'sameInstitution', label: 'I currently share, or recently shared, an institution with an author.' },
  { key: 'recentCollaborator', label: 'I collaborated, published, patented, or held a project with an author in the relevant period.' },
  { key: 'advisorOrStudent', label: 'I have an advisor, student, or direct reporting relationship with an author.' },
  { key: 'otherDirectConflict', label: 'I have another family, financial, legal, or direct competitive conflict.' },
]

const progressTasks = computed(() => mine.value.filter(task => ['ACCEPTED', 'OVERDUE'].includes(task.status)))
const completedTasks = computed(() => mine.value.filter(task => task.status === 'COMPLETED'))
const visibleTasks = computed(() => activeTab.value === 'available' ? available.value : activeTab.value === 'progress' ? progressTasks.value : completedTasks.value)
const countFor = key => key === 'available' ? available.value.length : key === 'progress' ? progressTasks.value.length : completedTasks.value.length
const formatDate = value => value ? new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : '—'

const load = async () => {
  pending.value = true; loadError.value = false
  try {
    const [availableData, mineData, profileData] = await Promise.all([listAvailableReviewTasks(20), listMyReviewTasks(), getReviewerProfile()])
    available.value = Array.isArray(availableData) ? availableData : []
    mine.value = Array.isArray(mineData) ? mineData : []
    profile.value = profileData || {}
  } catch { loadError.value = true } finally { pending.value = false }
}
const openClaim = task => { claimTarget.value = task; claimError.value = ''; cleanConfirmed.value = false; Object.keys(declaration).forEach(key => { declaration[key] = false }) }
const closeClaim = () => { if (!claiming.value) claimTarget.value = null }
const claim = async () => {
  if (!claimTarget.value || !cleanConfirmed.value) return
  claiming.value = true; claimError.value = ''
  try {
    await claimReviewTask(claimTarget.value.literaturePaperId, { ...declaration })
    claimTarget.value = null; activeTab.value = 'progress'; await load()
  } catch (error) { claimError.value = error?.data?.error || error?.data?.message || error?.message || 'Unable to claim this task.' } finally { claiming.value = false }
}

onMounted(load)
</script>

<style scoped>
.review-workspace { padding-bottom: 64px; }.review-profile { display:grid;grid-template-columns:repeat(4,1fr);gap:0;margin:24px 0;border-top:1px solid #aebbc0;border-bottom:1px solid #aebbc0}.review-profile>div{display:grid;gap:4px;padding:18px;border-right:1px solid #cbd7dc;background:transparent}.review-profile>div:last-child{border-right:0}.review-profile span,.review-meta{color:#527080;font-size:11px;font-weight:800;letter-spacing:.06em;text-transform:uppercase}.review-profile strong{font-family:Georgia,serif;font-size:30px;color:#173847;font-weight:400}.review-profile small,.review-row small{color:#687980}.paper-tab span{margin-left:4px;color:#6e7c82}.review-list{border-top:1px solid #ccd7db}.review-row{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:24px;padding:20px 4px;border-bottom:1px solid #d8e0e3}.review-row h2{margin:6px 0;font-family:Georgia,serif;font-size:20px;font-weight:400}.review-row p{margin:0 0 7px;color:#65757c}.review-action,.claim-submit{padding:10px 14px;border:1px solid #0065a8;background:#0065a8;color:#fff;font-weight:750;text-decoration:none;cursor:pointer}.review-state{padding:34px 4px;color:#687980}.review-state.error,.claim-error{color:#9b3934}.review-modal-backdrop{position:fixed;inset:0;z-index:1000;display:grid;place-items:center;padding:20px;background:rgba(20,36,43,.58)}.review-modal{position:relative;width:min(620px,100%);max-height:90vh;overflow:auto;padding:30px;border-top:5px solid #0065a8;background:#fff}.review-modal h2{margin:8px 0;font-family:Georgia,serif;font-size:28px;font-weight:400}.review-modal>p{color:#617179;line-height:1.55}.review-modal-close{position:absolute;right:14px;top:10px;border:0;background:transparent;font-size:28px;cursor:pointer}.conflict-row,.clean-confirm{display:flex;align-items:flex-start;gap:10px;padding:11px 0;border-top:1px solid #e1e7e9;font-size:14px;line-height:1.45}.clean-confirm{margin-top:10px;border-top:2px solid #afc4cc;font-weight:750}.claim-submit{margin-top:16px}.claim-submit:disabled{cursor:not-allowed;opacity:.5}@media(max-width:760px){.review-profile{grid-template-columns:repeat(2,1fr)}.review-row{grid-template-columns:1fr;align-items:start}.review-action{width:max-content}}
</style>
