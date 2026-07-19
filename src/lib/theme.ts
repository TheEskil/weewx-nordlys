import type { ThemeConfig } from './types'

function cssVars(tokens: Record<string, string>): string {
  return Object.entries(tokens)
    .map(([key, value]) => `--nl-${key}: ${value};`)
    .join(' ')
}

/*
 * Applies the [theme] section of skin.conf. Token overrides are injected
 * as a stylesheet that mirrors the cascade structure of tokens.css, so
 * per-mode overrides win exactly when that mode is active - whether the
 * mode comes from data-theme or from prefers-color-scheme.
 */
export type ThemeChoice = 'auto' | 'light' | 'dark'
export const THEME_KEY = 'nordlys-theme'
export const THEME_ORDER: ThemeChoice[] = ['auto', 'light', 'dark']

export function readChoice(): ThemeChoice {
  try {
    const value = localStorage.getItem(THEME_KEY)
    return value === 'light' || value === 'dark' ? value : 'auto'
  } catch {
    return 'auto'
  }
}

/**
 * Stamp the effective theme on <html>. Precedence: visitor choice >
 * skin.conf mode > system (no data-theme = follow prefers-color-scheme).
 */
export function applyChoice(choice: ThemeChoice, skinMode?: string): void {
  const root = document.documentElement
  const forced =
    choice === 'light' || choice === 'dark'
      ? choice
      : skinMode === 'light' || skinMode === 'dark'
        ? skinMode
        : null
  if (forced) root.dataset.theme = forced
  else delete root.dataset.theme
  try {
    localStorage.setItem(THEME_KEY, choice)
  } catch {
    /* private mode: choice just doesn't persist */
  }
  updateThemeColor()
}

/** Keep the browser-chrome color matching the effective background. */
export function updateThemeColor(): void {
  const bg =
    getComputedStyle(document.documentElement)
      .getPropertyValue('--nl-bg')
      .trim() || '#0b1220'
  // Replace any static (media-based) metas with a single managed one.
  document
    .querySelectorAll('meta[name="theme-color"]:not([data-nl])')
    .forEach((meta) => meta.remove())
  let meta = document.querySelector<HTMLMetaElement>(
    'meta[name="theme-color"][data-nl]',
  )
  if (!meta) {
    meta = document.createElement('meta')
    meta.name = 'theme-color'
    meta.setAttribute('data-nl', '')
    document.head.appendChild(meta)
  }
  meta.content = bg
}

export function applyTheme(theme?: ThemeConfig): void {
  if (!theme) return

  // data-theme is owned by the theme switcher / <head> bootstrap; here we
  // only inject the per-mode token overrides.
  const rules: string[] = []
  if (theme.dark && Object.keys(theme.dark).length > 0) {
    rules.push(`:root { ${cssVars(theme.dark)} }`)
    rules.push(`:root[data-theme='dark'] { ${cssVars(theme.dark)} }`)
  }
  if (theme.light && Object.keys(theme.light).length > 0) {
    rules.push(
      `@media (prefers-color-scheme: light) { :root:not([data-theme='dark']) { ${cssVars(theme.light)} } }`,
    )
    rules.push(`:root[data-theme='light'] { ${cssVars(theme.light)} }`)
  }
  if (rules.length === 0) return

  const style = document.createElement('style')
  style.id = 'nordlys-theme-overrides'
  style.textContent = rules.join('\n')
  document.head.appendChild(style)
}
