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

  type Day = (typeof days)[number]

  // Year-over-year change for month i, when both this year and last year had
  // data for that month. null = no comparison available.
  function monthDelta(day: Day, i: number): number | null {
    if (!(day.covered?.[i] ?? true) || !day.prevCovered?.[i]) return null
    return (day.months?.[i] ?? 0) - (day.prevMonths?.[i] ?? 0)
  }

  // Year total change over the same period (months both years cover).
  function yearDelta(day: Day): number | null {
    if (!day.prevMonths || !day.prevCovered) return null
    let now = 0
    let prev = 0
    let any = false
    for (let i = 0; i < 12; i++) {
      if ((day.covered?.[i] ?? true) && day.prevCovered[i]) {
        now += day.months?.[i] ?? 0
        prev += day.prevMonths[i] ?? 0
        any = true
      }
    }
    return any ? now - prev : null
  }

  const fmtDelta = (d: number) => (d > 0 ? `+${d}` : `${d}`)
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
          {@const yd = yearDelta(day)}
          <tr>
            <th scope="row">
              <span class="name">{day.label}</span>
              <span class="criterion">{criterion(day)}</span>
            </th>
            {#each MONTHS as _m, i (i)}
              {@const covered = day.covered?.[i] ?? true}
              {@const n = day.months?.[i] ?? 0}
              {@const d = monthDelta(day, i)}
              <td class="nl-num" class:zero={covered && n === 0}>
                {#if covered}{n}{#if d}<span
                      class="delta"
                      class:up={d > 0}
                      class:down={d < 0}>({fmtDelta(d)})</span
                    >{/if}{:else}<span class="blank">·</span>{/if}
              </td>
            {/each}
            <td class="nl-num total">
              {day.count}{#if yd}<span
                  class="delta"
                  class:up={yd > 0}
                  class:down={yd < 0}>({fmtDelta(yd)})</span
                >{/if}
            </td>
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

  /* Year-over-year change vs the same period last year: green up, red down. */
  .delta {
    font-size: 0.625rem;
    font-weight: 500;
    margin-left: 0.25em;
  }

  .delta.up {
    color: var(--nl-ok);
  }

  .delta.down {
    color: var(--nl-alert);
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
