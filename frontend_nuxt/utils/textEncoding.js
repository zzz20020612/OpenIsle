const WINDOWS_1252_BYTES = new Map([
  ['€', 0x80], ['‚', 0x82], ['ƒ', 0x83], ['„', 0x84], ['…', 0x85],
  ['†', 0x86], ['‡', 0x87], ['ˆ', 0x88], ['‰', 0x89], ['Š', 0x8a],
  ['‹', 0x8b], ['Œ', 0x8c], ['Ž', 0x8e], ['‘', 0x91], ['’', 0x92],
  ['“', 0x93], ['”', 0x94], ['•', 0x95], ['–', 0x96], ['—', 0x97],
  ['˜', 0x98], ['™', 0x99], ['š', 0x9a], ['›', 0x9b], ['œ', 0x9c],
  ['ž', 0x9e], ['Ÿ', 0x9f],
])

const MOJIBAKE_MARKERS = /(?:Ã.|Â.|â[\u0080-\u00bf€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•–—˜™š›œžŸ]{1,2}|ð[\u0080-\u00bf])/g

const markerCount = (value) => (String(value).match(MOJIBAKE_MARKERS) || []).length

const toLegacyByte = (character) => {
  const codePoint = character.codePointAt(0)
  if (codePoint <= 0xff) return codePoint
  return WINDOWS_1252_BYTES.get(character)
}

export const repairMojibake = (value) => {
  if (typeof value !== 'string' || markerCount(value) === 0) return value

  const bytes = []
  for (const character of value) {
    const byte = toLegacyByte(character)
    if (byte == null) return value
    bytes.push(byte)
  }

  const decoded = new TextDecoder('utf-8', { fatal: false }).decode(Uint8Array.from(bytes))
  if (decoded.includes('\uFFFD') || markerCount(decoded) >= markerCount(value)) return value
  return decoded
}

export const repairMojibakeDeep = (value) => {
  if (typeof value === 'string') return repairMojibake(value)
  if (Array.isArray(value)) return value.map(repairMojibakeDeep)
  if (!value || typeof value !== 'object') return value
  return Object.fromEntries(
    Object.entries(value).map(([key, nestedValue]) => [key, repairMojibakeDeep(nestedValue)]),
  )
}
