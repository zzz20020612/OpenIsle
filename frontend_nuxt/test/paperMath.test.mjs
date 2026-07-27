import test from 'node:test'
import assert from 'node:assert/strict'
import katex from 'katex'
import { normalizeLatex, renderInlineMath } from '../utils/paperMath.js'

test('renders inline math before escaping surrounding HTML', () => {
  const html = renderInlineMath(
    'Use $v_{ij} > 0$ and keep <script> escaped.',
    (latex) => `<math>${latex}</math>`,
  )

  assert.equal(
    html,
    'Use <math>v_{ij} > 0</math> and keep &lt;script&gt; escaped.',
  )
})

test('normalizes unambiguous legacy DOCX characters', () => {
  assert.equal(
    normalizeLatex('\\lambda{L}_{reg}\\left(\\theta\\right)\u2001\u2001\\left(4\\right)', {
      stripEquationNumber: true,
    }),
    '\\lambda{L}_{reg}\\left(\\theta\\right)',
  )
  assert.equal(normalizeLatex('{x}\u2208S\u2212{w}'), '{x}\\in S-{w}')
})

test('removes display delimiters without exposing raw dollar signs', () => {
  assert.equal(normalizeLatex('$$x > 0$$'), 'x > 0')
  assert.equal(normalizeLatex('$x > 0$'), 'x > 0')
})

test('keeps invalid imported formula structure for author correction', () => {
  const normalized = normalizeLatex(
    '{h}_{ij}={v}_{ij}_{s}^{\u200b}{y}_{s}\u2001\u2001\\left(2\\right)',
    { stripEquationNumber: true },
  )

  assert.equal(normalized, '{h}_{ij}={v}_{ij}_{s}^{}{y}_{s}')
  assert.throws(() =>
    katex.renderToString(normalized, { displayMode: true, throwOnError: true }),
  )
})
