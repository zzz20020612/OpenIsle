<template>
  <article class="draft-row">
    <div class="draft-identity">
      <strong>{{ draftDisplayTitle(draft) }}</strong>
      <span>{{ draftSourceLabel(draft) }}</span>
      <small>Last edited {{ formatDraftTime(draft.updatedAt) }}</small>
    </div>

    <form v-if="mode === 'rename'" class="draft-inline-form" @submit.prevent="saveName">
      <label class="sr-only" :for="`draft-name-${draft.id}`">Draft name</label>
      <input :id="`draft-name-${draft.id}`" v-model="name" maxlength="160" autofocus />
      <button type="submit" :disabled="busy">{{ busy ? 'Saving...' : 'Save' }}</button>
      <button type="button" :disabled="busy" @click="mode = 'actions'">Cancel</button>
    </form>

    <div v-else-if="mode === 'delete'" class="draft-delete-confirm" role="group" aria-label="Confirm discard draft">
      <span>Discard this draft?</span>
      <button type="button" class="danger" :disabled="busy" @click="discardDraft">{{ busy ? 'Discarding...' : 'Discard' }}</button>
      <button type="button" :disabled="busy" @click="mode = 'actions'">Keep</button>
    </div>

    <div v-else class="draft-actions">
      <NuxtLink :to="{ path: '/papers/submit', query: { draft: draft.id } }">Continue</NuxtLink>
      <button type="button" @click="beginRename">Rename</button>
      <button type="button" class="danger" @click="mode = 'delete'">Discard</button>
    </div>
  </article>
</template>

<script setup>
import { toast } from '~/main'
import { draftDisplayTitle, draftSourceLabel } from '~/utils/paperDraftPresentation'

const props = defineProps({ draft: { type: Object, required: true } })
const emit = defineEmits(['updated', 'deleted'])
const { renameSubmissionDraft, discardSubmissionDraft } = usePaperApi()
const mode = ref('actions')
const name = ref('')
const busy = ref(false)

const formatDraftTime = (value) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'recently'
  return new Intl.DateTimeFormat('en', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}
const beginRename = () => {
  name.value = props.draft.displayName || draftDisplayTitle(props.draft)
  mode.value = 'rename'
}
const saveName = async () => {
  if (busy.value) return
  busy.value = true
  try {
    emit('updated', await renameSubmissionDraft(props.draft.id, name.value))
    mode.value = 'actions'
  } catch (error) {
    toast.error(error?.data?.error || error?.message || 'Unable to rename this draft.')
  } finally {
    busy.value = false
  }
}
const discardDraft = async () => {
  if (busy.value) return
  busy.value = true
  try {
    await discardSubmissionDraft(props.draft.id)
    emit('deleted', props.draft.id)
  } catch (error) {
    toast.error(error?.data?.error || error?.message || 'Unable to discard this draft.')
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.draft-row { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 14px 18px; border-top: 1px solid #e0e6e9; }
.draft-identity { display: grid; gap: 3px; min-width: 0; }
.draft-identity strong { overflow-wrap: anywhere; color: #20313a; font-size: 15px; }
.draft-identity span, .draft-identity small { color: #6a777e; font-size: 12px; }
.draft-actions, .draft-inline-form, .draft-delete-confirm { display: flex; flex: 0 0 auto; align-items: center; gap: 7px; }
.draft-actions a, button { padding: 7px 9px; border: 1px solid #b9c7cd; background: #fff; color: #245f7d; font: inherit; font-size: 12px; font-weight: 700; text-decoration: none; cursor: pointer; }
.draft-actions a { border-color: #2f6178; }
button:hover, .draft-actions a:hover { background: #edf4f7; }
button.danger { color: #9a3f37; }
button:disabled { cursor: wait; opacity: .6; }
.draft-inline-form input { width: min(260px, 28vw); padding: 8px 9px; border: 1px solid #96aab3; font: inherit; }
.draft-delete-confirm span { color: #79342f; font-size: 12px; font-weight: 700; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; }
@media (max-width: 700px) { .draft-row { align-items: stretch; flex-direction: column; }.draft-actions, .draft-inline-form, .draft-delete-confirm { flex-wrap: wrap; }.draft-inline-form input { width: 100%; } }
</style>
