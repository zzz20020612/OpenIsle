const numericRevision = (paper) => Math.max(Number(paper?.revisionNumber) || 1, 1)

const resolveRootId = (paper, byId) => {
  if (paper?.revisionRootPaperId) return String(paper.revisionRootPaperId)
  let current = paper
  const visited = new Set()
  while (current?.revisionOfPaperId && !visited.has(String(current.id))) {
    visited.add(String(current.id))
    const parent = byId.get(String(current.revisionOfPaperId))
    if (!parent) return String(current.revisionOfPaperId)
    current = parent
  }
  return String(current?.id ?? paper?.id)
}

export const groupPaperRevisionLineages = (papers = []) => {
  const byId = new Map(papers.map((paper) => [String(paper.id), paper]))
  const groups = new Map()
  for (const paper of papers) {
    const rootId = resolveRootId(paper, byId)
    if (!groups.has(rootId)) groups.set(rootId, [])
    groups.get(rootId).push(paper)
  }
  return [...groups.entries()].map(([rootId, versions]) => {
    const ordered = [...versions].sort((left, right) =>
      numericRevision(left) - numericRevision(right) || Number(left.id) - Number(right.id),
    )
    return {
      rootId,
      root: ordered.find((paper) => String(paper.id) === rootId) || ordered[0],
      latest: ordered[ordered.length - 1],
      versions: ordered,
    }
  }).sort((left, right) => Number(right.latest.id) - Number(left.latest.id))
}
