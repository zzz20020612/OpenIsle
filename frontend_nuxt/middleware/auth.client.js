import { getToken } from '~/utils/auth'

export default defineNuxtRouteMiddleware((to) => {
  if (import.meta.server) return
  if (getToken()) return
  return navigateTo(
    {
      path: '/login',
      query: { redirect: to.fullPath },
    },
    { replace: true },
  )
})
