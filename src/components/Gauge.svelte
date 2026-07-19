<script lang="ts">
  import type { Observation, TileOptions } from '../lib/types'
  import { valueColor } from '../lib/color'
  import { formatObs, formatTrend, formatValue } from '../lib/format'

  let {
    obs,
    title,
    options,
  }: { obs: Observation; title?: string; options?: TileOptions } = $props()

  // 240° arc, from -120° to +120°, measured clockwise from 12 o'clock.
  const SPAN = 240
  const START = -SPAN / 2
  const CX = 50
  const CY = 50
  const R = 40

  function point(angle: number): [number, number] {
    const rad = (angle * Math.PI) / 180
    return [CX + R * Math.sin(rad), CY - R * Math.cos(rad)]
  }

  function arc(from: number, to: number): string {
    const [x1, y1] = point(from)
    const [x2, y2] = point(to)
    const large = to - from > 180 ? 1 : 0
    return `M ${x1} ${y1} A ${R} ${R} 0 ${large} 1 ${x2} ${y2}`
  }

  const min = $derived(options?.min ?? 0)
  const max = $derived(options?.max ?? 100)

  function fracOf(value: number): number {
    return Math.min(1, Math.max(0, (value - min) / (max - min)))
  }
  function angleOf(fraction: number): number {
    return START + SPAN * fraction
  }

  const scaled = $derived(max > min)
  const nowFrac = $derived(
    obs.value === null || !scaled ? null : fracOf(obs.value),
  )
  const minVal = $derived(obs.min?.value ?? null)
  const maxVal = $derived(obs.max?.value ?? null)

  // The band spans the period's observed range. With only a max (min is
  // suppressed for wind/UV/etc.) it grows from the scale minimum; with no
  // extremes at all there is no band, only the now-marker dot.
  const band = $derived.by(() => {
    if (!scaled || (minVal === null && maxVal === null)) return null
    const lo = minVal !== null ? fracOf(minVal) : 0
    const hi = maxVal !== null ? fracOf(maxVal) : (nowFrac ?? lo)
    return hi >= lo ? { lo, hi } : { lo: hi, hi: lo }
  })
  const marker = $derived(nowFrac === null ? null : point(angleOf(nowFrac)))

  const [minX, minY] = point(START)
  const [maxX, maxY] = point(-START)
  const arcColor = $derived(valueColor(obs.value, options))
</script>

<article>
  <svg
    viewBox="0 0 100 82"
    role="img"
    aria-label="{title ?? obs.label}: {formatObs(obs)} {obs.unit}"
  >
    <path class="track" d={arc(START, -START)} />
    {#if band}
      <path
        class="band"
        style:stroke={arcColor}
        d={arc(angleOf(band.lo), angleOf(band.hi))}
      />
    {/if}
    {#if marker}
      <circle class="marker" style:fill={arcColor} cx={marker[0]} cy={marker[1]} r="4" />
    {/if}
    <text class="value nl-num" x="50" y="52">{formatObs(obs)}</text>
    <text class="unit" x="50" y="64">{obs.unit}</text>
    {#if obs.trend !== null && obs.trend !== undefined}
      <text class="trend nl-num" x="50" y="80">
        {formatTrend(obs.trend, obs.decimals ?? 1)}
      </text>
    {/if}
    <text class="bound nl-num" x={minX} y={minY + 10}>
      {formatValue(min, 0)}
    </text>
    <text class="bound nl-num" x={maxX} y={maxY + 10}>
      {formatValue(max, 0)}
    </text>
  </svg>
  <h3>{title ?? obs.label}</h3>
</article>

<style>
  article {
    text-align: center;
  }

  svg {
    display: block;
    width: 100%;
    max-width: 180px;
    margin: 0 auto;
  }

  .track {
    fill: none;
    stroke: var(--nl-border);
    stroke-width: 4;
    stroke-linecap: round;
  }

  .band {
    fill: none;
    stroke: var(--nl-accent);
    stroke-width: 4;
    stroke-linecap: round;
    stroke-opacity: 0.35;
  }

  .marker {
    fill: var(--nl-accent);
    stroke: var(--nl-surface);
    stroke-width: 1.25;
  }

  text {
    text-anchor: middle;
  }

  .value {
    font-size: 15px;
    font-weight: 600;
    fill: var(--nl-text);
  }

  .unit {
    font-size: 6.5px;
    fill: var(--nl-text-dim);
  }

  .bound {
    font-size: 6px;
    fill: var(--nl-text-dim);
  }

  .trend {
    font-size: 6px;
    fill: var(--nl-text-dim);
  }

  h3 {
    font-size: var(--nl-fs-sm);
    font-weight: 500;
    color: var(--nl-text-dim);
    margin-top: var(--nl-space-1);
  }
</style>
