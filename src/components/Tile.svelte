<script lang="ts">
  import type { Observation, TileConfig } from '../lib/types'
  import StatTile from './StatTile.svelte'
  import Gauge from './Gauge.svelte'
  import CompassGauge from './CompassGauge.svelte'

  let {
    tile,
    current,
  }: {
    tile: TileConfig
    current: Record<string, Observation>
  } = $props()

  const obs = $derived(tile.obs ? current[tile.obs] : undefined)
</script>

<div class="tile">
  {#if tile.type === 'gauge' && obs}
    {#if tile.options?.style === 'compass'}
      <CompassGauge {obs} title={tile.title} />
    {:else}
      <Gauge {obs} title={tile.title} options={tile.options} />
    {/if}
  {:else if tile.type === 'stat' && obs}
    <StatTile {obs} title={tile.title} options={tile.options} />
  {:else if tile.type === 'text'}
    <p class="text">{tile.title ?? ''}</p>
  {:else}
    <p class="missing">
      {tile.obs ? `No data for ${tile.obs}` : `Unsupported tile: ${tile.type}`}
    </p>
  {/if}
</div>

<style>
  .tile {
    background: var(--nl-surface);
    border: 1px solid var(--nl-border);
    border-radius: var(--nl-radius);
    padding: var(--nl-space-2) var(--nl-space-2) var(--nl-space-2);
    min-width: 0;
  }

  .missing {
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }
</style>
