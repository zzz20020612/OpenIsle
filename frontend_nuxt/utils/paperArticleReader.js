const normalizedHeading = (value = '') => String(value).trim().toLowerCase()

const isDuplicateAbstractCover = (section = {}) => {
  const blocks = section.blocks || []
  return normalizedHeading(section.heading) === 'article' &&
    blocks.length >= 2 &&
    blocks[0]?.type === 'PARAGRAPH' &&
    normalizedHeading(blocks[0]?.text) === 'abstract'
}

export const normalizeReaderArticle = (article = {}) => ({
  ...article,
  sections: (article.sections || []).filter((section) => !isDuplicateAbstractCover(section)),
})
