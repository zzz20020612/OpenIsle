export const medalTitles = {
  COMMENT: 'Active Commenter',
  POST: 'Active Publisher',
  FEATURED: 'Featured Author',
  SEED: 'Seed Member',
  CONTRIBUTOR: 'Contributor',
  PIONEER: 'Pioneer Member',
}

export function getMedalTitle(type) {
  return medalTitles[type] || ''
}
