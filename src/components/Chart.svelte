<script lang="ts">
  import uPlot from 'uplot'
  import 'uplot/dist/uPlot.min.css'
  import type { NordlysPayload, SeriesEntry, TileConfig } from '../lib/types'
  import { cssColor } from '../lib/color'
  import { degToCompass } from '../lib/format'
  import { emptyObsSet, obsKeysOf } from '../lib/empty'
  import { formatsOf, strftime } from '../lib/strftime'

  let { tile, payload }: { tile: TileConfig; payload: NordlysPayload } =
    $props()

  const kind = $derived(tile.options?.chart ?? 'line')
  const span = $derived(tile.options?.span ?? 'day')
  const fmts = $derived(formatsOf(payload))
  // Day-scale charts tick by time (06:00, 12:00, …); longer spans by date
  // (13 Jul, 14 Jul), replacing uPlot's US "6pm" defaults.
  const isDaySpan = $derived(['24h', 'day', 'yesterday'].includes(span))
  const empty = $derived(
    tile.options?.always_show ? new Set<string>() : emptyObsSet(payload),
  )
  const obsKeys = $derived(obsKeysOf(tile).filter((key) => !empty.has(key)))
  const entries = $derived(
    obsKeys
      .map((key) => payload.series?.[span]?.[key])
      .filter((entry): entry is SeriesEntry => entry !== undefined),
  )
  // A bar chart may overlay a second obs (e.g. rain bars + rain-rate line) on
  // its own right-hand axis. Present only when the obs has series data.
  const overlayKey = $derived(
    typeof tile.options?.overlay === 'string' ? tile.options.overlay : undefined,
  )
  const overlay = $derived(
    overlayKey && !empty.has(overlayKey)
      ? payload.series?.[span]?.[overlayKey]
      : undefined,
  )
  // A lone line series reads better filled; multiple series stay unfilled so
  // they don't obscure each other.
  const fillLine = $derived(kind === 'line' && entries.length === 1)
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

  // The overlay (a rate line) shares the x-axis but keeps its own scale,
  // anchored at zero so it reads against the bars beneath it.
  function overlayRange(_u: uPlot, _min: number, dataMax: number): [number, number] {
    return dataMax == null || dataMax <= 0 ? [0, 1] : [0, dataMax * 1.1]
  }

  // Bucket-average the overlay onto the base series' timestamps. The base
  // (rain, summed) is bucketed coarser than the raw rate, so we average each
  // rate sample into the base bucket (prev, t] it falls in - keeping the line
  // aligned with the bars at every span.
  function alignOverlay(
    baseTimes: number[],
    pts: [number, number | null][],
  ): (number | null)[] {
    const out: (number | null)[] = new Array(baseTimes.length).fill(null)
    let j = 0
    for (let i = 0; i < baseTimes.length; i++) {
      const lo = i === 0 ? -Infinity : baseTimes[i - 1]
      const hi = baseTimes[i]
      let sum = 0
      let n = 0
      while (j < pts.length && pts[j][0] <= hi) {
        const [t, v] = pts[j]
        if (t > lo && v != null) {
          sum += v
          n++
        }
        j++
      }
      out[i] = n ? sum / n : null
    }
    return out
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
          kind === 'area' || fillLine
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
    // Overlay series (e.g. rain rate) rides a distinct right-hand y2 scale.
    if (overlay) {
      const oColor = seriesColor(entries.length)
      series.push({
        label: overlay.label,
        scale: 'y2',
        stroke: oColor,
        width: 1.5,
        value: (_u: uPlot, v: number | null) =>
          v == null
            ? '-'
            : `${v.toFixed(overlay.decimals)}${overlay.unit ? ` ${overlay.unit}` : ''}`,
      })
    }
    return {
      width,
      height: 190,
      series: [
        {
          value: (_u: uPlot, ts: number | null) =>
            ts == null
              ? ''
              : strftime(ts, isDaySpan ? fmts.weekday_time : fmts.date),
        },
        ...series,
      ],
      scales: {
        y: { range: isDirection ? [0, 360] : yRange },
        ...(overlay ? { y2: { range: overlayRange } } : {}),
      },
      axes: [
        {
          ...axis,
          grid: { show: false },
          values: (_u: uPlot, splits: number[]) =>
            splits.map((ts) =>
              strftime(ts, isDaySpan ? fmts.time : fmts.date),
            ),
        },
        isDirection
          ? {
              ...axis,
              scale: 'y',
              splits: () => [0, 90, 180, 270, 360],
              values: () => ['N', 'E', 'S', 'W', 'N'],
              size: 40,
            }
          : { ...axis, size: 50, values: tickValues },
        ...(overlay
          ? [
              {
                ...axis,
                scale: 'y2',
                side: 1 as const,
                grid: { show: false },
                size: 50,
                values: tickValues,
              },
            ]
          : []),
      ],
      cursor: { y: false },
      legend: { live: true },
    }
  }

  $effect(() => {
    if (!container || entries.length === 0) return

    const baseTimes = entries[0].points.map((p) => p[0])
    const data: uPlot.AlignedData = [
      baseTimes,
      ...entries.map((entry) => entry.points.map((p) => p[1])),
      ...(overlay ? [alignOverlay(baseTimes, overlay.points)] : []),
    ]

    let plot: uPlot | undefined
    const media = matchMedia('(prefers-color-scheme: dark)')
    const create = () => {
      plot?.destroy()
      plot = new uPlot(buildOptions(container!.clientWidth), data, container!)
    }
    create()

    // Recreate on theme flips (colors are resolved to concrete values).
    // uPlot follows neither prefers-color-scheme nor the data-theme the
    // switcher toggles, so watch both.
    media.addEventListener('change', create)
    const themeObserver = new MutationObserver(create)
    themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme'],
    })
    const resize = new ResizeObserver(() => {
      if (plot && container) plot.setSize({ width: container.clientWidth, height: 190 })
    })
    resize.observe(container)

    return () => {
      media.removeEventListener('change', create)
      themeObserver.disconnect()
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
