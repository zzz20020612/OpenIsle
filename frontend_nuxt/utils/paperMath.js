const LEGACY_MATH_REPLACEMENTS = [
  ['Î¸', '\\theta'],
  ['Î»', '\\lambda'],
  ['â', '-'],
  ['â', '\\in '],
  ['â', '\\quad '],
  ['â', ''],
  ['\u2212', '-'],
  ['\u2208', '\\in '],
  ['\u2001', '\\quad '],
  ['\u200b', ''],
]

export const escapeHtml = (value = '') => String(value)
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#039;')

export const normalizeLatex = (value = '', { stripEquationNumber = false } = {}) => {
  let latex = String(value).trim()

  if (latex.startsWith('$$') && latex.endsWith('$$')) {
    latex = latex.slice(2, -2).trim()
  } else if (latex.startsWith('$') && latex.endsWith('$')) {
    latex = latex.slice(1, -1).trim()
  }

  for (const [corrupted, replacement] of LEGACY_MATH_REPLACEMENTS) {
    latex = latex.replaceAll(corrupted, replacement)
  }

  if (stripEquationNumber) {
    latex = latex
      .replace(/(?:\\quad\s*)+\\left\(\d+\\right\)\s*$/, '')
      .replace(/(?:\\quad\s*)+\(\d+\)\s*$/, '')
      .trim()
  }

  return latex
}

export const renderInlineMath = (value = '', renderLatex) => {
  const parts = String(value).split(/(\$[^$\n]+\$)/g)
  return parts
    .map((part) => {
      if (part.startsWith('$') && part.endsWith('$')) {
        const latex = normalizeLatex(part)
        try {
          return renderLatex(latex)
        } catch {
          return `<code>${escapeHtml(latex)}</code>`
        }
      }
      return escapeHtml(part).replaceAll('\n', '<br>')
    })
    .join('')
}
