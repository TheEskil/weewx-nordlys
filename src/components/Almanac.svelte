<script lang="ts">
  import type { NordlysPayload, TileConfig } from '../lib/types'
  import SunPath from './SunPath.svelte'

  let { tile, payload }: { tile: TileConfig; payload: NordlysPayload } =
    $props()

  const almanac = $derived(payload.almanac)
  const section = $derived(tile.options?.section as string | undefined)

  // Moon disc: terminator ellipse from fullness; lit side from phase name.
  const R = 15
  const moon = $derived.by(() => {
    if (!almanac) return null
    const fullness = Math.max(0, Math.min(100, almanac.moon_fullness))
    const waxing = !/waning|last quarter|third quarter/i.test(almanac.moon_phase)
    const rx = R * Math.abs(Math.cos((Math.PI * fullness) / 100))
    const growing = fullness > 50
    const side = waxing ? 1 : 0
    const path = [
      `M 0 ${-R}`,
      `A ${R} ${R} 0 0 ${side} 0 ${R}`,
      `A ${rx} ${R} 0 0 ${growing ? side : 1 - side} 0 ${-R}`,
      'Z',
    ].join(' ')
    return { path, fullness }
  })

  function deltaLabel(seconds: number): string {
    const sign = seconds >= 0 ? '+' : '−'
    const abs = Math.abs(seconds)
    const m = Math.floor(abs / 60)
    const s = abs % 60
    return `${sign}${m} min ${s.toString().padStart(2, '0')} s`
  }

  // Day-length change worded for the seasons section (getting longer/shorter).
  function trendLabel(seconds: number): string {
    const abs = Math.abs(seconds)
    const m = Math.floor(abs / 60)
    const s = abs % 60
    const dir = seconds < 0 ? 'shorter' : 'longer'
    return `${m} min ${s.toString().padStart(2, '0')} s ${dir}`
  }

  const twilights = $derived(
    almanac?.twilight
      ? ([
          ['Civil', almanac.twilight.civil],
          ['Nautical', almanac.twilight.nautical],
          ['Astronomical', almanac.twilight.astronomical],
        ] as const)
      : [],
  )
  const showExtrasHint = $derived(
    Boolean(section) && almanac != null && almanac.hasExtras === false,
  )

  const eq = $derived(almanac?.seasons?.equinox)
  const sol = $derived(almanac?.seasons?.solstice)
</script>

<article>
  {#if tile.title}<h3>{tile.title}</h3>{/if}

  {#if !almanac}
    <p class="missing">No almanac data</p>
  {:else if section === 'sunpath'}
    <SunPath {almanac} />
  {:else if section === 'sun'}
    <div class="body">
      <svg class="sun-icon" viewBox="-18 -18 36 36" aria-hidden="true">
        <circle class="sun-disc" r="7" />
        <g class="rays">
          <line x1="0" y1="-10.5" x2="0" y2="-15.5" />
          <line x1="7.4" y1="-7.4" x2="11" y2="-11" />
          <line x1="10.5" y1="0" x2="15.5" y2="0" />
          <line x1="7.4" y1="7.4" x2="11" y2="11" />
          <line x1="0" y1="10.5" x2="0" y2="15.5" />
          <line x1="-7.4" y1="7.4" x2="-11" y2="11" />
          <line x1="-10.5" y1="0" x2="-15.5" y2="0" />
          <line x1="-7.4" y1="-7.4" x2="-11" y2="-11" />
        </g>
      </svg>
      <dl class="rows nl-num">
        <div><dt>Sunrise</dt><dd>{almanac.sunrise ?? '-'}</dd></div>
        <div><dt>Sunset</dt><dd>{almanac.sunset ?? '-'}</dd></div>
        {#if almanac.transit}<div><dt>Solar noon</dt><dd>{almanac.transit}</dd></div>{/if}
        {#if almanac.day_length}<div><dt>Day length</dt><dd>{almanac.day_length}</dd></div>{/if}
        {#if almanac.day_length_delta != null}
          <div>
            <dt>vs yesterday</dt>
            <dd class:neg={almanac.day_length_delta < 0}>
              {deltaLabel(almanac.day_length_delta)}
            </dd>
          </div>
        {/if}
        {#each twilights as [name, band] (name)}
          {#if band && (band[0] || band[1])}
            <div>
              <dt>{name} twilight</dt>
              <dd>{band[0] ?? '-'} · {band[1] ?? '-'}</dd>
            </div>
          {/if}
        {/each}
      </dl>
    </div>
  {:else if section === 'moon'}
    <div class="body">
      <svg class="moon-icon" viewBox="-18 -18 36 36" aria-hidden="true">
        <circle class="disc" r={R} />
        {#if moon}<path class="lit" d={moon.path} />{/if}
      </svg>
      <dl class="rows nl-num">
        <div><dt class="phase">{almanac.moon_phase}</dt><dd>{almanac.moon_fullness}%</dd></div>
        {#if almanac.moonrise}<div><dt>Moonrise</dt><dd>{almanac.moonrise}</dd></div>{/if}
        {#if almanac.moonset}<div><dt>Moonset</dt><dd>{almanac.moonset}</dd></div>{/if}
        {#if almanac.next_full_moon}<div><dt>Next full</dt><dd>{almanac.next_full_moon}</dd></div>{/if}
        {#if almanac.next_new_moon}<div><dt>Next new</dt><dd>{almanac.next_new_moon}</dd></div>{/if}
      </dl>
    </div>
  {:else if section === 'seasons'}
    <dl class="rows nl-num">
      {#if almanac.day_length}
        <div><dt>Day length</dt><dd>{almanac.day_length}</dd></div>
      {/if}
      {#if almanac.day_length_delta != null}
        <div>
          <dt>Trend</dt>
          <dd class:neg={almanac.day_length_delta < 0}>
            {trendLabel(almanac.day_length_delta)}
          </dd>
        </div>
      {/if}
      {#if eq}
        <div>
          <dt>Next equinox</dt>
          <dd>{eq.date} <span class="dim">· {eq.days} d</span></dd>
        </div>
      {/if}
      {#if sol}
        <div>
          <dt>Next solstice</dt>
          <dd>{sol.date} <span class="dim">· {sol.days} d</span></dd>
        </div>
        <div>
          <dt>{sol.kind === 'summer' ? 'Longest day' : 'Shortest day'}</dt>
          <dd>{sol.date}</dd>
        </div>
      {/if}
      {#if !eq && !sol}
        <p class="missing">No season data</p>
      {/if}
    </dl>
  {:else if section === 'planets'}
    {#if almanac.planets && almanac.planets.length > 0}
      <table class="planets nl-num">
        <thead><tr><th></th><th>Rise</th><th>Set</th></tr></thead>
        <tbody>
          {#each almanac.planets as planet (planet.name)}
            <tr>
              <th scope="row">{planet.name}</th>
              <td>{planet.rise ?? '-'}</td>
              <td>{planet.set ?? '-'}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {:else}
      <p class="missing">No planet data</p>
    {/if}
  {:else}
    <!-- Bare combo card (Today): sun + moon at a glance. -->
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
          {#if moon}<path class="lit" d={moon.path} />{/if}
        </svg>
        <div>
          <p class="phase">{almanac.moon_phase}</p>
          <p class="detail nl-num">{almanac.moon_fullness}% illuminated</p>
        </div>
      </div>
    </div>
  {/if}

  {#if showExtrasHint}
    <p class="hint">Install <code>ephem</code> for twilight, moon and planet times.</p>
  {/if}
</article>

<style>
  h3 {
    font-size: var(--nl-fs-sm);
    font-weight: 500;
    color: var(--nl-text-dim);
    margin-bottom: var(--nl-space-1);
  }

  .rows {
    display: flex;
    flex-direction: column;
    gap: var(--nl-space-0);
  }

  .rows > div {
    display: flex;
    justify-content: space-between;
    gap: var(--nl-space-2);
    padding: var(--nl-space-0) 0;
    border-top: 1px solid var(--nl-border);
  }

  .rows > div:first-child {
    border-top: none;
  }

  dt {
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }

  dd {
    font-weight: 500;
    white-space: nowrap;
  }

  dd.neg {
    color: var(--nl-cold);
  }

  .dim {
    color: var(--nl-text-dim);
    font-weight: 400;
  }

  .phase {
    text-transform: capitalize;
    font-weight: 500;
  }

  .planets {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--nl-fs-sm);
  }

  .planets th,
  .planets td {
    padding: var(--nl-space-0) var(--nl-space-1);
    border-top: 1px solid var(--nl-border);
  }

  .planets thead th {
    border-top: none;
    color: var(--nl-text-dim);
    font-weight: 600;
    text-align: right;
    text-transform: uppercase;
    font-size: 0.6875rem;
    letter-spacing: 0.06em;
  }

  .planets tbody th {
    text-align: left;
    font-weight: 500;
  }

  .planets td {
    text-align: right;
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

  /* Sun and Moon sections share the same shape: icon left, rows right. */
  .body {
    display: flex;
    align-items: center;
    gap: var(--nl-space-3);
  }

  .body > svg {
    width: 52px;
    height: 52px;
    flex-shrink: 0;
  }

  .body .rows {
    flex: 1;
    min-width: 0;
  }

  .disc {
    fill: none;
    stroke: var(--nl-border);
    stroke-width: 1.5;
  }

  .lit {
    fill: var(--nl-text-dim);
  }

  .sun-disc {
    fill: var(--nl-accent);
  }

  .rays line {
    stroke: var(--nl-accent);
    stroke-width: 2;
    stroke-linecap: round;
  }

  /* The bare combo card (Today) keeps its own two-up layout. */
  .moon {
    display: flex;
    align-items: center;
    gap: var(--nl-space-3);
  }

  .moon svg {
    width: 52px;
    height: 52px;
    flex-shrink: 0;
  }

  .hint {
    margin-top: var(--nl-space-1);
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }

  .hint code {
    font-family: var(--nl-font-mono, monospace);
  }

  .missing {
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }
</style>
