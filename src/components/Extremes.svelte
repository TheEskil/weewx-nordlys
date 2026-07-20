<script lang="ts">
  import type { Observation } from '../lib/types'
  import { formatValue } from '../lib/format'
  import Glyph from './Glyph.svelte'

  let { obs }: { obs: Observation } = $props()

  const decimals = $derived(obs.decimals ?? 1)
  const has = $derived(Boolean(obs.min) || Boolean(obs.max))
</script>

{#if has}
  <div class="extremes nl-num">
    {#if obs.min}
      <span class="item min">
        <Glyph kind="min" label="lowest" />
        <span class="val"
          >{formatValue(obs.min.value, decimals)}<span class="unit"
            >{obs.unit}</span
          ></span
        >
        <span class="time">{obs.min.time ?? ''}</span>
      </span>
    {/if}
    {#if obs.max}
      <span class="item max">
        <Glyph kind="max" label="highest" />
        <span class="val"
          >{formatValue(obs.max.value, decimals)}<span class="unit"
            >{obs.unit}</span
          ></span
        >
        <span class="time">{obs.max.time ?? ''}</span>
      </span>
    {/if}
  </div>
{/if}

<style>
  /* Two columns: the day's low pinned left, the high pinned right. Within each,
     a small grid keeps the glyph beside the number and drops the time directly
     beneath the number - left-aligned under the low, right-aligned under the
     high, so the two mirror each other. */
  .extremes {
    display: flex;
    justify-content: space-between;
    align-items: start;
    gap: var(--nl-space-3);
    color: var(--nl-text-dim);
  }

  .item {
    display: grid;
    grid-template-columns: auto auto;
    column-gap: 0.3em;
    align-items: baseline;
    min-width: 0;
  }

  .item :global(.glyph) {
    grid-row: 1 / 3;
    align-self: center;
  }

  .val {
    grid-column: 2;
    grid-row: 1;
    white-space: nowrap;
  }

  .time {
    grid-column: 2;
    grid-row: 2;
    font-size: 0.85em;
    line-height: 1;
    opacity: 0.55;
  }

  .unit {
    opacity: 0.7;
    margin-left: 0.1em;
  }

  /* The high pins right even when there is no low (max-only obs). */
  .item.max {
    margin-left: auto;
  }

  .item.max .val,
  .item.max .time {
    text-align: right;
  }
</style>
