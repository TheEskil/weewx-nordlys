<script lang="ts">
  import uPlot from 'uplot'
  import 'uplot/dist/uPlot.min.css'
  import type { NordlysPayload, SeriesEntry, TileConfig } from '../lib/types'
  import { cssColor } from '../lib/color'
  import { degToCompass } from '../lib/format'
  import { emptyObsSet, obsKeysOf } from '../lib/empty'

  let { tile, payload }: { tile: TileConfig; payload: NordlysPayload } =
    $props()

  const kind = $derived(tile.options?.chart ?? 'line')
  const span = $derived(tile.options?.span ?? 'day')
  const empty = $derived(
    tile.options?.always_show ? new Set<string>() : emptyObsSet(payload),
  )
  const obsKeys = $derived(obsKeysOf(tile).filter((key) => !empty.has(key)))
  const entries = $derived(
    obsKeys
      .map((key) => payload.series?.[span]?.[key])
      .filter((entry): entry is SeriesEntry => entry !== undefined),
  )
  const title = $derived(tile.title ?? entries[0]?.label ?? '')
  // All series in one chart share span + aggregation, so the first
  // series' timestamps are the x values for the whole chart.
  const isDirection = $derived(entries.length > 0 && entries[0].unit === '°')

  let container: HTMLDivElement | undefined = $state()

  function token(name: string): string {
    return (
      getComputedStyle(document.documentElement)
        .getPropertyValue(`--nl-${name}`)
        .trim() || '#888888'
    )
  }

  function seriesColor(index: number): string {
    const configured = (tile.options?.colors as string[] | undefined)?.[index]
    if (configured) {
      const css = cssColor(configured)
      // uPlot needs concrete colors, not var() references.
      return css?.startsWith('var(') ? token(configured) : (css ?? '#888888')
    }
    return token(`series-${(index % 6) + 1}`)
  }

  // Plain numeric tick labels: no locale thousands grouping (wrong for
  // measurement values), float noise rounded away.
  function tickValues(_u: uPlot, splits: number[]): string[] {
    return splits.map((v) => (v == null ? '' : String(+v.toFixed(6))))
  }

  // Keep flat/empty series from autoscaling to uPlot's constant-data
  // default (0-100), and anchor bar charts at a zero baseline.
  function yRange(_u: uPlot, dataMin: number, dataMax: number): [number, number] {
    if (dataMin == null || dataMax == null) return [0, 1]
    if (kind === 'bar') {
      return dataMax <= 0 ? [0, 1] : [0, dataMax * 1.1]
    }
    if (dataMin === dataMax) {
      if (dataMin === 0) return [0, 1]
      const pad = Math.abs(dataMin) * 0.1
      return [dataMin - pad, dataMax + pad]
    }
    return uPlot.rangeNum(dataMin, dataMax, 0.1, true) as [number, number]
  }

  function buildOptions(width: number): uPlot.Options {
    const border = token('border')
    const dim = token('text-dim')
    const axis: uPlot.Axis = {
      stroke: dim,
      font: `11px ${token('font')}`,
      ticks: { stroke: border, width: 1, size: 4 },
      grid: { stroke: border, width: 1 },
    }
    const series: uPlot.Series[] = entries.map((entry, i) => {
      const color = seriesColor(i)
      return {
        // A lone series echoes the tile title (e.g. "Rain", not the
        // stat-tile label "Rain today").
        label: entries.length === 1 ? (tile.title ?? entry.label) : entry.label,
        stroke: kind === 'bar' ? undefined : color,
        width: kind === 'bar' ? 0 : 1.5,
        fill:
          kind === 'area'
            ? color + '2e'
            : kind === 'bar'
              ? color + 'cc'
              : undefined,
        paths:
          kind === 'bar'
            ? uPlot.paths!.bars!({ size: [0.6, 100] })
            : kind === 'scatter'
              ? () => null
              : undefined,
        points: { show: kind === 'scatter', size: 4, fill: color },
        value: (_u: uPlot, v: number | null) =>
          v == null
            ? '-'
            : isDirection
              ? `${degToCompass(v)} ${v.toFixed(0)}°`
              : `${v.toFixed(entry.decimals)}${entry.unit ? ` ${entry.unit}` : ''}`,
      }
    })
    return {
      width,
      height: 190,
      series: [{}, ...series],
      scales: { y: { range: isDirection ? [0, 360] : yRange } },
      axes: [
        { ...axis, grid: { show: false } },
        isDirection
          ? {
              ...axis,
              scale: 'y',
              splits: () => [0, 90, 180, 270, 360],
              values: () => ['N', 'E', 'S', 'W', 'N'],
              size: 40,
            }
          : { ...axis, size: 50, values: tickValues },
      ],
      cursor: { y: false },
      legend: { live: true },
    }
  }

  $effect(() => {
    if (!container || entries.length === 0) return

    const data: uPlot.AlignedData = [
      entries[0].points.map((p) => p[0]),
      ...entries.map((entry) => entry.points.map((p) => p[1])),
    ]

    let plot: uPlot | undefined
    const media = matchMedia('(prefers-color-scheme: dark)')
    const create = () => {
      plot?.destroy()
      plot = new uPlot(buildOptions(container!.clientWidth), data, container!)
    }
    create()

    // Recreate on theme flips (colors are resolved to concrete values).
    media.addEventListener('change', create)
    const resize = new ResizeObserver(() => {
      if (plot && container) plot.setSize({ width: container.clientWidth, height: 190 })
    })
    resize.observe(container)

    return () => {
      media.removeEventListener('change', create)
      resize.disconnect()
      plot?.destroy()
    }
  })
</script>

<article>
  {#if title}
    <h3>{title}</h3>
  {/if}
  {#if entries.length > 0}
    <div class="chart" bind:this={container}></div>
  {:else}
    <p class="missing">No chart data for {obsKeys.join(', ')}</p>
  {/if}
</article>

<style>
  h3 {
    font-size: var(--nl-fs-sm);
    font-weight: 500;
    color: var(--nl-text-dim);
    margin-bottom: var(--nl-space-1);
  }

  .missing {
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }

  .chart :global(.u-legend) {
    font-size: var(--nl-fs-sm);
    color: var(--nl-text-dim);
    font-variant-numeric: tabular-nums;
  }

  .chart :global(.u-legend .u-marker) {
    border-radius: 50%;
    width: 8px;
    height: 8px;
  }
</style>
