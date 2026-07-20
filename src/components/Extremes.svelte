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
  /* Two columns: the day's low pinned left, the high pinned right, each with
     its timestamp tucked beneath. */
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

  /* The high sits on the right even when there is no low (max-only obs). */
  .item.max {
    margin-left: auto;
    align-items: flex-end;
    text-align: right;
  }

  .v {
    display: inline-flex;
    align-items: center;
    gap: 0.3em;
    white-space: nowrap;
  }

  .unit {
    opacity: 0.7;
    margin-left: 0.1em;
  }

  .time {
    font-size: 0.85em;
    line-height: 1;
    opacity: 0.55;
  }

  /* Line each time up under its number, past the glyph. */
  .item.min .time {
    padding-left: calc(10px + 0.3em);
  }
</style>
