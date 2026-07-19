<script lang="ts">
  import type { Observation } from '../lib/types'
  import { formatObs, formatTrend, formatValue } from '../lib/format'

  let { obs, title }: { obs: Observation; title?: string } = $props()

  const decimals = $derived(obs.decimals ?? 1)
</script>

<article>
  <h3>{title ?? obs.label}</h3>
  <p class="value nl-num">
    {formatObs(obs)}<span class="unit">{obs.unit}</span>
  </p>
  <div class="detail nl-num">
    {#if obs.min || obs.max}
      <span>
        {#if obs.min}
          <span class="extreme">↓ {formatValue(obs.min.value, decimals)}</span>
          {#if obs.min.time}<span class="time">{obs.min.time}</span>{/if}
        {/if}
        {#if obs.max}
          <span class="extreme">↑ {formatValue(obs.max.value, decimals)}</span>
          {#if obs.max.time}<span class="time">{obs.max.time}</span>{/if}
        {/if}
      </span>
    {/if}
    {#if obs.trend !== null && obs.trend !== undefined}
      <span class="trend">{formatTrend(obs.trend, decimals)}</span>
    {/if}
  </div>
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

  .detail {
    display: flex;
    justify-content: space-between;
    gap: var(--nl-space-1);
    margin-top: var(--nl-space-1);
    font-size: var(--nl-fs-sm);
    color: var(--nl-text-dim);
  }

  .extreme + .time,
  .time + .extreme {
    margin-left: var(--nl-space-0);
  }

  .time {
    opacity: 0.7;
  }
</style>
