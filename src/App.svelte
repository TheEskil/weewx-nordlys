<script lang="ts">
  import type { NordlysPayload } from './lib/types'
  import Header from './components/Header.svelte'
  import Page from './components/Page.svelte'

  let { payload }: { payload: NordlysPayload } = $props()

  // The payload prop is set once at mount; capturing the initial page is intended.
  // svelte-ignore state_referenced_locally
  let activePageId = $state(payload.config.pages[0]?.id)
  const activePage = $derived(
    payload.config.pages.find((p) => p.id === activePageId),
  )
  const generated = $derived(
    new Date(payload.meta.generatedAt * 1000).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }),
  )
</script>

<!-- The one brand flourish: a full-bleed aurora gradient hairline. -->
<div class="aurora" aria-hidden="true"></div>

<div class="app">
  <Header
    station={payload.meta.station}
    pages={payload.config.pages}
    active={activePageId}
    onNavigate={(id) => (activePageId = id)}
  />

  <main>
    {#if activePage}
      <Page page={activePage} current={payload.current} />
    {/if}
  </main>

  <footer>
    <span>Generated {generated}</span>
    <span>Powered by <a href="https://weewx.com">weewx</a> · Nordlys</span>
  </footer>
</div>

<style>
  .aurora {
    height: 2px;
    background: linear-gradient(
      90deg,
      var(--nl-accent),
      var(--nl-accent-2),
      var(--nl-accent-3)
    );
  }

  .app {
    max-width: var(--nl-max-width);
    margin: 0 auto;
    padding: 0 var(--nl-space-3);
    min-height: 100dvh;
    display: flex;
    flex-direction: column;
  }

  main {
    flex: 1;
    padding: var(--nl-space-4) 0 var(--nl-space-6);
  }

  footer {
    display: flex;
    justify-content: space-between;
    gap: var(--nl-space-2);
    flex-wrap: wrap;
    padding: var(--nl-space-2) 0 var(--nl-space-3);
    border-top: 1px solid var(--nl-border);
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }

  footer a {
    color: var(--nl-text-dim);
    text-decoration: underline;
  }
</style>
