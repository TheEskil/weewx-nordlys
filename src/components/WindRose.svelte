<script lang="ts">
  import type { NordlysPayload, TileConfig } from '../lib/types'

  let { tile, payload }: { tile: TileConfig; payload: NordlysPayload } =
    $props()

  const span = $derived(tile.options?.span ?? 'day')
  const rose = $derived(payload.windrose?.[span])

  const CX = 100
  const CY = 84
  const R_INNER = 6
  const R_OUTER = 64
  const HALF_WIDTH = 9 // degrees; sectors are 22.5° apart

  // Sequential ramp from light air to strong wind.
  const RAMP = ['series-6', 'accent-2', 'accent', 'warm', 'accent-4', 'accent-3']

  function point(angle: number, radius: number): string {
    const rad = (angle * Math.PI) / 180
    return `${CX + radius * Math.sin(rad)} ${CY - radius * Math.cos(rad)}`
  }

  function wedge(angle: number, r0: number, r1: number): string {
    const a0 = angle - HALF_WIDTH
    const a1 = angle + HALF_WIDTH
    return [
      `M ${point(a0, r1)}`,
      `A ${r1} ${r1} 0 0 1 ${point(a1, r1)}`,
      `L ${point(a1, r0)}`,
      `A ${r0} ${r0} 0 0 0 ${point(a0, r0)}`,
      'Z',
    ].join(' ')
  }

  const maxTotal = $derived(
    rose
      ? Math.max(...rose.sectors.map((bands) => bands.reduce((a, b) => a + b, 0)))
      : 0,
  )

  function radius(cumulative: number): number {
    if (maxTotal === 0) return R_INNER
    return R_INNER + (cumulative / maxTotal) * (R_OUTER - R_INNER)
  }

  /** [sector angle, band index, r0, r1] for every non-empty segment */
  const segments = $derived.by(() => {
    if (!rose) return []
    const out: [number, number, number, number][] = []
    rose.sectors.forEach((bands, sector) => {
      let cumulative = 0
      bands.forEach((pct, band) => {
        if (pct <= 0) return
        const r0 = radius(cumulative)
        cumulative += pct
        out.push([sector * 22.5, band, r0, radius(cumulative)])
      })
    })
    return out
  })

  const rings = $derived(
    maxTotal > 0 ? [1 / 3, 2 / 3, 1].map((f) => f * maxTotal) : [],
  )

  function bandLabel(index: number, bands: number[]): string {
    if (index === 0) return `< ${bands[0]}`
    if (index === bands.length) return `≥ ${bands[bands.length - 1]}`
    return `${bands[index - 1]} - ${bands[index]}`
  }

  const cardinals = [
    { label: 'N', angle: 0 },
    { label: 'E', angle: 90 },
    { label: 'S', angle: 180 },
    { label: 'W', angle: 270 },
  ]
</script>

<article>
  <h3>{tile.title ?? 'Wind rose'}</h3>
  {#if rose}
    <svg viewBox="0 0 200 168" role="img" aria-label="Wind rose">
      {#each rings as ring (ring)}
        <circle
          class="ring"
          cx={CX}
          cy={CY}
          r={radius(ring)}
        />
      {/each}
      {#each rings as ring (ring)}
        <text class="ring-label nl-num" x={CX + 3} y={CY - radius(ring) - 2}>
          {Math.round(ring)}%
        </text>
      {/each}
      {#each segments as [angle, band, r0, r1], i (i)}
        <path
          d={wedge(angle, r0, r1)}
          fill="var(--nl-{RAMP[band % RAMP.length]})"
        />
      {/each}
      {#each cardinals as c (c.label)}
        <text class="cardinal" x={point(c.angle, R_OUTER + 10).split(' ')[0]}
          y={Number(point(c.angle, R_OUTER + 10).split(' ')[1]) + 3}>
          {c.label}
        </text>
      {/each}
    </svg>
    <div class="legend">
      {#each { length: rose.bands.length + 1 } as _, band (band)}
        <span class="chip">
          <span
            class="dot"
            style:background="var(--nl-{RAMP[band % RAMP.length]})"
          ></span>
          {bandLabel(band, rose.bands)}
        </span>
      {/each}
      <span class="chip unit">{rose.unit}</span>
      <span class="chip calm nl-num">calm {rose.calm}%</span>
    </div>
  {:else}
    <p class="missing">No wind data</p>
  {/if}
</article>

<style>
  h3 {
    font-size: var(--nl-fs-sm);
    font-weight: 500;
    color: var(--nl-text-dim);
    margin-bottom: var(--nl-space-1);
  }

  svg {
    display: block;
    width: 100%;
    max-width: 260px;
    margin: 0 auto;
  }

  .ring {
    fill: none;
    stroke: var(--nl-border);
    stroke-width: 1;
  }

  .ring-label {
    font-size: 6.5px;
    fill: var(--nl-text-dim);
  }

  .cardinal {
    font-size: 8px;
    fill: var(--nl-text-dim);
    text-anchor: middle;
  }

  .legend {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: var(--nl-space-0) var(--nl-space-2);
    margin-top: var(--nl-space-1);
    font-size: var(--nl-fs-sm);
    color: var(--nl-text-dim);
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-variant-numeric: tabular-nums;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .missing {
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }
</style>
