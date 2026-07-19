<script lang="ts">
  import type {
    PageConfig,
    PeriodInfo,
    Station,
    ThemeConfig,
  } from '../lib/types'
  import type { LiveStatus } from '../lib/live'
  import ThemeSwitch from './ThemeSwitch.svelte'

  let {
    station,
    pages,
    active,
    live = 'off',
    period = null,
    theme,
    href,
    onNavigate,
  }: {
    station: Station
    pages: PageConfig[]
    active: string | undefined
    live?: LiveStatus
    period?: PeriodInfo | null
    theme?: ThemeConfig
    href: (id: string) => string
    onNavigate: (id: string) => void
  } = $props()

  function isPlainClick(event: MouseEvent): boolean {
    return !(
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    )
  }

  function onNavClick(event: MouseEvent, id: string) {
    // Let the browser handle modified clicks (new tab, etc.).
    if (!isPlainClick(event)) return
    event.preventDefault()
    onNavigate(id)
  }

  // Icon + name link to Today: intercepted like a nav link on live pages;
  // on archive pages let it navigate to index.html for real.
  function onBrandClick(event: MouseEvent) {
    if (period || !isPlainClick(event)) return
    const home = pages[0]?.id
    if (!home) return
    event.preventDefault()
    onNavigate(home)
  }

  // The tab row scrolls horizontally on narrow screens; a gradient fade
  // hints at hidden tabs on whichever side has more, and the active tab
  // is kept in view.
  let navEl: HTMLElement | undefined = $state()
  let atStart = $state(true)
  let atEnd = $state(true)

  function updateFade() {
    if (!navEl) return
    atStart = navEl.scrollLeft <= 1
    atEnd = navEl.scrollLeft + navEl.clientWidth >= navEl.scrollWidth - 1
  }

  $effect(() => {
    updateFade()
    const onResize = () => updateFade()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  })

  $effect(() => {
    active // re-run when the active tab changes
    const el = navEl?.querySelector('.active') as HTMLElement | undefined
    el?.scrollIntoView({ inline: 'nearest', block: 'nearest' })
    updateFade()
  })
</script>

<header>
  <a class="brand" href="index.html" aria-label={station.name} onclick={onBrandClick}>
    <img class="icon" src="icon.svg" alt="" width="28" height="28" />
    <span class="names">
      <h1>{station.name}</h1>
      {#if period}
        <span class="location">{period.label} · archive</span>
      {:else if station.location && station.location !== station.name}
        <span class="location">{station.location}</span>
      {/if}
    </span>
  </a>

  <div class="right">
    {#if pages.length > 1}
      <nav
        aria-label="Pages"
        bind:this={navEl}
        onscroll={updateFade}
        style:--fade-l={atStart ? '0px' : '16px'}
        style:--fade-r={atEnd ? '0px' : '16px'}
      >
        {#each pages as page (page.id)}
          <a
            href={href(page.id)}
            class:active={page.id === active}
            aria-current={page.id === active ? 'page' : undefined}
            onclick={(event) => onNavClick(event, page.id)}
          >
            {page.title}
          </a>
        {/each}
      </nav>
    {/if}
    <div class="controls">
      {#if theme?.switcher !== false}
        <ThemeSwitch skinMode={theme?.mode} />
      {/if}
      {#if live !== 'off'}
        <span class="live {live}" title="Live updates: {live}">
          <span class="dot" aria-hidden="true"></span>
          live
        </span>
      {/if}
    </div>
  </div>
</header>

<style>
  header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--nl-space-3);
    flex-wrap: wrap;
    padding: var(--nl-space-3) 0 var(--nl-space-2);
    border-bottom: 1px solid var(--nl-border);
  }

  .brand {
    display: flex;
    align-items: center;
    gap: var(--nl-space-2);
    text-decoration: none;
    color: inherit;
    min-width: 0;
  }

  .icon {
    width: 28px;
    height: 28px;
    flex: none;
    border-radius: 6px;
  }

  .names {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  h1 {
    font-size: var(--nl-fs-lg);
  }

  .brand:hover h1 {
    color: var(--nl-accent);
  }

  .location {
    display: block;
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }

  .right {
    display: flex;
    align-items: center;
    gap: var(--nl-space-3);
    min-width: 0;
  }

  .controls {
    display: flex;
    align-items: center;
    gap: var(--nl-space-2);
    flex: none;
  }

  .live {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: var(--nl-fs-sm);
    color: var(--nl-text-dim);
  }

  .live .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--nl-text-dim);
  }

  .live.connected .dot {
    background: var(--nl-ok);
  }

  @media (prefers-reduced-motion: no-preference) {
    .live.connected .dot {
      animation: nl-pulse 2.4s ease-in-out infinite;
    }
  }

  .live.error .dot {
    background: var(--nl-alert);
  }

  @keyframes nl-pulse {
    50% {
      opacity: 0.4;
    }
  }

  nav {
    display: flex;
    gap: var(--nl-space-2);
    min-width: 0;
    max-width: 100%;
    overflow-x: auto;
    scrollbar-width: none;
    /* Fade only the side that has more tabs to scroll to. */
    -webkit-mask-image: linear-gradient(
      to right,
      transparent 0,
      #000 var(--fade-l, 0),
      #000 calc(100% - var(--fade-r, 0)),
      transparent 100%
    );
    mask-image: linear-gradient(
      to right,
      transparent 0,
      #000 var(--fade-l, 0),
      #000 calc(100% - var(--fade-r, 0)),
      transparent 100%
    );
  }

  nav::-webkit-scrollbar {
    display: none;
  }

  nav a {
    padding: var(--nl-space-0) 0;
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
    text-decoration: none;
    white-space: nowrap;
    scroll-margin: 0 12px;
    border-bottom: 2px solid transparent;
  }

  nav a:hover {
    color: var(--nl-text);
  }

  nav a.active {
    color: var(--nl-text);
    border-bottom-color: var(--nl-accent);
  }
</style>
