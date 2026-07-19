<script lang="ts">
  import type { NordlysPayload, TileConfig } from '../lib/types'

  let { tile, payload }: { tile: TileConfig; payload: NordlysPayload } =
    $props()

  const almanac = $derived(payload.almanac)

  // Moon disc: terminator ellipse from fullness; lit side from phase name.
  const R = 15
  const moon = $derived.by(() => {
    if (!almanac) return null
    const fullness = Math.max(0, Math.min(100, almanac.moon_fullness))
    const waxing = !/waning|last quarter|third quarter/i.test(
      almanac.moon_phase,
    )
    const rx = R * Math.abs(Math.cos((Math.PI * fullness) / 100))
    const growing = fullness > 50
    // Outer semicircle on the lit side, terminator arc back.
    const side = waxing ? 1 : 0
    const path = [
      `M 0 ${-R}`,
      `A ${R} ${R} 0 0 ${side} 0 ${R}`,
      `A ${rx} ${R} 0 0 ${growing ? side : 1 - side} 0 ${-R}`,
      'Z',
    ].join(' ')
    return { path, fullness }
  })
</script>

<article>
  <h3>{tile.title ?? 'Sun & moon'}</h3>
  {#if almanac}
    <div class="halves">
      <div class="half">
        {#if almanac.always_up}
          <p class="big">Midnight sun</p>
          <p class="detail">The sun does not set today</p>
        {:else if almanac.always_down}
          <p class="big">Polar night</p>
          <p class="detail">The sun does not rise today</p>
        {:else}
          <p class="rise-set nl-num">
            <span>↑ {almanac.sunrise}</span>
            <span>↓ {almanac.sunset}</span>
          </p>
          {#if almanac.day_length}
            <p class="detail nl-num">Day length {almanac.day_length}</p>
          {/if}
        {/if}
      </div>
      <div class="half moon">
        <svg viewBox="-18 -18 36 36" aria-hidden="true">
          <circle class="disc" r={R} />
          {#if moon}
            <path class="lit" d={moon.path} />
          {/if}
        </svg>
        <div>
          <p class="phase">{almanac.moon_phase}</p>
          <p class="detail nl-num">{almanac.moon_fullness}% illuminated</p>
        </div>
      </div>
    </div>
  {:else}
    <p class="missing">No almanac data</p>
  {/if}
</article>

<style>
  h3 {
    font-size: var(--nl-fs-sm);
    font-weight: 500;
    color: var(--nl-text-dim);
    margin-bottom: var(--nl-space-1);
  }

  .halves {
    display: flex;
    flex-wrap: wrap;
    gap: var(--nl-space-2) var(--nl-space-4);
    align-items: center;
  }

  .half {
    min-width: 140px;
  }

  .rise-set {
    display: flex;
    gap: var(--nl-space-2);
    font-size: var(--nl-fs-lg);
    font-weight: 600;
  }

  .big {
    font-size: var(--nl-fs-lg);
    font-weight: 600;
  }

  .detail {
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
    margin-top: var(--nl-space-0);
  }

  .moon {
    display: flex;
    align-items: center;
    gap: var(--nl-space-2);
  }

  .moon svg {
    width: 44px;
    height: 44px;
    flex-shrink: 0;
  }

  .disc {
    fill: none;
    stroke: var(--nl-border);
    stroke-width: 1.5;
  }

  .lit {
    fill: var(--nl-text-dim);
  }

  .phase {
    font-weight: 500;
  }

  .phase::first-letter {
    text-transform: uppercase;
  }

  .missing {
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }
</style>
