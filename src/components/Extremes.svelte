<script lang="ts">
  import type { Observation } from '../lib/types'
  import { formatValue } from '../lib/format'
  import Glyph from './Glyph.svelte'

  let { obs }: { obs: Observation } = $props()

  const decimals = $derived(obs.decimals ?? 1)
  const has = $derived(
    Boolean(obs.min) || obs.avg !== undefined || Boolean(obs.max),
  )
</script>

{#if has}
  <div class="extremes nl-num">
    {#if obs.min}
      <span class="item">
        <Glyph kind="min" label="lowest" />
        <span class="lbl">Low</span>
        <span>{formatValue(obs.min.value, decimals)}<span class="unit"
            >{obs.unit}</span
          ></span>
        {#if obs.min.time}<span class="time">{obs.min.time}</span>{/if}
      </span>
    {/if}
    {#if obs.avg !== undefined}
      <span class="item">
        <Glyph kind="avg" label="average" />
        <span class="lbl">Avg</span>
        <span>{formatValue(obs.avg, decimals)}<span class="unit"
            >{obs.unit}</span
          ></span>
      </span>
    {/if}
    {#if obs.max}
      <span class="item">
        <Glyph kind="max" label="highest" />
        <span class="lbl">High</span>
        <span>{formatValue(obs.max.value, decimals)}<span class="unit"
            >{obs.unit}</span
          ></span>
        {#if obs.max.time}<span class="time">{obs.max.time}</span>{/if}
      </span>
    {/if}
  </div>
{/if}

<style>
  .extremes {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--nl-space-0) var(--nl-space-2);
    color: var(--nl-text-dim);
  }

  .item {
    display: inline-flex;
    align-items: center;
    gap: 0.2em;
    white-space: nowrap;
  }

  /* Word labels (Low / Avg / High) that name each extreme, al199-style. */
  .lbl {
    opacity: 0.65;
    font-variant-numeric: normal;
  }

  .unit {
    opacity: 0.7;
    margin-left: 0.1em;
  }

  .time {
    opacity: 0.7;
  }
</style>
