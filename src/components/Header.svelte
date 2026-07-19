<script lang="ts">
  import type { PageConfig, PeriodInfo, Station } from '../lib/types'
  import type { LiveStatus } from '../lib/live'

  let {
    station,
    pages,
    active,
    live = 'off',
    period = null,
    href,
    onNavigate,
  }: {
    station: Station
    pages: PageConfig[]
    active: string | undefined
    live?: LiveStatus
    period?: PeriodInfo | null
    href: (id: string) => string
    onNavigate: (id: string) => void
  } = $props()

  function onNavClick(event: MouseEvent, id: string) {
    // Let the browser handle modified clicks (new tab, etc.).
    if (
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    )
      return
    event.preventDefault()
    onNavigate(id)
  }
</script>

<header>
  <div class="station">
    {#if period}
      <h1><a class="home" href="index.html">{station.name}</a></h1>
      <p class="location">{period.label} · archive</p>
    {:else}
      <h1>{station.name}</h1>
      {#if station.location && station.location !== station.name}
        <p class="location">{station.location}</p>
      {/if}
    {/if}
  </div>

  <div class="right">
    {#if live !== 'off'}
      <span class="live {live}" title="Live updates: {live}">
        <span class="dot" aria-hidden="true"></span>
        live
      </span>
    {/if}
    {#if pages.length > 1}
      <nav aria-label="Pages">
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

  h1 {
    font-size: var(--nl-fs-lg);
  }

  h1 .home {
    color: inherit;
  }

  h1 .home:hover {
    color: var(--nl-accent);
    text-decoration: none;
  }

  .location {
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }

  .right {
    display: flex;
    align-items: center;
    gap: var(--nl-space-3);
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
  }

  nav a {
    padding: var(--nl-space-0) 0;
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
    text-decoration: none;
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
