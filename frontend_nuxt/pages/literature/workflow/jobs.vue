<template>
  <main class="paper-shell">
    <div class="paper-container admin-container">
      <header class="paper-workspace-header">
        <div>
          <div class="paper-page-eyebrow">Knowledge Base / Administration</div>
          <h1 class="paper-page-title">Processing jobs</h1>
          <p class="paper-page-description">
            Inspect, filter, retry, and archive collection, download, parsing, and extraction jobs.
          </p>
        </div>
        <button class="paper-button" @click="load">Refresh</button>
      </header>
      <LiteratureKnowledgeNav />
      <LiteratureAdminNav />
      <p v-if="message" class="admin-notice" :class="{ error }">{{ message }}</p>
      <section class="summary-grid">
        <article>
          <strong>{{ stats.total_failed || 0 }}</strong
          ><span>Failed jobs</span>
        </article>
        <article>
          <strong>{{ stats.archived_count || 0 }}</strong
          ><span>Archived jobs</span>
        </article>
      </section>
      <section
        v-if="stats.by_error_class?.length || stats.by_stage_status?.length"
        class="job-stats-grid"
      >
        <article class="paper-panel admin-card">
          <h2>Failures by error class</h2>
          <AdminDataTable :rows="stats.by_error_class || []" empty="No failure categories." />
        </article>
        <article class="paper-panel admin-card">
          <h2>Jobs by stage and status</h2>
          <AdminDataTable :rows="stats.by_stage_status || []" empty="No stage statistics." />
        </article>
      </section>
      <section class="paper-panel admin-card">
        <form class="job-filters" @submit.prevent="applyFilters">
          <label
            >Stage<select v-model="filters.stage">
              <option value="">All stages</option>
              <option value="download">Download</option>
              <option value="parse">Parse</option>
              <option value="extract">Extract</option>
            </select></label
          ><label
            >Status<select v-model="filters.status">
              <option value="">All statuses</option>
              <option value="pending">Pending</option>
              <option value="running">Running</option>
              <option value="done">Done</option>
              <option value="failed">Failed</option>
              <option value="permanent_failed">Permanent failure</option>
              <option value="skipped">Skipped</option>
              <option value="superseded">Superseded</option>
            </select></label
          ><label
            >Error class<input
              v-model="filters.error_class"
              placeholder="Optional error category" /></label
          ><button class="admin-action">Apply filters</button>
        </form>
        <div v-if="loading" class="empty">Loading jobs…</div>
        <div v-else-if="!jobs.length" class="empty">No matching jobs.</div>
        <div v-else class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Paper</th>
                <th>Stage</th>
                <th>Status</th>
                <th>Error class</th>
                <th>Progress</th>
                <th>Message</th>
                <th>Created</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="job in jobs" :key="job.id">
                <td>{{ job.id }}</td>
                <td>
                  <NuxtLink v-if="job.paper_id" :to="`/literature/${job.paper_id}`">{{
                    job.paper_id
                  }}</NuxtLink
                  ><span v-else>—</span>
                </td>
                <td>{{ job.stage || job.job_type }}</td>
                <td>{{ job.status }}</td>
                <td>{{ job.error_class || '—' }}</td>
                <td>{{ Number(job.progress || 0) }}%</td>
                <td>{{ job.error_msg || job.error_message || job.message || '—' }}</td>
                <td>{{ format(job.created_at || job.started_at) }}</td>
                <td>
                  <button
                    v-if="
                      ['failed', 'permanent_failed'].includes(String(job.status).toLowerCase()) &&
                      job.paper_id &&
                      (job.stage || job.job_type)
                    "
                    :disabled="busy === job.id"
                    @click="retry(job)"
                  >
                    Retry
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <nav class="job-pagination">
          <button :disabled="offset === 0" @click="page(-1)">Previous</button
          ><span
            >Page {{ currentPage }}<template v-if="total"> of {{ pageCount }}</template> ·
            {{ total || jobs.length }} jobs</span
          ><button
            :disabled="jobs.length < limit || (total && offset + limit >= total)"
            @click="page(1)"
          >
            Next
          </button>
        </nav>
        <div class="archive">
          <label
            >Archive completed jobs older than
            <input v-model.number="archiveDays" type="number" min="1" /> days</label
          ><button class="admin-action" @click="archive">Archive</button>
        </div>
      </section>
    </div>
  </main>
</template>
<script setup>
import '~/assets/paper-platform.css'
import { authState, loadCurrentUser } from '~/utils/auth'
definePageMeta({ middleware: 'auth-client' })
useHead({ title: 'Literature Jobs - OpenIsle' })
const api = useLiteratureAdmin(),
  jobs = ref([]),
  stats = ref({}),
  filters = reactive({ stage: '', status: '', error_class: '' }),
  loading = ref(true),
  busy = ref(null),
  archiveDays = ref(7),
  message = ref(''),
  error = ref(false),
  offset = ref(0),
  limit = 50,
  total = ref(0)
const currentPage = computed(() => Math.floor(offset.value / limit) + 1),
  pageCount = computed(() => Math.max(1, Math.ceil(total.value / limit)))
const ensure = async () => {
  if (!authState.role) await loadCurrentUser()
  if (authState.role !== 'ADMIN') return navigateTo('/literature/workflow')
  return true
}
const load = async () => {
  loading.value = true
  error.value = false
  try {
    if (!(await ensure())) return
    const params = {
      limit,
      offset: offset.value,
      ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)),
    }
    const [list, summary] = await Promise.all([api.get('/jobs', params), api.get('/jobs/stats')])
    jobs.value = list.jobs || list.items || (Array.isArray(list) ? list : [])
    total.value = Number(list.total || list.count || 0)
    stats.value = summary
  } catch (e) {
    error.value = true
    message.value = e?.data?.message || e.message
  } finally {
    loading.value = false
  }
}
const applyFilters = () => {
  offset.value = 0
  load()
}
const page = (direction) => {
  offset.value = Math.max(0, offset.value + direction * limit)
  load()
}
const retry = async (job) => {
  busy.value = job.id
  try {
    await api.post('/retry', {
      paper_id: job.paper_id,
      stage: job.stage || job.job_type,
      job_id: job.id,
    })
    message.value = 'Retry task submitted.'
    await load()
  } catch (e) {
    error.value = true
    message.value = e?.data?.message || e.message
  } finally {
    busy.value = null
  }
}
const archive = async () => {
  if (!window.confirm(`Archive completed or failed jobs older than ${archiveDays.value} days?`))
    return
  try {
    await api.post('/jobs/archive', { days: archiveDays.value, batch: 1000 })
    message.value = 'Archive task submitted.'
    offset.value = 0
    await load()
  } catch (e) {
    error.value = true
    message.value = e?.data?.message || e.message
  }
}
const humanize = (v) => v.replaceAll('_', ' ')
const format = (value) => {
  if (!value) return '—'
  const raw = String(value)
  // The literature engine stores naive timestamps in UTC. Add the missing
  // timezone marker so browsers convert them to the viewer's local timezone.
  const normalized = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?$/.test(raw)
    ? `${raw.replace(' ', 'T')}Z`
    : raw
  return new Date(normalized).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
}
onMounted(load)
</script>
<style scoped src="~/assets/literature-admin.css"></style>
<style scoped>
.job-stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.job-filters {
  display: flex;
  align-items: end;
  gap: 12px;
  margin-bottom: 18px;
}
.job-filters label {
  display: grid;
  gap: 5px;
  color: var(--paper-muted);
  font-size: 12px;
  font-weight: 750;
}
.job-filters input,
.job-filters select,
.archive input {
  min-height: 38px;
  border: 1px solid var(--paper-line);
  padding: 8px;
  background: #fff;
}
.job-pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  padding: 14px;
}
.job-pagination button {
  border: 1px solid var(--paper-line);
  background: #fff;
  padding: 7px 10px;
}
.job-pagination span {
  color: var(--paper-muted);
  font-size: 11px;
}
.archive {
  display: flex;
  align-items: end;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 16px;
}
.archive label {
  color: var(--paper-muted);
  font-size: 12px;
}
@media (max-width: 700px) {
  .job-stats-grid {
    grid-template-columns: 1fr;
  }
  .job-filters {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
