<script lang="ts">
  import type { HistoryEntry, NordlysPayload, TileConfig } from '../lib/types'
  import { formatValue } from '../lib/format'
  import { obsKeysOf } from '../lib/empty'
  import Glyph from './Glyph.svelte'

  let { tile, payload }: { tile: TileConfig; payload: NordlysPayload } =
    $props()

  const span = $derived(tile.options?.span ?? 'day')
  const obsKeys = $derived(obsKeysOf(tile))
  const groups = $derived(
    obsKeys
      .map((key) => ({ key, entry: payload.history?.[span]?.[key] }))
      .filter((g): g is { key: string; entry: HistoryEntry } =>
        Boolean(g.entry),
      ),
  )

  type Row = {
    kind: 'max' | 'avg' | 'min'
    label: string
    value: string
    year?: number
  }

  function fmt(entry: HistoryEntry, v: number | null): string {
    return `${formatValue(v, entry.decimals)}${entry.unit}`
  }

  // Records ranked high -> normal -> low. `low` is absent for sum/wind/rate
  // obs, so those simply show fewer rows.
  function rows(entry: HistoryEntry): Row[] {
    const out: Row[] = []
    if (entry.high)
      out.push({
        kind: 'max',
        label: 'Record high',
        value: fmt(entry, entry.high.value),
        year: entry.high.year,
      })
    if (entry.avg !== undefined)
      out.push({ kind: 'avg', label: 'Normal', value: fmt(entry, entry.avg) })
    if (entry.low)
      out.push({
        kind: 'min',
        label: 'Record low',
        value: fmt(entry, entry.low.value),
        year: entry.low.year,
      })
    return out
  }

  // Today's comparable figure: the day's high where there is one (temp, gust,
  // …), or the running total for sum obs like rain. Live-updates over MQTT.
  function todayValue(key: string): number | null | undefined {
    const obs = payload.current?.[key]
    return obs?.max?.value ?? obs?.value
  }
  function todayText(key: string, entry: HistoryEntry): string | null {
    const v = todayValue(key)
    if (v === null || v === undefined) return null
    return fmt(entry, v)
  }
  // Flag a record-tying/breaking day so it stands out.
  function todayKind(key: string, entry: HistoryEntry): '' | 'hot' | 'cold' {
    const v = todayValue(key)
    if (v === null || v === undefined) return ''
    if (entry.high?.value != null && v >= entry.high.value) return 'hot'
    if (entry.low?.value != null && v <= entry.low.value) return 'cold'
    return ''
  }
</script>

{#if groups.length > 0}
  <div class="groups">
    {#each groups as { key, entry } (key)}
      <div class="group">
        <p class="obs">{entry.label}</p>
        {#if todayText(key, entry)}
          <p class="today nl-num" data-kind={todayKind(key, entry)}>
            {todayText(key, entry)}<span class="tag">today</span>
          </p>
        {/if}
        <div class="records">
          {#each rows(entry) as row (row.kind)}
            <span class="label">
              <Glyph kind={row.kind} label={row.label} />
              <span>{row.label}</span>
            </span>
            <span class="value nl-num">{row.value}</span>
            <span class="year nl-num">{row.year ?? ''}</span>
          {/each}
        </div>
      </div>
    {/each}
  </div>
{:else}
  <p class="missing">No history yet</p>
{/if}

<style>
  .groups {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: var(--nl-space-3) var(--nl-space-5);
  }

  /* Stacked in one column (mobile), the groups need a divider so one obs's
     records don't run straight into the next obs heading. */
  @media (max-width: 560px) {
    .group + .group {
      border-top: 1px solid var(--nl-border);
      padding-top: var(--nl-space-3);
    }
  }

  .obs {
    font-size: var(--nl-fs-sm);
    font-weight: 500;
    color: var(--nl-text-dim);
  }

  .today {
    font-size: var(--nl-fs-lg);
    font-weight: 600;
    letter-spacing: -0.01em;
    margin: 0.1em 0 var(--nl-space-1);
  }

  .today .tag {
    font-size: var(--nl-fs-sm);
    font-weight: 400;
    color: var(--nl-text-dim);
    margin-left: 0.4em;
  }

  .today[data-kind='hot'] {
    color: var(--nl-hot);
  }

  .today[data-kind='cold'] {
    color: var(--nl-cold);
  }

  /* Desktop: narrow columns, packed tight-left so the year doesn't collide with
     the next column. Mobile (below): the card is full width, so the label flexes
     and the value/year sit at the right edge instead of leaving an empty void. */
  .records {
    display: grid;
    grid-template-columns: auto auto auto;
    justify-content: start;
    align-items: baseline;
    column-gap: var(--nl-space-2);
    row-gap: 0.35em;
    padding-top: var(--nl-space-1);
    border-top: 1px solid var(--nl-border);
    font-size: var(--nl-fs-sm);
  }

  @media (max-width: 560px) {
    .records {
      grid-template-columns: 1fr auto auto;
    }
  }

  .label {
    display: inline-flex;
    align-items: center;
    gap: 0.4em;
    color: var(--nl-text-dim);
  }

  .value {
    font-weight: 600;
    text-align: right;
  }

  .year {
    color: var(--nl-text-dim);
    opacity: 0.7;
    text-align: right;
    min-width: 2.5em;
  }

  .missing {
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }
</style>
