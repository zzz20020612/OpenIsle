import { randomUUID } from 'node:crypto'
import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import { basename, extname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = fileURLToPath(new URL('.', import.meta.url))
const generatedDir = resolve(process.argv[2] || join(scriptDir, 'generated'))
const payloadPath = join(generatedDir, 'paper01-submission.json')
const statePath = join(generatedDir, 'submitted-paper.json')
const apiBase = (process.env.OPENISLE_API_URL || 'http://localhost:8080').replace(/\/$/, '')
const force = process.argv.includes('--force')

if (existsSync(statePath) && !force) {
  const previous = JSON.parse(readFileSync(statePath, 'utf8'))
  console.log(`paper01 is already retained as paper ${previous.paperId}.`)
  console.log(`${process.env.OPENISLE_WEB_URL || 'http://localhost:3000'}/papers/${previous.paperId}`)
  process.exit(0)
}

const payload = JSON.parse(readFileSync(payloadPath, 'utf8'))

const request = async (path, options = {}) => {
  const response = await fetch(`${apiBase}${path}`, options)
  const text = await response.text()
  let body = null
  try { body = text ? JSON.parse(text) : null } catch { body = text }
  if (!response.ok) {
    throw new Error(`${options.method || 'GET'} ${path} failed (${response.status}): ${typeof body === 'string' ? body : JSON.stringify(body)}`)
  }
  return body
}

let token = process.env.OPENISLE_TOKEN
if (!token) {
  const login = await request('/api/auth/login', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      username: process.env.OPENISLE_USERNAME || 'user1',
      password: process.env.OPENISLE_PASSWORD || '123456',
    }),
  })
  token = login.token
}

const headers = { authorization: `Bearer ${token}` }
const jsonHeaders = { ...headers, 'content-type': 'application/json' }
const requestedDraftId = process.env.OPENISLE_DRAFT_ID
const draft = requestedDraftId
  ? await request(`/api/paper-submission-drafts/${requestedDraftId}`, { headers })
  : await request('/api/paper-submission-drafts', { method: 'POST', headers })
console.log(`${requestedDraftId ? 'Resuming' : 'Created'} retained draft ${draft.id}.`)

let savedDraft = await request(`/api/paper-submission-drafts/${draft.id}`, {
  method: 'PATCH',
  headers: jsonHeaders,
  body: JSON.stringify({
    version: draft.version,
    currentSection: 'article-content',
    formData: payload.formData,
  }),
})

const contentTypes = {
  '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  '.txt': 'text/plain',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
}
const uploadedIds = new Map()
const existingFiles = new Map((savedDraft.files || [])
  .filter((file) => file.uploadStatus === 'UPLOADED')
  .map((file) => [`${file.role}:${file.originalFileName}`, file]))

for (const descriptor of payload.files) {
  const localPath = descriptor.generated
    ? join(generatedDir, descriptor.path)
    : join(generatedDir, 'files', descriptor.sourceKey, basename(descriptor.path))
  const bytes = readFileSync(localPath)
  const existing = existingFiles.get(`${descriptor.role}:${basename(localPath)}`)
  if (existing) {
    uploadedIds.set(descriptor.sourceKey, existing.id)
    console.log(`Kept existing ${descriptor.role}: ${basename(localPath)}`)
    continue
  }
  const presign = await request(`/api/paper-submission-drafts/${draft.id}/files/presign`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({
      fileName: basename(localPath),
      displayName: basename(localPath),
      contentType: contentTypes[extname(localPath).toLowerCase()] || 'application/octet-stream',
      fileSize: bytes.length,
      role: descriptor.role,
      description: descriptor.description || null,
      visibility: descriptor.visibility,
    }),
  })
  const uploadResponse = await fetch(presign.uploadUrl, {
    method: 'PUT',
    headers: presign.uploadHeaders || {},
    body: bytes,
  })
  if (!uploadResponse.ok) throw new Error(`Upload ${descriptor.sourceKey} failed (${uploadResponse.status}).`)
  await request(`/api/paper-submission-drafts/${draft.id}/files/${presign.fileId}`, {
    method: 'PATCH',
    headers: jsonHeaders,
    body: JSON.stringify({ uploadStatus: 'UPLOADED' }),
  })
  uploadedIds.set(descriptor.sourceKey, presign.fileId)
  console.log(`Uploaded ${descriptor.role}: ${basename(localPath)}`)
}

const article = structuredClone(payload.articleTemplate)
const currentArticle = await request(`/api/paper-submission-drafts/${draft.id}/article`, { headers })
article.version = currentArticle.version
for (const block of article.sections.flatMap((section) => section.blocks)) {
  if (block.type !== 'FIGURE') continue
  block.fileId = uploadedIds.get(block.sourceKey)
  delete block.sourceKey
}

let savedArticle = await request(`/api/paper-submission-drafts/${draft.id}/article`, {
  method: 'PUT',
  headers: jsonHeaders,
  body: JSON.stringify(article),
})
const articleValidation = await request(`/api/paper-submission-drafts/${draft.id}/article/validate`, {
  method: 'POST', headers,
})
if (!articleValidation.valid) throw new Error(`Article validation failed: ${JSON.stringify(articleValidation.issues)}`)

savedArticle = await request(`/api/paper-submission-drafts/${draft.id}/article/ready`, {
  method: 'POST',
  headers: jsonHeaders,
  body: JSON.stringify(savedArticle),
})
const validation = await request(`/api/paper-submission-drafts/${draft.id}/validate`, {
  method: 'POST', headers,
})
if (!validation.valid) throw new Error(`Submission validation failed: ${JSON.stringify(validation.issues)}`)

savedDraft = await request(`/api/paper-submission-drafts/${draft.id}`, { headers })
const result = await request(`/api/paper-submission-drafts/${draft.id}/submit`, {
  method: 'POST',
  headers: jsonHeaders,
  body: JSON.stringify({
    version: savedDraft.version,
    idempotencyKey: `paper01-${randomUUID()}`,
    metadataMatchesManuscript: true,
    correspondingAuthorInformationConfirmed: true,
    publicDisplayConfirmed: true,
  }),
})

const retained = {
  draftId: draft.id,
  paperId: result.paperId,
  postId: result.postId,
  publicationStatus: result.publicationStatus,
  screeningStatus: result.screeningStatus,
  submittedAt: new Date().toISOString(),
}
writeFileSync(statePath, `${JSON.stringify(retained, null, 2)}\n`, 'utf8')
console.log(`Submitted and retained paper ${result.paperId}.`)
console.log(`${process.env.OPENISLE_WEB_URL || 'http://localhost:3000'}/papers/${result.paperId}`)
