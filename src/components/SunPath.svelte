<script lang="ts">
  import type { AlmanacData } from '../lib/types'

  let { almanac }: { almanac: AlmanacData } = $props()

  // A wide viewBox keeps the full-width arc a short banner (not a tall block).
  const W = 240
  const H = 46

  const path = $derived(almanac.sun_path ?? [])
  const alts = $derived([
    ...path.map((p) => p[1]),
    ...(almanac.sun_alt != null ? [almanac.sun_alt] : []),
    0,
  ])
  const altTop = $derived(Math.max(12, Math.ceil((Math.max(...alts) + 4) / 5) * 5))
  const altBot = $derived(Math.min(-6, Math.floor((Math.min(...alts) - 3) / 5) * 5))

  const xOf = (min: number) => (min / 1440) * W
  const yOf = (alt: number) =>
    H - ((alt - altBot) / (altTop - altBot)) * H

  const horizonY = $derived(yOf(0))
  const line = $derived(
    path
      .map((p, i) => `${i ? 'L' : 'M'} ${xOf(p[0]).toFixed(1)} ${yOf(p[1]).toFixed(1)}`)
      .join(' '),
  )
  const dayArea = $derived(
    path.length
      ? `${line} L ${xOf(path[path.length - 1][0]).toFixed(1)} ${horizonY.toFixed(1)}` +
          ` L ${xOf(path[0][0]).toFixed(1)} ${horizonY.toFixed(1)} Z`
      : '',
  )
  const sun = $derived(
    almanac.sun_now != null && almanac.sun_alt != null
      ? { x: xOf(almanac.sun_now), y: yOf(almanac.sun_alt), up: almanac.sun_alt >= 0 }
      : null,
  )

  // Twilight zones below the horizon (civil/nautical/astronomical),
  // clamped to the drawn area; deeper = darker.
  const bands = $derived(
    [
      [0, -6, 0.05],
      [-6, -12, 0.09],
      [-12, -18, 0.13],
    ]
      .map(([hi, lo, opacity]) => {
        const top = yOf(hi)
        const bottom = Math.min(H, yOf(lo))
        return { top, height: Math.max(0, bottom - top), opacity }
      })
      .filter((b) => b.height > 0.1),
  )

  function minutes(clock: string | null | undefined): number | null {
    if (!clock) return null
    const [h, m] = clock.split(':').map(Number)
    return Number.isFinite(h) && Number.isFinite(m) ? h * 60 + m : null
  }
  const marks = $derived(
    [
      { min: minutes(almanac.sunrise), label: almanac.sunrise },
      { min: minutes(almanac.transit), label: almanac.transit },
      { min: minutes(almanac.sunset), label: almanac.sunset },
    ].filter((mk): mk is { min: number; label: string } => mk.min != null),
  )
</script>

<div class="sunpath">
  {#if almanac.always_up}
    <p class="note">Midnight sun - the sun stays above the horizon all day.</p>
  {:else if almanac.always_down}
    <p class="note">Polar night - the sun stays below the horizon all day.</p>
  {/if}
  <svg viewBox="0 0 {W} {H + 8}" role="img" aria-label="Today's sun path">
    {#each bands as band (band.top)}
      <rect
        class="twilight"
        x="0"
        y={band.top}
        width={W}
        height={band.height}
        style:opacity={band.opacity}
      />
    {/each}
    {#if dayArea}<path class="day" d={dayArea} />{/if}
    <line class="horizon" x1="0" y1={horizonY} x2={W} y2={horizonY} />
    {#if line}<path class="track" d={line} />{/if}
    {#each marks as mk (mk.min)}
      <line class="tick" x1={xOf(mk.min)} y1={horizonY - 1.5} x2={xOf(mk.min)} y2={horizonY + 1.5} />
      <text
        class="time"
        x={xOf(mk.min)}
        y={H + 6}
        text-anchor={xOf(mk.min) < W * 0.1
          ? 'start'
          : xOf(mk.min) > W * 0.9
            ? 'end'
            : 'middle'}
      >{mk.label}</text>
    {/each}
    {#if sun}
      <circle class="sun" class:down={!sun.up} cx={sun.x} cy={sun.y} r="2.6" />
    {/if}
  </svg>
</div>

<style>
  .note {
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
    margin-bottom: var(--nl-space-1);
  }

  svg {
    display: block;
    width: 100%;
    max-height: 320px;
    margin: 0 auto;
  }

  .twilight {
    fill: var(--nl-text);
  }

  .day {
    fill: var(--nl-accent);
    opacity: 0.1;
  }

  .horizon {
    stroke: var(--nl-border);
    stroke-width: 0.5;
  }

  .track {
    fill: none;
    stroke: var(--nl-accent);
    stroke-width: 1;
    stroke-linejoin: round;
  }

  .tick {
    stroke: var(--nl-text-dim);
    stroke-width: 0.5;
  }

  .time {
    fill: var(--nl-text-dim);
    font-size: 3px;
    font-variant-numeric: tabular-nums;
  }

  .sun {
    fill: var(--nl-accent);
  }

  .sun.down {
    fill: var(--nl-text-dim);
  }
</style>
