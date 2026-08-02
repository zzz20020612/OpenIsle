const trimmed = (value) => (typeof value === 'string' ? value.trim() : '')

export const draftDisplayTitle = (draft) =>
  trimmed(draft?.displayName) ||
  trimmed(draft?.manuscriptTitle) ||
  trimmed(draft?.formData?.title) ||
  trimmed(draft?.primaryManuscriptFileName) ||
  trimmed(draft?.files?.find((file) => file?.role === 'MANUSCRIPT')?.originalFileName) ||
  'Untitled submission'

export const draftSourceLabel = (draft) => {
  if (draft?.revisionSourcePaperId) {
    return `Revision of ${trimmed(draft.revisionSourcePaperTitle) || `Paper #${draft.revisionSourcePaperId}`}`
  }
  const fileName = trimmed(draft?.primaryManuscriptFileName) ||
    trimmed(draft?.files?.find((file) => file?.role === 'MANUSCRIPT')?.originalFileName)
  if (fileName && fileName !== draftDisplayTitle(draft)) return fileName
  const fileCount = Number(draft?.fileCount ?? draft?.files?.length ?? 0)
  return fileCount ? `${fileCount} uploaded file${fileCount === 1 ? '' : 's'}` : 'New submission'
}

export const partitionDraftsByAge = (drafts = []) => ({
  recent: drafts.filter((draft) => !draft?.stale),
  older: drafts.filter((draft) => draft?.stale),
})
