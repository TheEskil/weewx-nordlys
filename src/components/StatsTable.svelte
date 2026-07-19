<script lang="ts">
  import type { NordlysPayload, StatsEntry, TileConfig } from '../lib/types'
  import { formatValue } from '../lib/format'
  import { emptyObsSet, obsKeysOf } from '../lib/empty'

  let { tile, payload }: { tile: TileConfig; payload: NordlysPayload } =
    $props()

  const span = $derived(tile.options?.span ?? 'month')
  const obsKeys = $derived(obsKeysOf(tile))
  const empty = $derived(
    tile.options?.always_show ? new Set<string>() : emptyObsSet(payload),
  )
  const rows = $derived(
    obsKeys
      .filter((key) => !empty.has(key))
      .map((key) => ({ key, entry: payload.stats?.[span]?.[key] }))
      .filter((row): row is { key: string; entry: StatsEntry } =>
        Boolean(row.entry),
      ),
  )
  const hasSum = $derived(rows.some(({ entry }) => entry.sum !== undefined))

  // style = cards: present the extremes as record cards (label, value,
  // date) instead of a min/avg/max table - for all-time station records.
  const asCards = $derived(tile.options?.style === 'cards')
  type Card = {
    key: string
    label: string
    value: number | null
    unit: string
    decimals: number
    time?: string
  }
  const cards = $derived.by(() => {
    const out: Card[] = []
    for (const { key, entry } of rows) {
      const label = entry.label.toLowerCase()
      if (entry.sum !== undefined) {
        if (entry.max)
          out.push({
            key: `${key}-max`,
            label: `Wettest day`,
            value: entry.max.value,
            unit: entry.unit,
            decimals: entry.decimals,
            time: entry.max.time,
          })
      } else {
        if (entry.max)
          out.push({
            key: `${key}-max`,
            label: `Highest ${label}`,
            value: entry.max.value,
            unit: entry.unit,
            decimals: entry.decimals,
            time: entry.max.time,
          })
        if (entry.min)
          out.push({
            key: `${key}-min`,
            label: `Lowest ${label}`,
            value: entry.min.value,
            unit: entry.unit,
            decimals: entry.decimals,
            time: entry.min.time,
          })
      }
    }
    return out
  })
</script>

{#if asCards}
  {#if cards.length > 0}
    <div class="cards">
      {#each cards as card (card.key)}
        <div class="card">
          <p class="card-label">{card.label}</p>
          <p class="card-value nl-num">
            {formatValue(card.value, card.decimals)}<span class="card-unit"
              >{card.unit}</span
            >
          </p>
          {#if card.time}<p class="card-time nl-num">{card.time}</p>{/if}
        </div>
      {/each}
    </div>
  {:else}
    <p class="missing">No records for {span}</p>
  {/if}
{:else if rows.length > 0}
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
  .cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: var(--nl-space-2);
  }

  .card-label {
    font-size: var(--nl-fs-sm);
    color: var(--nl-text-dim);
  }

  .card-value {
    font-size: var(--nl-fs-lg);
    font-weight: 600;
    margin-top: var(--nl-space-0);
  }

  .card-unit {
    font-size: var(--nl-fs-base);
    font-weight: 400;
    color: var(--nl-text-dim);
    margin-left: var(--nl-space-0);
  }

  .card-time {
    font-size: var(--nl-fs-sm);
    color: var(--nl-text-dim);
    margin-top: var(--nl-space-0);
  }

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
