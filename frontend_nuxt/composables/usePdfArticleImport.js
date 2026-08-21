import { createArticleBlock, createArticleSection } from '~/config/paperArticleConfig'

const cleanText = (value = '') => String(value).replace(/\s+/g, ' ').trim()

export const usePdfArticleImport = (draftId) => {
  const importing = ref(false)
  const progress = ref('')
  const paperApi = usePaperApi()

  const importPdf = async (file) => {
    if (!file?.name?.toLowerCase().endsWith('.pdf')) throw new Error('Select a PDF manuscript file.')
    importing.value = true
    progress.value = 'Parsing PDF with the manuscript extraction service...'
    try {
      const parsed = await paperApi.importDraftPdf(draftId, file)
      const abstractSection = (parsed.sections || []).find((section) => section.section_type === 'abstract')
      const sourceSections = (parsed.sections || []).filter((section) => (
        section.section_type !== 'abstract' && cleanText(section.content)
      ))
      const sections = sourceSections.map((source, sectionOrder) => {
        const section = createArticleSection(cleanText(source.heading) || `Section ${sectionOrder + 1}`, 1)
        section.displayOrder = sectionOrder
        section.blocks = []
        String(source.content || '').split(/\n\s*\n/).map(cleanText).filter(Boolean).forEach((text, blockOrder) => {
          const block = createArticleBlock('PARAGRAPH')
          block.text = text
          block.displayOrder = blockOrder
          section.blocks.push(block)
        })
        return section
      })
      if (!sections.length) throw new Error('No editable article text could be extracted from this PDF.')

      progress.value = `Imported ${sections.length} sections from ${parsed.page_count || 0} PDF pages using ${parsed.parser_used || 'the PDF parser'}. Review equations, complex tables, figures, and reading order before submission.`
      return {
        sections,
        pageCount: parsed.page_count || 0,
        characterCount: parsed.char_count || 0,
        parserUsed: parsed.parser_used || '',
        metadata: {
          title: cleanText(parsed.title),
          authors: Array.isArray(parsed.authors) ? parsed.authors.map(cleanText).filter(Boolean) : [],
          keywords: Array.isArray(parsed.keywords) ? parsed.keywords.map(cleanText).filter(Boolean) : [],
          abstractText: cleanText(abstractSection?.content),
        },
      }
    } catch (error) {
      progress.value = 'Import failed. Your existing article was kept unchanged.'
      throw error
    } finally {
      importing.value = false
    }
  }

  return { importing, progress, importPdf }
}
