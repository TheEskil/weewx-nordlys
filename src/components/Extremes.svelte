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
        <span class="v">
          <Glyph kind="min" label="lowest" />
          <span>{formatValue(obs.min.value, decimals)}<span class="unit"
              >{obs.unit}</span
            ></span>
        </span>
        <span class="time">{obs.min.time ?? ''}</span>
      </span>
    {/if}
    {#if obs.max}
      <span class="item max">
        <span class="v">
          <Glyph kind="max" label="highest" />
          <span>{formatValue(obs.max.value, decimals)}<span class="unit"
              >{obs.unit}</span
            ></span>
        </span>
        <span class="time">{obs.max.time ?? ''}</span>
      </span>
    {/if}
  </div>
{/if}

<style>
  /* The day's low pinned left, the high pinned right. For the low the icon
     leads and the time sits flush-left beneath it; for the high the value is
     right-aligned and the time sits flush-right beneath it - a mirrored pair. */
  .extremes {
    display: flex;
    justify-content: space-between;
    align-items: start;
    gap: var(--nl-space-3);
    color: var(--nl-text-dim);
  }

  .item {
    display: flex;
    flex-direction: column;
    gap: 0.1em;
    min-width: 0;
  }

  .v {
    display: inline-flex;
    align-items: center;
    gap: 0.3em;
    white-space: nowrap;
  }

  .time {
    font-size: 0.85em;
    line-height: 1;
    opacity: 0.55;
  }

  .unit {
    opacity: 0.7;
    margin-left: 0.1em;
  }

  /* Explicit alignment so a centered context (the gauge dial) can't leak in
     and shift the time: the low's time flush-left under its icon ... */
  .item.min {
    text-align: left;
  }

  /* ... and the high pinned right (even with no low), its value and time both
     right-aligned so the time lands under the number's right edge. */
  .item.max {
    margin-left: auto;
    align-items: flex-end;
    text-align: right;
  }
</style>
