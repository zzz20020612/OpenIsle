import { createArticleBlock, createArticleSection } from '~/config/paperArticleConfig'

const cleanText = (value = '') => String(value).replace(/\u00a0/g, ' ').replace(/[ \t]+/g, ' ').trim()
const isFigureCaption = (value) => /^(?:fig(?:ure)?\.?\s*\d+\.?)/i.test(value)
const children = (node, name) => [...(node?.children || [])].filter((child) => child.localName === name)
const child = (node, name) => children(node, name)[0]

const ommlToLatex = (node) => {
  if (!node) return ''
  const value = (name) => ommlToLatex(child(node, name))
  switch (node.localName) {
    case 't': return node.textContent || ''
    case 'f': return `\\frac{${value('num')}}{${value('den')}}`
    case 'sSup': return `{${value('e')}}^{${value('sup')}}`
    case 'sSub': return `{${value('e')}}_{${value('sub')}}`
    case 'sSubSup': return `{${value('e')}}_{${value('sub')}}^{${value('sup')}}`
    case 'rad': {
      const degree = value('deg')
      return degree ? `\\sqrt[${degree}]{${value('e')}}` : `\\sqrt{${value('e')}}`
    }
    case 'd': {
      const content = value('e')
      return `\\left(${content}\\right)`
    }
    case 'nary': return `${value('sub') ? `_{${value('sub')}}` : ''}${value('sup') ? `^{${value('sup')}}` : ''}${value('e')}`
    default: return [...(node.children || [])].map(ommlToLatex).join('')
  }
}

const readOmmlEquations = async (arrayBuffer) => {
  const { default: JSZip } = await import('jszip')
  const zip = await JSZip.loadAsync(arrayBuffer)
  const documentXml = await zip.file('word/document.xml')?.async('string')
  if (!documentXml) return []
  const xml = new DOMParser().parseFromString(documentXml, 'application/xml')
  const paragraphs = [...xml.getElementsByTagNameNS('*', 'p')]
  const equations = []
  let previousText = ''
  for (const paragraph of paragraphs) {
    const wordText = [...paragraph.getElementsByTagNameNS('*', 't')]
      .filter((item) => item.namespaceURI?.includes('wordprocessingml'))
      .map((item) => item.textContent || '').join('')
    const formulaNodes = [...paragraph.getElementsByTagNameNS('*', 'oMath')]
      .filter((formula) => formula.parentElement?.localName !== 'oMath')
    const displayFormulas = formulaNodes.filter((formula) => {
      let parent = formula.parentElement
      while (parent && parent !== paragraph) {
        if (parent.localName === 'oMathPara') return true
        parent = parent.parentElement
      }
      return false
    })
    for (const formula of displayFormulas) {
      const latex = cleanText(ommlToLatex(formula))
      if (latex) equations.push({ anchor: cleanText(wordText) || previousText, latex, display: true, inserted: false })
    }
    if (formulaNodes.length > displayFormulas.length) {
      const inlineText = cleanText((() => {
        const walk = (node) => {
          if (node.localName === 'oMath') return `$${cleanText(ommlToLatex(node))}$`
          if (node.localName === 't' && node.namespaceURI?.includes('wordprocessingml')) return node.textContent || ''
          return [...(node.children || [])].map(walk).join('')
        }
        return walk(paragraph)
      })())
      if (inlineText) {
        equations.push({ anchor: cleanText(wordText), replacement: inlineText, display: false, inserted: false })
      }
    }
    if (cleanText(wordText)) previousText = cleanText(wordText)
  }
  return equations
}

export const useDocxArticleImport = () => {
  const importing = ref(false)
  const progress = ref('')

  const importDocx = async (file, uploadFigure) => {
    if (!file?.name?.toLowerCase().endsWith('.docx')) {
      throw new Error('Select a DOCX manuscript file.')
    }

    importing.value = true
    progress.value = 'Reading DOCX...'
    try {
      const { default: mammoth } = await import('mammoth')
      const arrayBuffer = await file.arrayBuffer()
      const equations = await readOmmlEquations(arrayBuffer)
      const extractedImages = []
      const result = await mammoth.convertToHtml(
        { arrayBuffer },
        {
          convertImage: mammoth.images.imgElement(async (image) => {
            const index = extractedImages.length
            const contentType = image.contentType || 'image/png'
            const extension = contentType.includes('jpeg') ? 'jpg' : (contentType.split('/')[1] || 'png')
            const bytes = Uint8Array.from(atob(await image.read('base64')), (char) => char.charCodeAt(0))
            extractedImages.push(new File([bytes], `docx-figure-${index + 1}.${extension}`, { type: contentType }))
            return { src: `docx-figure-${index}` }
          }),
        },
      )

      const document = new DOMParser().parseFromString(result.value, 'text/html')
      const sections = []
      const uploadedFigures = new Map()
      let currentSection = null
      let bodyStarted = false
      let pendingFigure = null

      const addSection = (heading, level) => {
        const normalizedLevel = Math.min(Math.max(level, 1), 3)
        const parent = [...sections].reverse().find((section) => section.level < normalizedLevel)
        const section = createArticleSection(heading, normalizedLevel)
        section.parentKey = parent?.key || null
        section.displayOrder = sections.length
        section.blocks = []
        sections.push(section)
        currentSection = section
        bodyStarted = true
        pendingFigure = null
        return section
      }

      const ensureSection = () => currentSection || addSection('Manuscript', 1)
      const addBlock = (block) => {
        const section = ensureSection()
        block.displayOrder = section.blocks.length
        section.blocks.push(block)
        return block
      }

      const appendAnchoredEquations = (paragraphText) => {
        const normalized = cleanText(paragraphText)
        for (const equation of equations) {
          if (equation.inserted || !equation.display || !equation.anchor) continue
          const anchor = cleanText(equation.anchor)
          if (normalized !== anchor && !normalized.includes(anchor) && !anchor.includes(normalized)) continue
          const block = createArticleBlock('EQUATION')
          block.latex = equation.latex
          block.numbered = true
          addBlock(block)
          equation.inserted = true
        }
      }

      const restoreInlineEquations = (paragraphText) => {
        const normalized = cleanText(paragraphText)
        const match = equations.find((equation) => {
          if (equation.inserted || equation.display || !equation.anchor) return false
          const anchor = cleanText(equation.anchor)
          return normalized === anchor || normalized.includes(anchor) || anchor.includes(normalized)
        })
        if (!match) return normalized
        match.inserted = true
        return match.replacement || normalized
      }

      const uploadImage = async (imageElement) => {
        const rawSource = imageElement.getAttribute('src') || ''
        const match = rawSource.match(/docx-figure-(\d+)/)
        if (!match) return null
        const imageIndex = Number(match[1])
        if (!uploadedFigures.has(imageIndex)) {
          progress.value = `Uploading figure ${imageIndex + 1} of ${extractedImages.length}...`
          uploadedFigures.set(imageIndex, await uploadFigure(extractedImages[imageIndex], imageIndex))
        }
        const uploaded = uploadedFigures.get(imageIndex)
        const fallback = cleanText(imageElement.getAttribute('alt')) || `Figure imported from the manuscript (${imageIndex + 1}).`
        const block = createArticleBlock('FIGURE')
        block.fileId = uploaded.id
        block.caption = fallback
        block.altText = fallback
        pendingFigure = addBlock(block)
        return block
      }

      const nodes = [...document.body.children]
      for (const element of nodes) {
        const headingMatch = element.tagName.match(/^H([1-3])$/)
        if (headingMatch) {
          addSection(cleanText(element.textContent) || 'Untitled Section', Number(headingMatch[1]))
          continue
        }

        // Front matter is already captured in the submission metadata fields.
        if (!bodyStarted) continue

        if (element.tagName === 'TABLE') {
          const matrix = [...element.querySelectorAll('tr')].map((row) =>
            [...row.querySelectorAll('th,td')].map((cell) => cleanText(cell.textContent)),
          ).filter((row) => row.some(Boolean))
          if (matrix.length >= 2) {
            const block = createArticleBlock('TABLE')
            block.caption = 'Table imported from the manuscript.'
            block.columns = matrix[0]
            block.rows = matrix.slice(1)
            addBlock(block)
          }
          pendingFigure = null
          continue
        }

        const images = [...element.querySelectorAll('img')]
        if (images.length) {
          for (const image of images) await uploadImage(image)
          continue
        }

        const math = element.querySelector('math')
        if (math) {
          const block = createArticleBlock('EQUATION')
          block.latex = cleanText(math.getAttribute('alttext')) || cleanText(math.textContent)
          block.numbered = true
          if (block.latex) addBlock(block)
          pendingFigure = null
          continue
        }

        const text = cleanText(element.textContent)
        if (!text) continue
        if (pendingFigure && isFigureCaption(text)) {
          pendingFigure.caption = text.replace(/^(?:fig(?:ure)?\.?\s*\d+\.?\s*)/i, '') || text
          pendingFigure.altText = pendingFigure.caption
          pendingFigure = null
          continue
        }
        const block = createArticleBlock('PARAGRAPH')
        block.text = restoreInlineEquations(text)
        addBlock(block)
        appendAnchoredEquations(text)
        pendingFigure = null
      }

      for (const equation of equations.filter((item) => !item.inserted)) {
        const block = createArticleBlock(equation.display ? 'EQUATION' : 'PARAGRAPH')
        if (equation.display) {
          block.latex = equation.latex
          block.numbered = true
        } else {
          block.text = equation.replacement
        }
        addBlock(block)
        equation.inserted = true
      }

      if (!sections.length || !sections.some((section) => section.blocks.length)) {
        throw new Error('No structured article content could be read from this DOCX file.')
      }
      sections.forEach((section, sectionOrder) => {
        section.displayOrder = sectionOrder
        section.blocks.forEach((block, blockOrder) => { block.displayOrder = blockOrder })
      })

      const displayEquationCount = equations.filter((item) => item.display).length
      const inlineEquationCount = equations.filter((item) => !item.display).length
      progress.value = `Imported ${sections.length} sections, ${uploadedFigures.size} figures, ${displayEquationCount} display equations, and ${inlineEquationCount} paragraphs with inline math.`
      return {
        sections,
        messages: result.messages || [],
        figureCount: uploadedFigures.size,
        equationCount: displayEquationCount,
        inlineMathParagraphCount: inlineEquationCount,
      }
    } finally {
      importing.value = false
    }
  }

  return { importing, progress, importDocx }
}
