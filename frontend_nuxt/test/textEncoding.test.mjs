import test from 'node:test'
import assert from 'node:assert/strict'
import { repairMojibake, repairMojibakeDeep } from '../utils/textEncoding.js'

test('repairs common UTF-8 text decoded as Windows-1252', () => {
  assert.equal(repairMojibake('modelâ€™s objective'), 'model’s objective')
  assert.equal(repairMojibake('500 m Ã— 500 m'), '500 m × 500 m')
  assert.equal(repairMojibake('25Â°36â€² N'), '25°36′ N')
  assert.equal(repairMojibake('dataâ€”specifically'), 'data—specifically')
})

test('leaves valid English, Chinese, formulae, and URLs unchanged', () => {
  const values = [
    'Open research infrastructure',
    '知识提取结果可以保留中文。',
    'X_ij = V_ij / Σ V_ij',
    'https://doi.org/10.1000/example',
  ]
  values.forEach((value) => assert.equal(repairMojibake(value), value))
})

test('repairs nested article and comment payloads without mutation', () => {
  const source = { heading: 'Methods', blocks: [{ text: '500 m Ã— 500 m' }] }
  const repaired = repairMojibakeDeep(source)
  assert.equal(repaired.blocks[0].text, '500 m × 500 m')
  assert.equal(source.blocks[0].text, '500 m Ã— 500 m')
})
