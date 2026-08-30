import { reactive } from 'vue'
import { toast } from '~/main'

export const ThemeMode = {
  SYSTEM: 'system',
  LIGHT: 'light',
  DARK: 'dark',
}

const THEME_KEY = 'theme-mode'

export const themeState = reactive({
  mode: ThemeMode.SYSTEM,
})

function apply(mode) {
  if (!import.meta.client) return
  const root = document.documentElement
  let newMode =
    mode === ThemeMode.SYSTEM
      ? window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light'
      : mode
  if (root.dataset.theme === newMode) return
  root.dataset.theme = newMode

  // 更新 meta 标签
  const androidMeta = document.querySelector('meta[name="theme-color"]')
  const iosMeta = document.querySelector('meta[name="apple-mobile-web-app-status-bar-style"]')
  const themeColor = getComputedStyle(document.documentElement)
    .getPropertyValue('--background-color')
    .trim()
  const themeStatus = newMode === 'dark' ? 'black-translucent' : 'default'

  if (androidMeta) {
    androidMeta.content = themeColor
  } else {
    const newAndroidMeta = document.createElement('meta')
    newAndroidMeta.name = 'theme-color'
    newAndroidMeta.content = themeColor
    document.head.appendChild(newAndroidMeta)
  }

  if (iosMeta) {
    iosMeta.content = themeStatus
  } else {
    const newIosMeta = document.createElement('meta')
    newIosMeta.name = 'apple-mobile-web-app-status-bar-style'
    newIosMeta.content = themeStatus
    document.head.appendChild(newIosMeta)
  }
}

export function initTheme() {
  if (!import.meta.client) return
  const saved = localStorage.getItem(THEME_KEY)
  if (saved && Object.values(ThemeMode).includes(saved)) {
    themeState.mode = saved
  }
  apply(themeState.mode)
}

export function setTheme(mode) {
  if (!import.meta.client) return
  if (!Object.values(ThemeMode).includes(mode)) return
  themeState.mode = mode
  localStorage.setItem(THEME_KEY, mode)
  apply(mode)
}

function getCircle(event) {
  if (!import.meta.client) return undefined

  let x, y
  if (event.touches?.length) {
    x = event.touches[0].clientX
    y = event.touches[0].clientY
  } else if (event.changedTouches?.length) {
    x = event.changedTouches[0].clientX
    y = event.changedTouches[0].clientY
  } else {
    x = event.clientX
    y = event.clientY
  }

  return {
    x,
    y,
    radius: Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y)),
  }
}

function withViewTransition(event, applyFn, direction = true) {
  if (typeof document !== 'undefined' && document.startViewTransition) {
    const transition = document.startViewTransition(() => {
      applyFn()
    })

    transition.ready
      .then(() => {
        const { x, y, radius } = getCircle(event)

        const clipPath = [`circle(0 at ${x}px ${y}px)`, `circle(${radius}px at ${x}px ${y}px)`]

        document.documentElement.animate(
          {
            clipPath: direction ? clipPath : [...clipPath].reverse(),
          },
          {
            duration: 400,
            easing: 'ease-in-out',
            fill: 'both',
            pseudoElement: direction
              ? '::view-transition-new(root)'
              : '::view-transition-old(root)',
          },
        )
      })
      .catch(console.warn)
  } else {
    fallbackThemeTransition(applyFn)
  }
}

function fallbackThemeTransition(applyFn) {
  if (!import.meta.client) return

  const root = document.documentElement
  const computedStyle = getComputedStyle(root)

  // 获取当前背景色用于过渡
  const currentBg = computedStyle.getPropertyValue('--background-color').trim()

  // 创建过渡元素
  const transitionElement = document.createElement('div')
  transitionElement.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: ${currentBg};
    z-index: 9999;
    pointer-events: none;
    backdrop-filter: var(--blur-1);
  `
  document.body.appendChild(transitionElement)

  // 使用 Web Animations API 实现淡出动画
  const animation = transitionElement.animate([{ opacity: 1 }, { opacity: 0 }], {
    duration: 300,
    easing: 'ease-out',
  })

  // 应用主题变更
  applyFn()

  // 动画完成后清理
  animation.finished
    .then(() => {
      document.body.removeChild(transitionElement)
    })
    .catch(() => {
      // 降级处理
      document.body.removeChild(transitionElement)
    })
}

function getSystemTheme() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function cycleTheme(event) {
  if (!import.meta.client) return
  const modes = [ThemeMode.SYSTEM, ThemeMode.LIGHT, ThemeMode.DARK]
  const index = modes.indexOf(themeState.mode)
  const next = modes[(index + 1) % modes.length]
  if (next === ThemeMode.SYSTEM) {
    toast.success('Using the system theme.')
  } else if (next === ThemeMode.LIGHT) {
    toast.success('Light theme enabled.')
  } else {
    toast.success('Dark theme enabled.')
  }
  // 获取当前真实主题
  const currentTheme = themeState.mode === ThemeMode.SYSTEM ? getSystemTheme() : themeState.mode

  // 获取新主题的真实表现
  const nextTheme = next === ThemeMode.SYSTEM ? getSystemTheme() : next

  // 如果新旧主题相同，不用过渡动画
  if (currentTheme === nextTheme) {
    setTheme(next)
    return
  }

  // 计算新主题是否是暗色
  const newThemeIsDark = nextTheme === 'dark'

  withViewTransition(
    event,
    () => {
      setTheme(next)
    },
    !newThemeIsDark,
  )
}

if (import.meta.client && window.matchMedia) {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (themeState.mode === ThemeMode.SYSTEM) {
      apply(ThemeMode.SYSTEM)
    }
  })
}
