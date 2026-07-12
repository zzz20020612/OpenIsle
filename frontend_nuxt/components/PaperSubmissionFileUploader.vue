<template>
  <div class="submission-file-manager">
    <div class="submission-required-files">
      <article v-for="row in REQUIRED_FILE_ROWS" :key="row.role" class="submission-file-row">
        <div class="submission-file-kind">
          <FileText :size="20" />
          <div>
            <div class="submission-file-label">
              {{ row.label }} <span aria-hidden="true">*</span>
            </div>
            <p>{{ row.description }}</p>
          </div>
        </div>

        <div v-if="fileForRole(row.role)" class="submission-file-record">
          <div class="submission-file-name">
            <strong>{{ fileForRole(row.role).displayName }}</strong>
            <span>
              {{ formatFileSize(fileForRole(row.role).fileSize) }}
              · {{ statusLabel(fileForRole(row.role).uploadStatus) }}
            </span>
          </div>
          <button
            class="submission-icon-button danger"
            type="button"
            :title="`Remove ${row.label}`"
            :aria-label="`Remove ${row.label}`"
            @click="$emit('remove', fileForRole(row.role).id)"
          >
            <Delete :size="17" />
          </button>
        </div>

        <label v-else class="submission-upload-button" :class="{ disabled: uploadState.active > 0 }">
          <UploadOne :size="18" />
          <span>{{ isUploading(row.role) ? 'Uploading...' : 'Choose file' }}</span>
          <input
            type="file"
            :accept="row.accept"
            :disabled="uploadState.active > 0"
            @change="selectRequiredFile($event, row)"
          />
        </label>
      </article>
    </div>

    <div class="submission-other-files">
      <div class="submission-subheading-row">
        <div>
          <h3>Other Files</h3>
          <p>Add Supporting Information, a PDF version, data, code, or review-only material.</p>
        </div>
      </div>

      <div class="submission-other-upload">
        <label class="submission-field compact">
          <span>Designation</span>
          <select v-model="newFile.role">
            <option v-for="role in OPTIONAL_FILE_ROLES" :key="role.value" :value="role.value">
              {{ role.label }}
            </option>
          </select>
        </label>
        <label class="submission-field compact">
          <span>Visibility</span>
          <select v-model="newFile.visibility" :disabled="newFile.role === 'REVIEW_ONLY'">
            <option value="PRIVATE">Private</option>
            <option value="PUBLIC">Public</option>
          </select>
        </label>
        <label class="submission-field description">
          <span>Description{{ descriptionRequired ? ' *' : '' }}</span>
          <input
            v-model.trim="newFile.description"
            placeholder="What does this file contain?"
          />
        </label>
        <label
          class="submission-upload-button secondary"
          :class="{ disabled: uploadState.active > 0 || descriptionMissing }"
          :title="descriptionMissing ? 'Add a description before uploading public Supporting Information' : 'Add another file'"
        >
          <AddOne :size="18" />
          <span>{{ isUploading(newFile.role) ? 'Uploading...' : 'Add file' }}</span>
          <input
            type="file"
            accept=".pdf,.doc,.docx,.xlsx,.csv,.zip,.txt,.png,.jpg,.jpeg,.webp,.tex,.bib,.json,.md,.py,.r,.js,.ts,.ipynb"
            :disabled="uploadState.active > 0 || descriptionMissing"
            @change="selectOptionalFile"
          />
        </label>
      </div>

      <div v-if="optionalFiles.length" class="submission-optional-list">
        <article v-for="file in optionalFiles" :key="file.id" class="submission-optional-file">
          <div class="submission-optional-file-head">
            <div>
              <strong>{{ file.displayName }}</strong>
              <span>{{ roleLabel(file.role) }} · {{ formatFileSize(file.fileSize) }}</span>
            </div>
            <button
              class="submission-icon-button danger"
              type="button"
              title="Remove file"
              aria-label="Remove file"
              @click="$emit('remove', file.id)"
            >
              <Delete :size="17" />
            </button>
          </div>
          <div class="submission-optional-file-fields">
            <label class="submission-field compact">
              <span>Display name</span>
              <input
                :value="file.displayName"
                @change="update(file, { displayName: $event.target.value })"
              />
            </label>
            <label class="submission-field compact">
              <span>Designation</span>
              <select :value="file.role" @change="update(file, { role: $event.target.value })">
                <option v-for="role in OPTIONAL_FILE_ROLES" :key="role.value" :value="role.value">
                  {{ role.label }}
                </option>
              </select>
            </label>
            <label class="submission-field compact">
              <span>Visibility</span>
              <select
                :value="file.visibility"
                :disabled="file.role === 'REVIEW_ONLY'"
                @change="update(file, { visibility: $event.target.value })"
              >
                <option value="PRIVATE">Private</option>
                <option value="PUBLIC">Public</option>
              </select>
            </label>
            <label class="submission-field description">
              <span>Description{{ publicSi(file) ? ' *' : '' }}</span>
              <input
                :value="file.description || ''"
                placeholder="Describe the contents"
                @change="update(file, { description: $event.target.value })"
              />
            </label>
          </div>
        </article>
      </div>
    </div>

    <p v-if="uploadState.error" class="submission-inline-error">{{ uploadState.error }}</p>
  </div>
</template>

<script setup>
import { AddOne, Delete, FileText, UploadOne } from '@icon-park/vue-next'
import {
  OPTIONAL_FILE_ROLES,
  REQUIRED_FILE_ROWS,
} from '~/config/paperSubmissionConfig'

const props = defineProps({
  files: { type: Array, default: () => [] },
  uploadState: { type: Object, required: true },
})

const emit = defineEmits(['upload', 'update', 'remove'])

const newFile = reactive({
  role: 'SUPPORTING_INFORMATION',
  visibility: 'PRIVATE',
  description: '',
})

watch(
  () => newFile.role,
  (role) => {
    if (role === 'REVIEW_ONLY') newFile.visibility = 'PRIVATE'
  },
)

const optionalFiles = computed(() =>
  props.files.filter((file) => !REQUIRED_FILE_ROWS.some((row) => row.role === file.role)),
)
const descriptionRequired = computed(() =>
  newFile.role === 'SUPPORTING_INFORMATION' && newFile.visibility === 'PUBLIC',
)
const descriptionMissing = computed(() => descriptionRequired.value && !newFile.description.trim())

const fileForRole = (role) => props.files.find((file) => file.role === role)
const isUploading = (role) => props.uploadState.active > 0 && props.uploadState.role === role
const publicSi = (file) => file.role === 'SUPPORTING_INFORMATION' && file.visibility === 'PUBLIC'

const selectRequiredFile = (event, row) => {
  const file = event.target.files?.[0]
  if (file) {
    emit('upload', file, {
      role: row.role,
      visibility: row.visibility,
      description: '',
      displayName: file.name,
    })
  }
  event.target.value = ''
}

const selectOptionalFile = (event) => {
  const file = event.target.files?.[0]
  if (file && !descriptionMissing.value) {
    emit('upload', file, {
      role: newFile.role,
      visibility: newFile.visibility,
      description: newFile.description,
      displayName: file.name,
    })
    newFile.description = ''
  }
  event.target.value = ''
}

const update = (file, payload) => {
  if (payload.role === 'REVIEW_ONLY') payload.visibility = 'PRIVATE'
  emit('update', file.id, payload)
}

const roleLabel = (role) =>
  OPTIONAL_FILE_ROLES.find((item) => item.value === role)?.label || role?.replaceAll('_', ' ')

const statusLabel = (status) => {
  if (status === 'UPLOADED') return 'Uploaded'
  if (status === 'FAILED') return 'Upload failed'
  return 'Pending'
}

const formatFileSize = (size) => {
  if (!size) return '0 B'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}
</script>

<style scoped>
.submission-file-manager { display: grid; gap: 28px; }
.submission-required-files { border: 1px solid #d7dce2; border-bottom: 0; }
.submission-file-row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(210px, 300px); gap: 20px; align-items: center; min-height: 96px; padding: 16px 18px; border-bottom: 1px solid #d7dce2; background: #fff; }
.submission-file-kind { display: flex; gap: 12px; min-width: 0; color: #27313a; }
.submission-file-kind svg { flex: 0 0 auto; margin-top: 2px; color: #4c6576; }
.submission-file-label { font-weight: 700; color: #17232c; }
.submission-file-label span { color: #b42318; }
.submission-file-kind p, .submission-subheading-row p { margin: 4px 0 0; color: #5f6b74; font-size: 13px; line-height: 1.45; }
.submission-upload-button { min-height: 42px; display: inline-flex; align-items: center; justify-content: center; gap: 8px; border: 1px solid #1f5b78; background: #fff; color: #174b64; padding: 8px 14px; font-weight: 700; cursor: pointer; }
.submission-upload-button.secondary { align-self: end; }
.submission-upload-button.disabled { opacity: .55; cursor: not-allowed; }
.submission-upload-button input { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; }
.submission-file-record { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-width: 0; padding: 10px 12px; background: #f4f7f8; border: 1px solid #d8e0e4; }
.submission-file-name { display: grid; min-width: 0; }
.submission-file-name strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; }
.submission-file-name span, .submission-optional-file-head span { color: #68747c; font-size: 12px; margin-top: 2px; }
.submission-icon-button { width: 36px; height: 36px; display: inline-grid; place-items: center; border: 1px solid #cbd3d8; background: #fff; color: #33424c; cursor: pointer; flex: 0 0 auto; }
.submission-icon-button.danger { color: #a53b32; }
.submission-icon-button:hover { background: #eef3f5; }
.submission-other-files { display: grid; gap: 14px; }
.submission-subheading-row h3 { margin: 0; font-size: 16px; }
.submission-other-upload { display: grid; grid-template-columns: 190px 130px minmax(220px, 1fr) auto; gap: 12px; align-items: end; padding: 16px; border: 1px solid #d7dce2; background: #f7f8f9; }
.submission-field { display: grid; gap: 6px; min-width: 0; }
.submission-field span { color: #36454f; font-size: 12px; font-weight: 700; }
.submission-field input, .submission-field select { width: 100%; min-height: 40px; border: 1px solid #bfc8ce; background: #fff; padding: 8px 10px; color: #18242c; }
.submission-optional-list { display: grid; gap: 10px; }
.submission-optional-file { border: 1px solid #d7dce2; padding: 14px; background: #fff; }
.submission-optional-file-head { display: flex; justify-content: space-between; gap: 16px; align-items: center; }
.submission-optional-file-head > div { display: grid; min-width: 0; }
.submission-optional-file-fields { display: grid; grid-template-columns: minmax(160px, .8fr) 180px 130px minmax(220px, 1.2fr); gap: 12px; margin-top: 12px; }
.submission-inline-error { margin: 0; color: #b42318; font-size: 13px; font-weight: 600; }
@media (max-width: 900px) {
  .submission-file-row { grid-template-columns: 1fr; }
  .submission-other-upload, .submission-optional-file-fields { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 560px) {
  .submission-file-row { padding: 14px; }
  .submission-other-upload, .submission-optional-file-fields { grid-template-columns: 1fr; }
  .submission-upload-button { width: 100%; }
}
</style>
