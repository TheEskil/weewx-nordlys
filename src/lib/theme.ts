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
export function applyTheme(theme?: ThemeConfig): void {
  if (!theme) return

  const root = document.documentElement
  if (theme.mode === 'dark' || theme.mode === 'light') {
    root.dataset.theme = theme.mode
  }

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
