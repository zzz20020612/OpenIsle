import { createArticleBlock, createArticleSection } from '~/config/paperArticleConfig'
import pdfWorkerUrl from 'pdfjs-dist/legacy/build/pdf.worker.min.mjs?url'

const cleanText = (value = '') => String(value).replace(/\s+/g, ' ').trim()
const headingPattern = /^(abstract|introduction|background|methods?|materials? and methods?|results?|discussion|conclusions?|acknowledg(?:e)?ments?|references)$/i

export const usePdfArticleImport = () => {
  const importing = ref(false)
  const progress = ref('')

  const importPdf = async (file) => {
    if (!file?.name?.toLowerCase().endsWith('.pdf')) throw new Error('Select a PDF manuscript file.')
    importing.value = true
    progress.value = 'Reading PDF...'
    try {
      const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs')
      pdfjs.GlobalWorkerOptions.workerSrc = pdfWorkerUrl
      const bytes = new Uint8Array(await file.arrayBuffer())
      const pdf = await pdfjs.getDocument({ data: bytes }).promise
      const lines = []
      let itemCount = 0
      let usedOcr = false

      for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
        progress.value = `Reading page ${pageNumber} of ${pdf.numPages}...`
        const page = await pdf.getPage(pageNumber)
        const content = await page.getTextContent()
        itemCount += content.items.length
        const ordered = [...content.items].sort((a, b) => {
          const y = Number(b.transform?.[5] || 0) - Number(a.transform?.[5] || 0)
          return Math.abs(y) > 2 ? y : Number(a.transform?.[4] || 0) - Number(b.transform?.[4] || 0)
        })
        let current = null
        for (const item of ordered) {
          const text = cleanText(item.str)
          if (!text) continue
          const y = Number(item.transform?.[5] || 0)
          const size = Math.abs(Number(item.transform?.[0] || item.height || 0))
          if (!current || Math.abs(current.y - y) > Math.max(2.5, size * 0.35)) {
            current = { text, y, size, page: pageNumber }
            lines.push(current)
          } else {
            current.text = cleanText(`${current.text} ${text}`)
            current.size = Math.max(current.size, size)
          }
        }
      }

      const readable = lines.filter((line) => line.text.length > 1)
      let characterCount = readable.reduce((total, line) => total + line.text.length, 0)
      if (itemCount === 0 || characterCount < Math.max(120, pdf.numPages * 40)) {
        usedOcr = true
        lines.length = 0
        const { createWorker } = await import('tesseract.js')
        progress.value = 'Preparing OCR for this scanned PDF...'
        const worker = await createWorker('eng', 1, {
          logger: (message) => {
            if (message.status === 'recognizing text') {
              progress.value = `Running OCR... ${Math.round((message.progress || 0) * 100)}%`
            }
          },
        })
        try {
          for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
            progress.value = `Running OCR on page ${pageNumber} of ${pdf.numPages}...`
            const page = await pdf.getPage(pageNumber)
            const viewport = page.getViewport({ scale: 2 })
            const canvas = document.createElement('canvas')
            canvas.width = Math.ceil(viewport.width)
            canvas.height = Math.ceil(viewport.height)
            const context = canvas.getContext('2d', { alpha: false })
            await page.render({ canvasContext: context, viewport }).promise
            const result = await worker.recognize(canvas)
            String(result.data.text || '').split(/\r?\n/).forEach((value) => {
              const text = cleanText(value)
              if (text.length > 1) lines.push({ text, y: 0, size: 10, page: pageNumber })
            })
            canvas.width = 1
            canvas.height = 1
          }
        } finally {
          await worker.terminate()
        }
        characterCount = lines.reduce((total, line) => total + line.text.length, 0)
        if (characterCount < Math.max(40, pdf.numPages * 15)) {
          throw new Error('OCR could not find enough readable manuscript text in this PDF. Try a clearer scan or enter the article content manually.')
        }
      }

      const extractedLines = lines.filter((line) => line.text.length > 1)
      const bodySizes = extractedLines.map((line) => line.size).filter(Boolean).sort((a, b) => a - b)
      const bodySize = bodySizes[Math.floor(bodySizes.length / 2)] || 10
      const sections = []
      let section = null
      const addSection = (heading) => {
        section = createArticleSection(heading || 'Manuscript', 1)
        section.blocks = []
        section.displayOrder = sections.length
        sections.push(section)
      }
      const addParagraph = (text) => {
        if (!section) addSection('Manuscript')
        const previous = section.blocks.at(-1)
        if (previous?.type === 'PARAGRAPH' && !/[.!?:;]$/.test(previous.text) && text.length < 160) {
          previous.text = cleanText(`${previous.text} ${text}`)
          return
        }
        const block = createArticleBlock('PARAGRAPH')
        block.text = text
        block.displayOrder = section.blocks.length
        section.blocks.push(block)
      }

      for (const line of extractedLines) {
        const likelyHeading = headingPattern.test(line.text) || (line.size >= bodySize * 1.25 && line.text.length <= 100)
        if (likelyHeading) addSection(line.text)
        else addParagraph(line.text)
      }
      const populated = sections.filter((item) => item.blocks.length)
      if (!populated.length) throw new Error('No editable article text could be extracted from this PDF.')
      populated.forEach((item, sectionOrder) => {
        item.displayOrder = sectionOrder
        item.blocks.forEach((block, blockOrder) => { block.displayOrder = blockOrder })
      })
      progress.value = `${usedOcr ? 'OCR imported' : 'Imported'} ${populated.length} sections from ${pdf.numPages} PDF pages. Review headings, equations, complex tables, and two-column reading order before submission.`
      return { sections: populated, pageCount: pdf.numPages, characterCount, usedOcr }
    } catch (error) {
      progress.value = 'Import failed. Your existing article was kept unchanged.'
      throw error
    } finally {
      importing.value = false
    }
  }

  return { importing, progress, importPdf }
}
