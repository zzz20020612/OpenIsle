export const cleanupImportedDraftFiles = async (fileIds = [], removeFile) => {
  const uniqueIds = [...new Set(fileIds.filter(Boolean))]
  const results = await Promise.allSettled(uniqueIds.map((fileId) => removeFile(fileId)))
  return results.reduce((failedIds, result, index) => {
    if (result.status === 'rejected') failedIds.push(uniqueIds[index])
    return failedIds
  }, [])
}
