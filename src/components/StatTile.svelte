<script lang="ts">
  import type { Observation, TileOptions } from '../lib/types'
  import { valueColor } from '../lib/color'
  import { formatObs, formatValue } from '../lib/format'
  import Extremes from './Extremes.svelte'
  import Glyph from './Glyph.svelte'

  let {
    obs,
    title,
    options,
  }: { obs: Observation; title?: string; options?: TileOptions } = $props()

  const decimals = $derived(obs.decimals ?? 1)
  const hasExtremes = $derived(
    Boolean(obs.min) || obs.avg !== undefined || Boolean(obs.max),
  )
  const hasTrend = $derived(obs.trend !== null && obs.trend !== undefined)
  const trendKind = $derived(
    !obs.trend ? 'steady' : obs.trend > 0 ? 'rising' : 'falling',
  )
</script>

<article>
  <h3>{title ?? obs.label}</h3>
  <p class="value nl-num" style:color={valueColor(obs.value, options)}>
    {formatObs(obs)}<span class="unit">{obs.unit}</span>
  </p>
  {#if hasExtremes || hasTrend}
    <div class="detail nl-num">
      <Extremes {obs} />
      {#if hasTrend}
        <span class="trend">
          <Glyph kind={trendKind} label="trend" />
          {formatValue(Math.abs(obs.trend as number), decimals)}
        </span>
      {/if}
    </div>
  {/if}
</article>

<style>
  h3 {
    font-size: var(--nl-fs-sm);
    font-weight: 500;
    color: var(--nl-text-dim);
  }

  .value {
    font-size: var(--nl-fs-xl);
    font-weight: 600;
    letter-spacing: -0.01em;
    margin-top: var(--nl-space-0);
  }

  .unit {
    font-size: var(--nl-fs-base);
    font-weight: 400;
    color: var(--nl-text-dim);
    margin-left: var(--nl-space-0);
  }

  /* When the value is semantically colored, the unit stays dim. */
  .value .unit {
    color: var(--nl-text-dim);
  }

  .detail {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: var(--nl-space-0) var(--nl-space-2);
    flex-wrap: wrap;
    margin-top: var(--nl-space-1);
    font-size: var(--nl-fs-sm);
    color: var(--nl-text-dim);
  }

  .trend {
    display: inline-flex;
    align-items: center;
    gap: 0.2em;
    margin-left: auto;
    white-space: nowrap;
  }
</style>
