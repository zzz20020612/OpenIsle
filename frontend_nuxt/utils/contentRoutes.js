export function resolveContentPath(post, anchor = '') {
  if (!post) return '#'
  const base = post.paperId ? `/papers/${post.paperId}` : `/posts/${post.id}`
  return anchor ? `${base}${anchor}` : base
}

export function resolveCommentPath(post, commentId) {
  if (!commentId) return resolveContentPath(post)
  return resolveContentPath(post, `#comment-${commentId}`)
}
