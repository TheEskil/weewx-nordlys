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
    text: string
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
        text: fmt(entry, entry.high.value),
        year: entry.high.year,
      })
    if (entry.avg !== undefined)
      out.push({ kind: 'avg', label: 'Normal', text: fmt(entry, entry.avg) })
    if (entry.low)
      out.push({
        kind: 'min',
        label: 'Record low',
        text: fmt(entry, entry.low.value),
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
        <div class="obs-head">
          <span class="obs">{entry.label}</span>
          {#if todayText(key, entry)}
            <span class="today nl-num" data-kind={todayKind(key, entry)}>
              <span class="today-label">today</span>{todayText(key, entry)}
            </span>
          {/if}
        </div>
        <div class="rows">
          {#each rows(entry) as row (row.kind)}
            <div class="row">
              <Glyph kind={row.kind} label={row.label} />
              <span class="row-label">{row.label}</span>
              <span class="row-value nl-num">{row.text}</span>
              <span class="row-year nl-num">{row.year ?? ''}</span>
            </div>
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
    display: flex;
    flex-direction: column;
    gap: var(--nl-space-3);
  }

  .obs-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: var(--nl-space-2);
    margin-bottom: var(--nl-space-1);
    border-bottom: 1px solid var(--nl-border);
    padding-bottom: var(--nl-space-0);
  }

  .obs {
    font-size: var(--nl-fs-sm);
    font-weight: 500;
    color: var(--nl-text-dim);
  }

  .today {
    font-size: var(--nl-fs-sm);
    font-weight: 600;
    color: var(--nl-text);
    white-space: nowrap;
  }

  .today-label {
    font-weight: 400;
    color: var(--nl-text-dim);
    margin-right: 0.4em;
  }

  .today[data-kind='hot'] {
    color: var(--nl-hot);
  }

  .today[data-kind='cold'] {
    color: var(--nl-cold);
  }

  .rows {
    display: flex;
    flex-direction: column;
    gap: var(--nl-space-0);
  }

  .row {
    display: grid;
    grid-template-columns: 14px minmax(0, auto) 1fr auto auto;
    align-items: baseline;
    gap: 0 var(--nl-space-2);
    font-size: var(--nl-fs-sm);
  }

  .row :global(.glyph) {
    align-self: center;
  }

  .row-label {
    color: var(--nl-text-dim);
  }

  .row-value {
    font-weight: 600;
    text-align: right;
  }

  .row-year {
    color: var(--nl-text-dim);
    opacity: 0.7;
    min-width: 2.5em;
    text-align: right;
  }

  .missing {
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }
</style>
