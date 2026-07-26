import { getToken } from '~/utils/auth'

export const useDraftFileObjectUrls = (draftId) => {
  const api = usePaperApi()
  const urls = reactive(new Map())
  const pending = new Set()

  const load = async (fileId) => {
    if (!fileId || urls.has(fileId) || pending.has(fileId)) return
    pending.add(fileId)
    try {
      const token = getToken()
      const response = await fetch(api.draftFileContentUrl(draftId, fileId, true), {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!response.ok) throw new Error(`Unable to open figure (${response.status})`)
      urls.set(fileId, URL.createObjectURL(await response.blob()))
    } finally {
      pending.delete(fileId)
    }
  }

  const source = (fileId) => {
    if (!fileId) return ''
    if (!urls.has(fileId)) load(fileId).catch(() => {})
    return urls.get(fileId) || ''
  }

  onBeforeUnmount(() => {
    urls.forEach((url) => URL.revokeObjectURL(url))
    urls.clear()
  })

  return { source }
}
