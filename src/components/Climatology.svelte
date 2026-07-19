<script lang="ts">
  import type { NordlysPayload } from '../lib/types'

  let { payload }: { payload: NordlysPayload } = $props()

  const days = $derived(payload.climatology?.days ?? [])

  const AGGREGATE_LABEL: Record<string, string> = {
    min: 'daily min',
    max: 'daily max',
    avg: 'daily avg',
    sum: 'daily total',
  }
</script>

{#if days.length > 0}
  <div class="grid">
    {#each days as day (day.id)}
      <div class="entry">
        <p class="count nl-num">{day.count}</p>
        <p class="label">{day.label}</p>
        <p class="criterion nl-num">
          {AGGREGATE_LABEL[day.aggregate] ?? day.aggregate}
          {day.op}
          {day.value}{day.unit ? ` ${day.unit}` : ''}
        </p>
      </div>
    {/each}
  </div>
{:else}
  <p class="missing">No climatological days configured</p>
{/if}

<style>
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: var(--nl-space-2) var(--nl-space-3);
  }

  .count {
    font-size: var(--nl-fs-xl);
    font-weight: 600;
  }

  .label {
    margin-top: var(--nl-space-0);
  }

  .criterion {
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
    margin-top: 2px;
  }

  .missing {
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }
</style>
