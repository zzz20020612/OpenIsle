export const useSubmissionScrollspy = (sectionIds) => {
  const activeSection = ref(sectionIds[0] || '')
  let observer = null

  const start = () => {
    if (!process.client || typeof IntersectionObserver === 'undefined') return
    observer?.disconnect()
    observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((left, right) => {
            const topDelta = Math.abs(left.boundingClientRect.top) - Math.abs(right.boundingClientRect.top)
            return topDelta || right.intersectionRatio - left.intersectionRatio
          })
        if (visible[0]?.target?.id) {
          activeSection.value = visible[0].target.id
        }
      },
      { rootMargin: '-96px 0px -62% 0px', threshold: [0, 0.15, 0.4, 0.75] },
    )
    sectionIds.forEach((id) => {
      const element = document.getElementById(id)
      if (element) observer.observe(element)
    })
  }

  const scrollTo = (sectionId) => {
    const element = document.getElementById(sectionId)
    if (!element) return
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    element.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' })
    activeSection.value = sectionId
  }

  onBeforeUnmount(() => observer?.disconnect())

  return { activeSection, start, scrollTo }
}
