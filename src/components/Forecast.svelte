<script lang="ts">
  import type { NordlysPayload, TileConfig } from '../lib/types'

  let { tile, payload }: { tile: TileConfig; payload: NordlysPayload } =
    $props()

  const forecast = $derived(payload.forecast)

  const TREND = {
    rising: { arrow: '↗', text: 'barometer rising' },
    steady: { arrow: '→', text: 'barometer steady' },
    falling: { arrow: '↘', text: 'barometer falling' },
  } as const
</script>

<article>
  <h3>{tile.title ?? 'Forecast'}</h3>
  {#if forecast}
    <p class="text">{forecast.text}</p>
    <p class="detail">
      {TREND[forecast.trend].arrow}
      {TREND[forecast.trend].text} · Zambretti {forecast.code}
    </p>
  {:else}
    <p class="missing">No forecast available</p>
  {/if}
</article>

<style>
  h3 {
    font-size: var(--nl-fs-sm);
    font-weight: 500;
    color: var(--nl-text-dim);
    margin-bottom: var(--nl-space-1);
  }

  .text {
    font-size: var(--nl-fs-lg);
    font-weight: 600;
  }

  .detail {
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
    margin-top: var(--nl-space-0);
  }

  .missing {
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }
</style>
