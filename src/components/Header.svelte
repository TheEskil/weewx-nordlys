<script lang="ts">
  import type { PageConfig, Station } from '../lib/types'
  import type { LiveStatus } from '../lib/live'

  let {
    station,
    pages,
    active,
    live = 'off',
    onNavigate,
  }: {
    station: Station
    pages: PageConfig[]
    active: string
    live?: LiveStatus
    onNavigate: (id: string) => void
  } = $props()
</script>

<header>
  <div class="station">
    <h1>{station.name}</h1>
    {#if station.location && station.location !== station.name}
      <p class="location">{station.location}</p>
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
          <button
            type="button"
            class:active={page.id === active}
            aria-current={page.id === active ? 'page' : undefined}
            onclick={() => onNavigate(page.id)}
          >
            {page.title}
          </button>
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

  nav button {
    border: none;
    background: none;
    padding: var(--nl-space-0) 0;
    color: var(--nl-text-dim);
    font: inherit;
    font-size: var(--nl-fs-sm);
    cursor: pointer;
    border-bottom: 2px solid transparent;
  }

  nav button:hover {
    color: var(--nl-text);
  }

  nav button.active {
    color: var(--nl-text);
    border-bottom-color: var(--nl-accent);
  }
</style>
