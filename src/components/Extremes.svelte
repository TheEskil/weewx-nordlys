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
        <span class="v">
          <Glyph kind="min" label="lowest" />
          <span>{formatValue(obs.min.value, decimals)}<span class="unit"
              >{obs.unit}</span
            ></span>
        </span>
        <span class="time">{obs.min.time ?? ''}</span>
      </span>
    {/if}
    {#if obs.avg !== undefined}
      <span class="item">
        <span class="v">
          <Glyph kind="avg" label="average" />
          <span>{formatValue(obs.avg, decimals)}<span class="unit"
              >{obs.unit}</span
            ></span>
        </span>
        <span class="time"></span>
      </span>
    {/if}
    {#if obs.max}
      <span class="item">
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
  /* min / avg / max spread across the row as aligned columns: the value sits
     on the top line (glyph + number), the time hangs beneath it. */
  .extremes {
    display: flex;
    justify-content: space-between;
    align-items: start;
    gap: var(--nl-space-1) var(--nl-space-3);
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

  .unit {
    opacity: 0.7;
    margin-left: 0.1em;
  }

  .time {
    font-size: 0.85em;
    line-height: 1;
    opacity: 0.55;
    /* line the time up under the number, past the glyph */
    padding-left: calc(10px + 0.3em);
  }
</style>
