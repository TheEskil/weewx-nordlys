<script lang="ts">
  import type { NordlysPayload, TileConfig } from '../lib/types'
  import StatTile from './StatTile.svelte'
  import Gauge from './Gauge.svelte'
  import CompassGauge from './CompassGauge.svelte'
  import Chart from './Chart.svelte'
  import WindRose from './WindRose.svelte'
  import Calendar from './Calendar.svelte'
  import StatsTable from './StatsTable.svelte'
  import RecordsTable from './RecordsTable.svelte'
  import Climatology from './Climatology.svelte'
  import History from './History.svelte'
  import Almanac from './Almanac.svelte'
  import Forecast from './Forecast.svelte'
  import Reports from './Reports.svelte'
  import { tileIsEmpty } from '../lib/empty'
  import { periodObs } from '../lib/period'

  let { tile, payload }: { tile: TileConfig; payload: NordlysPayload } =
    $props()

  const obsKey = $derived(Array.isArray(tile.obs) ? tile.obs[0] : tile.obs)
  // A stat tile with a span renders period stats (stats[span]) instead of
  // current conditions.
  const statSpan = $derived(tile.type === 'stat' ? tile.options?.span : undefined)
  const periodEntry = $derived(
    statSpan && obsKey ? payload.stats?.[statSpan]?.[obsKey] : undefined,
  )
  const obs = $derived(
    statSpan
      ? periodEntry
        ? periodObs(periodEntry)
        : undefined
      : obsKey
        ? payload.current[obsKey]
        : undefined,
  )
  // Period stat tiles show the span average (or the total for sum obs like
  // rain) as the hero - label it so it reads as a period figure, not a
  // current reading. Current-conditions tiles (no span) carry no label.
  const aggregate = $derived(
    statSpan && periodEntry
      ? periodEntry.sum !== undefined
        ? 'sum'
        : 'avg'
      : undefined,
  )
  const isChart = $derived(tile.type === 'chart')
  // Absent sensors (and period stat tiles with no stats for the span) are
  // hidden entirely rather than showing empty tiles.
  const hidden = $derived(
    tileIsEmpty(tile, payload) || (statSpan !== undefined && !periodEntry),
  )
</script>

{#if !hidden}
<div class="tile" class:chart={isChart}>
  {#if tile.type === 'gauge' && obs}
    {#if tile.options?.style === 'compass'}
      <CompassGauge {obs} title={tile.title} />
    {:else}
      <Gauge {obs} title={tile.title} options={tile.options} />
    {/if}
  {:else if tile.type === 'stat' && obs}
    <StatTile
      {obs}
      obsKey={obsKey}
      title={tile.title}
      options={tile.options}
      {aggregate}
    />
  {:else if tile.type === 'chart'}
    {#if tile.options?.chart === 'windrose'}
      <WindRose {tile} {payload} />
    {:else if tile.options?.chart === 'calendar'}
      <Calendar {payload} />
    {:else}
      <Chart {tile} {payload} />
    {/if}
  {:else if tile.type === 'table'}
    {#if tile.options?.table === 'records'}
      <RecordsTable {tile} {payload} />
    {:else}
      <StatsTable {tile} {payload} />
    {/if}
  {:else if tile.type === 'climatology'}
    <Climatology {payload} />
  {:else if tile.type === 'history'}
    <History {tile} {payload} />
  {:else if tile.type === 'celestial'}
    <Almanac {tile} {payload} />
  {:else if tile.type === 'forecast'}
    <Forecast {tile} {payload} />
  {:else if tile.type === 'reports'}
    <Reports {payload} />
  {:else if tile.type === 'text'}
    <p class="text">{tile.title ?? ''}</p>
  {:else}
    <p class="missing">
      {obsKey ? `No data for ${obsKey}` : `Unsupported tile: ${tile.type}`}
    </p>
  {/if}
</div>
{/if}

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
