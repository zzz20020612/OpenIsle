export const ARTICLE_BLOCK_TYPES = [
  { value: 'PARAGRAPH', label: 'Paragraph' },
  { value: 'SUBHEADING', label: 'Subheading' },
  { value: 'FIGURE', label: 'Figure' },
  { value: 'EQUATION', label: 'Equation' },
  { value: 'TABLE', label: 'Table' },
]

export const createArticleBlock = (type = 'PARAGRAPH') => ({
  key: `${type.toLowerCase()}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
  type,
  displayOrder: 0,
  text: type === 'PARAGRAPH' || type === 'SUBHEADING' ? '' : undefined,
  fileId: null,
  label: '',
  caption: '',
  altText: '',
  sourceNote: '',
  latex: '',
  numbered: true,
  columns: [],
  rows: [],
  notes: '',
})

export const createArticleSection = (heading = 'New Section', level = 1) => ({
  key: `section-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
  parentKey: null,
  heading,
  level,
  displayOrder: 0,
  blocks: [createArticleBlock()],
})

export const createEmptyArticle = () => ({
  version: 0,
  status: 'NOT_STARTED',
  readyAt: null,
  sections: [],
})
