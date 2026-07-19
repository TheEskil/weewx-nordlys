<script lang="ts">
  import type { PageConfig, Station } from '../lib/types'

  let {
    station,
    pages,
    active,
    onNavigate,
  }: {
    station: Station
    pages: PageConfig[]
    active: string
    onNavigate: (id: string) => void
  } = $props()
</script>

<header>
  <div class="station">
    <h1>{station.name}</h1>
    <p class="location">{station.location}</p>
  </div>

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
