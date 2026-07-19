<script lang="ts">
  import type { NordlysPayload, SeriesEntry, TileConfig } from '../lib/types'
  import { formatValue } from '../lib/format'
  import { emptyObsSet, obsKeysOf } from '../lib/empty'

  let { tile, payload }: { tile: TileConfig; payload: NordlysPayload } =
    $props()

  const PAGE_SIZE = 24

  const span = $derived(tile.options?.span ?? 'day')
  const empty = $derived(
    tile.options?.always_show ? new Set<string>() : emptyObsSet(payload),
  )
  const obsKeys = $derived(obsKeysOf(tile).filter((key) => !empty.has(key)))
  const columns = $derived(
    obsKeys
      .map((key) => ({ key, entry: payload.series?.[span]?.[key] }))
      .filter((col): col is { key: string; entry: SeriesEntry } =>
        Boolean(col.entry),
      ),
  )

  // Rows joined on the first column's timestamps (raw series align).
  const allRows = $derived.by(() => {
    if (columns.length === 0) return []
    const byTime = columns.map(
      ({ entry }) => new Map(entry.points as [number, number | null][]),
    )
    return columns[0].entry.points.map(([ts]) => ({
      ts,
      values: byTime.map((m) => m.get(ts) ?? null),
    }))
  })

  let sortBy = $state(-1) // -1 = time, else column index
  let sortAsc = $state(false)
  let page = $state(0)

  const sorted = $derived.by(() => {
    const rows = [...allRows]
    rows.sort((a, b) => {
      const va = sortBy === -1 ? a.ts : (a.values[sortBy] ?? -Infinity)
      const vb = sortBy === -1 ? b.ts : (b.values[sortBy] ?? -Infinity)
      return sortAsc ? va - vb : vb - va
    })
    return rows
  })
  const pages = $derived(Math.max(1, Math.ceil(sorted.length / PAGE_SIZE)))
  const visible = $derived(
    sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE),
  )

  function sortOn(index: number) {
    if (sortBy === index) {
      sortAsc = !sortAsc
    } else {
      sortBy = index
      sortAsc = false
    }
    page = 0
  }

  function timeLabel(ts: number): string {
    return new Date(ts * 1000).toLocaleString(undefined, {
      weekday: 'short',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    })
  }

  function arrow(index: number): string {
    if (sortBy !== index) return ''
    return sortAsc ? ' ↑' : ' ↓'
  }
</script>

{#if columns.length > 0}
  <div class="scroll">
    <table>
      <thead>
        <tr>
          <th>
            <button type="button" onclick={() => sortOn(-1)}>
              Time{arrow(-1)}
            </button>
          </th>
          {#each columns as { key, entry }, i (key)}
            <th>
              <button type="button" onclick={() => sortOn(i)}>
                {entry.label}
                {#if entry.unit}<span class="unit">{entry.unit}</span>{/if}
                {arrow(i)}
              </button>
            </th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each visible as row (row.ts)}
          <tr>
            <td class="nl-num time">{timeLabel(row.ts)}</td>
            {#each row.values as value, i (i)}
              <td class="nl-num">
                {formatValue(value, columns[i].entry.decimals)}
              </td>
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
  <div class="pager">
    <button
      type="button"
      disabled={page === 0}
      onclick={() => (page -= 1)}
    >
      ‹ Newer
    </button>
    <span class="nl-num">{page + 1} / {pages}</span>
    <button
      type="button"
      disabled={page >= pages - 1}
      onclick={() => (page += 1)}
    >
      Older ›
    </button>
  </div>
{:else}
  <p class="missing">No archive data</p>
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
    padding: 0;
  }

  thead th:first-child {
    text-align: left;
  }

  thead button {
    border: none;
    background: none;
    font: inherit;
    font-weight: 600;
    font-size: 0.6875rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--nl-text-dim);
    cursor: pointer;
    padding: var(--nl-space-0) var(--nl-space-1);
    white-space: nowrap;
  }

  thead button:hover {
    color: var(--nl-text);
  }

  .unit {
    text-transform: none;
    letter-spacing: normal;
  }

  td {
    text-align: right;
    padding: var(--nl-space-0) var(--nl-space-1);
    border-top: 1px solid var(--nl-border);
    white-space: nowrap;
  }

  td.time {
    text-align: left;
    color: var(--nl-text-dim);
  }

  .pager {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--nl-space-2);
    margin-top: var(--nl-space-1);
    font-size: var(--nl-fs-sm);
    color: var(--nl-text-dim);
  }

  .pager button {
    border: none;
    background: none;
    font: inherit;
    font-size: var(--nl-fs-sm);
    color: var(--nl-text-dim);
    cursor: pointer;
    padding: var(--nl-space-0);
  }

  .pager button:not(:disabled):hover {
    color: var(--nl-text);
  }

  .pager button:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .missing {
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }
</style>
