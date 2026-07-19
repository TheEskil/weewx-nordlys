<script lang="ts">
  import type { NordlysPayload, StatsEntry, TileConfig } from '../lib/types'
  import { formatValue } from '../lib/format'

  let { tile, payload }: { tile: TileConfig; payload: NordlysPayload } =
    $props()

  const span = $derived(tile.options?.span ?? 'month')
  const obsKeys = $derived(
    Array.isArray(tile.obs) ? tile.obs : tile.obs ? [tile.obs] : [],
  )
  const rows = $derived(
    obsKeys
      .map((key) => ({ key, entry: payload.stats?.[span]?.[key] }))
      .filter((row): row is { key: string; entry: StatsEntry } =>
        Boolean(row.entry),
      ),
  )
  const hasSum = $derived(rows.some(({ entry }) => entry.sum !== undefined))
</script>

{#if rows.length > 0}
  <div class="scroll">
    <table>
      <thead>
        <tr>
          <th></th>
          <th>Min</th>
          <th>Avg</th>
          <th>Max</th>
          {#if hasSum}<th>Total</th>{/if}
        </tr>
      </thead>
      <tbody>
        {#each rows as { key, entry } (key)}
          <tr>
            <th scope="row">
              {entry.label}
              <span class="unit">{entry.unit}</span>
            </th>
            <td class="nl-num">
              {#if entry.min}
                {formatValue(entry.min.value, entry.decimals)}
                {#if entry.min.time}<span class="time">{entry.min.time}</span
                  >{/if}
              {/if}
            </td>
            <td class="nl-num">
              {#if entry.avg !== undefined}
                {formatValue(entry.avg, entry.decimals)}
              {/if}
            </td>
            <td class="nl-num">
              {#if entry.max}
                {formatValue(entry.max.value, entry.decimals)}
                {#if entry.max.time}<span class="time">{entry.max.time}</span
                  >{/if}
              {/if}
            </td>
            {#if hasSum}
              <td class="nl-num">
                {#if entry.sum !== undefined}
                  {formatValue(entry.sum, entry.decimals)}
                {/if}
              </td>
            {/if}
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
{:else}
  <p class="missing">No statistics for {span}</p>
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

  tbody th {
    text-align: left;
    font-weight: 500;
    white-space: nowrap;
  }

  tbody th .unit {
    color: var(--nl-text-dim);
    margin-left: var(--nl-space-0);
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

  .time {
    color: var(--nl-text-dim);
    margin-left: var(--nl-space-0);
    font-size: 0.6875rem;
  }

  .missing {
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }
</style>
