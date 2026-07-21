<script lang="ts">
  import type { NordlysPayload, StatsEntry, TileConfig } from '../lib/types'
  import { formatValue } from '../lib/format'
  import { emptyObsSet, obsKeysOf } from '../lib/empty'

  let { tile, payload }: { tile: TileConfig; payload: NordlysPayload } =
    $props()

  const spans = $derived(
    tile.options?.spans && tile.options.spans.length > 0
      ? tile.options.spans
      : [tile.options?.span ?? 'month'],
  )
  // The table (non-cards) view renders a single span.
  const span = $derived(spans[0])
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

  // style = cards: present the extremes as record cards (label, value, date)
  // instead of a min/avg/max table. With several spans, each card compares them
  // (e.g. this year vs all-time).
  const asCards = $derived(tile.options?.style === 'cards')
  const SPAN_LABEL: Record<string, string> = {
    day: 'Today',
    yesterday: 'Yesterday',
    week: 'This week',
    month: 'This month',
    year: 'This year',
    alltime: 'All-time',
  }
  const visibleObs = $derived(obsKeys.filter((key) => !empty.has(key)))

  type Line = { spanLabel: string; value: number | null; time?: string }
  type Card = {
    key: string
    label: string
    unit: string
    decimals: number
    lines: Line[]
  }

  // The record metrics a given obs contributes, based on its all-spans data:
  // sum obs -> wettest day; others -> highest (+ lowest when a min exists).
  function metricsFor(key: string): { metric: 'max' | 'min'; label: string }[] {
    const anySum = spans.some(
      (s) => payload.stats?.[s]?.[key]?.sum !== undefined,
    )
    const label = (payload.stats?.[spans[0]]?.[key]?.label ?? key).toLowerCase()
    if (anySum) return [{ metric: 'max', label: 'Wettest day' }]
    const anyMin = spans.some((s) => Boolean(payload.stats?.[s]?.[key]?.min))
    const out: { metric: 'max' | 'min'; label: string }[] = [
      { metric: 'max', label: `Highest ${label}` },
    ]
    if (anyMin) out.push({ metric: 'min', label: `Lowest ${label}` })
    return out
  }

  const cards = $derived.by(() => {
    const showSpanLabels = spans.length > 1
    const out: Card[] = []
    for (const key of visibleObs) {
      if (!spans.some((s) => payload.stats?.[s]?.[key])) continue
      for (const { metric, label } of metricsFor(key)) {
        const lines: Line[] = []
        let unit = ''
        let decimals = 1
        for (const s of spans) {
          const entry = payload.stats?.[s]?.[key]
          const ex = entry?.[metric]
          if (!entry || !ex) continue
          unit = entry.unit
          decimals = entry.decimals
          lines.push({
            spanLabel: showSpanLabels ? (SPAN_LABEL[s] ?? s) : '',
            value: ex.value,
            time: ex.time,
          })
        }
        if (lines.length > 0)
          out.push({ key: `${key}-${metric}`, label, unit, decimals, lines })
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
          {#each card.lines as line, i (i)}
            <div class="line" class:multi={card.lines.length > 1}>
              {#if line.spanLabel}<span class="line-span">{line.spanLabel}</span
                >{/if}
              <span class="card-value nl-num">
                {formatValue(line.value, card.decimals)}<span class="card-unit"
                  >{card.unit}</span
                >
              </span>
              {#if line.time}<span class="card-time nl-num">{line.time}</span
                >{/if}
            </div>
          {/each}
        </div>
      {/each}
    </div>
  {:else}
    <p class="missing">No records</p>
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
    margin-bottom: var(--nl-space-0);
  }

  /* Single-span cards stack value over time; comparative (multi-span) cards
     lay each span out as a labelled row: span | value | date. */
  .line.multi {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: baseline;
    gap: 0 var(--nl-space-1);
  }

  /* Single-span: value over its date, like the original record cards. */
  .line:not(.multi) .card-value,
  .line:not(.multi) .card-time {
    display: block;
  }

  .line + .line {
    margin-top: var(--nl-space-0);
  }

  .line-span {
    font-size: var(--nl-fs-sm);
    color: var(--nl-text-dim);
  }

  .card-value {
    font-size: var(--nl-fs-lg);
    font-weight: 600;
  }

  .line.multi .card-value {
    text-align: right;
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
  }

  .line.multi .card-time {
    text-align: right;
    white-space: nowrap;
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
