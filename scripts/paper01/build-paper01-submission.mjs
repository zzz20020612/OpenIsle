import { execFileSync } from 'node:child_process'
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { basename, dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = dirname(fileURLToPath(import.meta.url))
const defaultSource = 'D:/论文/paper01/paper_cnn1d'
const sourceDir = resolve(process.argv[2] || defaultSource)
const outputDir = resolve(process.argv[3] || join(scriptDir, 'generated'))
const qmdPath = join(sourceDir, 'paper_cnn1d_ai.qmd')
const docxPath = join(sourceDir, 'paper_cnn1d_ai.docx')

if (!existsSync(docxPath) || !existsSync(qmdPath)) {
  throw new Error(`Paper source was not found: ${docxPath}`)
}

// DOCX is the authoritative manuscript. QMD is used only as fixture metadata,
// mirroring the title/author fields an author enters in the submission form.
const ast = JSON.parse(execFileSync('quarto', ['pandoc', docxPath, '--to=json'], {
  encoding: 'utf8',
  maxBuffer: 32 * 1024 * 1024,
}))
const metadataAst = JSON.parse(execFileSync('quarto', ['pandoc', qmdPath, '--to=json'], {
  encoding: 'utf8',
  maxBuffer: 32 * 1024 * 1024,
}))

const stringifyInlines = (inlines = []) => inlines.map((inline) => {
  switch (inline.t) {
    case 'Str': return inline.c
    case 'Space': return ' '
    case 'SoftBreak': return ' '
    case 'LineBreak': return '\n'
    case 'Code': return inline.c[1]
    case 'Math': return inline.c[0].t === 'DisplayMath' ? `$$${inline.c[1]}$$` : `$${inline.c[1]}$`
    case 'Strong':
    case 'Emph':
    case 'Strikeout': return stringifyInlines(inline.c)
    case 'Quoted': return stringifyInlines(inline.c[1])
    case 'Cite': return stringifyInlines(inline.c[1])
    case 'Link': return stringifyInlines(inline.c[1])
    case 'Span': return stringifyInlines(inline.c[1])
    case 'Superscript': return `^${stringifyInlines(inline.c)}^`
    case 'Subscript': return `_${stringifyInlines(inline.c)}_`
    default: return ''
  }
}).join('').replace(/\s+([,.;:)])/g, '$1').replace(/([(])\s+/g, '$1').trim()

const metaValue = (node) => {
  if (!node) return null
  switch (node.t) {
    case 'MetaString': return node.c
    case 'MetaBool': return node.c
    case 'MetaInlines': return stringifyInlines(node.c)
    case 'MetaBlocks': return node.c.map(blockText).filter(Boolean).join('\n')
    case 'MetaList': return node.c.map(metaValue)
    case 'MetaMap': return Object.fromEntries(Object.entries(node.c).map(([key, value]) => [key, metaValue(value)]))
    default: return null
  }
}

function blockText(block) {
  if (!block) return ''
  if (block.t === 'Para' || block.t === 'Plain') return stringifyInlines(block.c)
  if (block.t === 'Header') return stringifyInlines(block.c[2])
  if (block.t === 'BlockQuote') return block.c.map(blockText).filter(Boolean).join('\n')
  return ''
}

const metadata = Object.fromEntries(Object.entries(metadataAst.meta).map(([key, value]) => [key, metaValue(value)]))
const figureFiles = new Map()
let figureCounter = 0
let sectionCounter = 0
let blockCounter = 0
let currentSection = null
const sections = []

const stableKey = (prefix, value) => {
  const slug = String(value || '').toLowerCase().normalize('NFKD')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 56)
  return `${prefix}-${slug || (prefix === 'section' ? ++sectionCounter : ++blockCounter)}`
}

const ensureSection = () => {
  if (!currentSection) addSection(1, 'Article')
  return currentSection
}

const addSection = (level, heading) => {
  const parent = [...sections].reverse().find((section) => section.level < level)
  currentSection = {
    key: stableKey('section', `${sections.length + 1}-${heading}`),
    parentKey: parent?.key || null,
    heading,
    level: Math.min(Math.max(level, 1), 3),
    displayOrder: sections.length,
    blocks: [],
  }
  sections.push(currentSection)
}

const addBlock = (type, values = {}) => {
  const section = ensureSection()
  section.blocks.push({
    key: `${type.toLowerCase()}-${++blockCounter}`,
    type,
    displayOrder: section.blocks.length,
    ...values,
  })
}

const imageFromInline = (inline) => {
  if (inline?.t === 'Image') return inline
  if (Array.isArray(inline?.c)) {
    for (const child of inline.c.flat(Infinity)) {
      const image = imageFromInline(child)
      if (image) return image
    }
  }
  return null
}

const processBlock = (block) => {
  if (block.t === 'Header') {
    addSection(block.c[0], stringifyInlines(block.c[2]))
    return
  }
  if (block.t === 'Para' || block.t === 'Plain') {
    const image = block.c.map(imageFromInline).find(Boolean)
    if (image) {
      figureCounter += 1
      const sourceKey = `image${figureCounter}`
      const source = `images/media/${sourceKey}.jpg`
      figureFiles.set(sourceKey, source)
      const rawCaption = stringifyInlines(image.c[1])
      const caption = rawCaption.replace(/^\*\*Fig\.\s*\d+\.\*\*\s*/i, '').trim() || `Figure from ${basename(source)}`
      addBlock('FIGURE', {
        fileId: null,
        sourceKey,
        label: '',
        caption,
        altText: caption,
        sourceNote: '',
      })
      return
    }
    const displayMath = block.c.length === 1 && block.c[0]?.t === 'Math' && block.c[0].c[0].t === 'DisplayMath'
    if (displayMath) {
      addBlock('EQUATION', { latex: block.c[0].c[1], numbered: true })
      return
    }
    const text = stringifyInlines(block.c)
    if (text) addBlock('PARAGRAPH', { text })
    return
  }
  if (block.t === 'Table') {
    const caption = stringifyInlines(block.c[1]?.[1] || []) || 'Article table'
    const headRows = block.c[3]?.[1] || []
    const bodyRows = (block.c[4] || []).flatMap((body) => body[3] || [])
    const cells = (row) => (row?.[1] || []).map((cell) => (cell?.[4] || []).map(blockText).filter(Boolean).join(' '))
    const columns = headRows.length ? cells(headRows[0]) : []
    const rows = bodyRows.map(cells).filter((row) => row.some(Boolean))
    if (columns.length && rows.length) addBlock('TABLE', { caption, columns, rows, notes: '' })
    return
  }
  if (block.t === 'Figure') {
    const caption = stringifyInlines(block.c[1]?.[1] || [])
    const before = figureCounter
    ;(block.c[2] || []).forEach(processBlock)
    if (caption && figureCounter > before) {
      const latest = currentSection?.blocks?.at(-1)
      if (latest?.type === 'FIGURE') {
        latest.caption = caption.replace(/^Fig\.\s*\d+\.\s*/i, '').trim()
        latest.altText = latest.caption
      }
    }
    return
  }
  if (block.t === 'Div' || block.t === 'BlockQuote') {
    const children = block.t === 'Div' ? block.c[1] : block.c
    ;(children || []).forEach(processBlock)
  }
}

for (const block of ast.blocks) {
  processBlock(block)
}

const rawAuthors = Array.isArray(metadata.author) ? metadata.author : []
const authors = rawAuthors.map((author, index) => {
  const displayName = author.name || ''
  const parts = displayName.trim().split(/\s+/)
  const affiliations = (Array.isArray(author.affiliation) ? author.affiliation : [author.affiliation]).filter(Boolean)
  return {
    displayName,
    givenName: parts.slice(0, -1).join(' '),
    middleName: '',
    familyName: parts.at(-1) || '',
    email: author.email || `${parts.join('.').toLowerCase()}@paper01.demo`,
    orcid: '',
    authorRole: author.corresponding ? 'Corresponding Author' : 'Author',
    correspondingAuthor: Boolean(author.corresponding),
    equalContribution: false,
    contributionRoles: [],
    affiliations: affiliations.map((organizationName, affiliationIndex) => ({
      organizationName,
      department: '', addressLine1: '', addressLine2: '', country: 'China',
      region: 'Jiangsu', city: 'Nanjing', postalCode: '', primaryAffiliation: affiliationIndex === 0,
    })),
  }
})

const files = [
  { sourceKey: 'manuscript', role: 'MANUSCRIPT', path: 'paper_cnn1d_ai.docx', visibility: 'PUBLIC', required: true },
  { sourceKey: 'cover-letter', role: 'COVER_LETTER', path: 'cover-letter.txt', visibility: 'PRIVATE', required: true, generated: true },
  { sourceKey: 'supporting-information', role: 'SUPPORTING_INFORMATION', path: 'si.docx', visibility: 'PUBLIC', required: false, description: 'Methods, mathematical proof, and supplementary figures and tables.' },
  { sourceKey: 'toc-graphic', role: 'TOC_GRAPHIC', path: 'images/media/abstract.png', visibility: 'PUBLIC', required: false },
  ...[...figureFiles.entries()].map(([sourceKey, path]) => ({ sourceKey, role: 'FIGURE', path, visibility: 'PUBLIC', required: true })),
]

const references = (readFileSync(join(sourceDir, 'references.bib'), 'utf8').match(/title\s*=\s*[{\"]([^}\"]+)/gi) || [])
  .map((entry) => entry.replace(/^title\s*=\s*[{\"]/i, '').trim())

const payload = {
  schemaVersion: 1,
  source: {
    name: 'paper01',
    manuscript: 'paper_cnn1d_ai.docx',
    metadataSidecar: 'paper_cnn1d_ai.qmd',
  },
  formData: {
    title: metadata.title || '',
    abstractText: metadata.abstract || '',
    subjectArea: 'Environmental Science',
    paperType: 'Research Article',
    keywords: metadata.keywords || [],
    references,
    content: '',
    authors,
    funding: [
      { funderName: 'Key Science and Technology Program of Yunnan Province', awardNumber: '202202AE090034' },
      { funderName: 'State Key Laboratory of Lake and Watershed Science for Water Security', awardNumber: 'NKL2023-QN05' },
    ],
    noFundingReceived: false,
    fundingStatement: 'Key Science and Technology Program of Yunnan Province (202202AE090034); Erhai Academy of Green Development; State Key Laboratory of Lake and Watershed Science for Water Security (NKL2023-QN05).',
    conflictOfInterest: 'The authors declare no known competing financial interests or personal relationships that could have influenced this work.',
    dataAvailability: 'All data generated or analyzed during this study are included in the article and its supporting information.',
    ethicsStatement: 'Not applicable.',
    preprintStatement: 'This manuscript has not been posted as a preprint.',
    aiUseDisclosure: 'AI-assisted language editing was used during manuscript preparation; all scientific content was reviewed and approved by the authors.',
    allAuthorsConsent: true,
    originalityConfirmed: true,
    rightsConfirmed: true,
    correspondingAuthorContactConfirmed: true,
    privateComments: 'Deterministic paper01 end-to-end demonstration submission.',
  },
  articleTemplate: { version: 0, status: 'IN_PROGRESS', readyAt: null, sections },
  files,
}

mkdirSync(outputDir, { recursive: true })
const coverLetter = `Dear Editors,\n\nPlease consider our Research Article, "${payload.formData.title}", for publication. The study presents a physics-constrained deep learning framework for high-resolution pollution-load attribution and demonstrates its application in the Erhai Lake Basin.\n\nAll authors approved this submission. The work is original and is not under consideration elsewhere.\n\nSincerely,\n${authors.find((author) => author.correspondingAuthor)?.displayName || authors[0]?.displayName || 'The authors'}\n`
writeFileSync(join(outputDir, 'cover-letter.txt'), coverLetter, 'utf8')

for (const file of files) {
  if (file.generated) continue
  const source = join(sourceDir, file.path)
  const target = join(outputDir, 'files', file.sourceKey, basename(file.path))
  mkdirSync(dirname(target), { recursive: true })
  copyFileSync(source, target)
}

writeFileSync(join(outputDir, 'paper01-submission.json'), `${JSON.stringify(payload, null, 2)}\n`, 'utf8')
console.log(`Generated ${sections.length} sections, ${sections.reduce((sum, section) => sum + section.blocks.length, 0)} blocks, ${figureFiles.size} figures, and ${authors.length} authors.`)
console.log(join(outputDir, 'paper01-submission.json'))
