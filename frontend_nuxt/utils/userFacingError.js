const readableMessage = (value) =>
  typeof value === 'string' && value.trim() ? value.trim() : ''

export const toUserFacingError = (cause, fallback) => {
  const candidates = [
    cause?.data?.error,
    cause?.data?.message,
    cause?.error,
    cause?.message,
  ]
  return candidates.map(readableMessage).find(Boolean) || fallback
}
