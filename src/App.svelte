<script lang="ts">
  import type { NordlysPayload } from './lib/types'
  import { startLive, type LiveStatus } from './lib/live'
  import Header from './components/Header.svelte'
  import Page from './components/Page.svelte'

  let { payload }: { payload: NordlysPayload } = $props()

  // The payload prop is set once at mount; deep-reactive state lets
  // live updates flow into tiles.
  // svelte-ignore state_referenced_locally
  const data = $state(payload)
  let liveStatus: LiveStatus = $state('off')

  // svelte-ignore state_referenced_locally
  let activePageId = $state(payload.config.pages[0]?.id)
  const activePage = $derived(
    data.config.pages.find((p) => p.id === activePageId),
  )
  const generated = $derived(
    new Date(data.meta.generatedAt * 1000).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }),
  )

  $effect(() => {
    const live = data.config.live
    if (!live?.broker) return
    return startLive(live, applyLiveUpdates, (status) => (liveStatus = status))
  })

  function applyLiveUpdates(updates: Record<string, number>) {
    const now = new Date().toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    })
    for (const [key, value] of Object.entries(updates)) {
      const obs = data.current[key]
      if (!obs) continue
      const rounded = Number(value.toFixed(obs.decimals ?? 1))
      obs.value = rounded
      if (obs.max?.value != null && rounded > obs.max.value) {
        obs.max = { value: rounded, time: now }
      }
      if (obs.min?.value != null && rounded < obs.min.value) {
        obs.min = { value: rounded, time: now }
      }
    }
  }
</script>

<!-- The one brand flourish: a full-bleed aurora gradient hairline. -->
<div class="aurora" aria-hidden="true"></div>

<div class="app">
  <Header
    station={data.meta.station}
    pages={data.config.pages}
    active={activePageId}
    live={liveStatus}
    period={data.period}
    onNavigate={(id) => (activePageId = id)}
  />

  <main>
    {#if activePage}
      <Page page={activePage} payload={data} />
    {:else}
      <p class="empty">
        No pages configured. Add a page under [Nordlys] [[pages]] in
        skin.conf and re-run the report.
      </p>
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

  .empty {
    color: var(--nl-text-dim);
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
