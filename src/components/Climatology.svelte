<script lang="ts">
  import type { NordlysPayload } from '../lib/types'

  let { payload }: { payload: NordlysPayload } = $props()

  const days = $derived(payload.climatology?.days ?? [])

  const MONTHS = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
  ]

  const AGGREGATE_LABEL: Record<string, string> = {
    min: 'daily min',
    max: 'daily max',
    avg: 'daily avg',
    sum: 'daily total',
  }

  function criterion(day: {
    aggregate: string
    op: string
    value: number
    unit: string
  }): string {
    const agg = AGGREGATE_LABEL[day.aggregate] ?? day.aggregate
    return `${agg} ${day.op} ${day.value}${day.unit ? ` ${day.unit}` : ''}`
  }
</script>

{#if days.length > 0}
  <div class="scroll">
    <table>
      <thead>
        <tr>
          <th></th>
          {#each MONTHS as m (m)}<th>{m}</th>{/each}
          <th class="total">Year</th>
        </tr>
      </thead>
      <tbody>
        {#each days as day (day.id)}
          <tr>
            <th scope="row">
              <span class="name">{day.label}</span>
              <span class="criterion">{criterion(day)}</span>
            </th>
            {#each MONTHS as _m, i (i)}
              {@const covered = day.covered?.[i] ?? true}
              {@const n = day.months?.[i] ?? 0}
              <td class="nl-num" class:zero={covered && n === 0}>
                {#if covered}{n}{:else}<span class="blank">·</span>{/if}
              </td>
            {/each}
            <td class="nl-num total">{day.count}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
{:else}
  <p class="missing">No climatological days configured</p>
{/if}

<style>
  .scroll {
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--nl-fs-sm);
  }

  thead th {
    text-align: right;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-size: 0.6875rem;
    color: var(--nl-text-dim);
    padding: var(--nl-space-0) var(--nl-space-1);
  }

  thead th:first-child {
    text-align: left;
  }

  tbody th {
    text-align: left;
    font-weight: 500;
    white-space: nowrap;
    display: flex;
    flex-direction: column;
  }

  tbody th .criterion {
    color: var(--nl-text-dim);
    font-size: 0.6875rem;
    font-weight: 400;
  }

  td,
  tbody th {
    padding: var(--nl-space-1);
    border-top: 1px solid var(--nl-border);
  }

  td {
    text-align: right;
    white-space: nowrap;
  }

  /* Covered-but-zero months stay quiet so the months that happened pop. */
  td.zero {
    color: var(--nl-text-dim);
    opacity: 0.55;
  }

  .blank {
    color: var(--nl-text-dim);
    opacity: 0.4;
  }

  .total {
    font-weight: 600;
    border-left: 1px solid var(--nl-border);
  }

  .missing {
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }
</style>
