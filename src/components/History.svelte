<script lang="ts">
  import type { HistoryEntry, NordlysPayload, TileConfig } from '../lib/types'
  import { formatValue } from '../lib/format'
  import { obsKeysOf } from '../lib/empty'

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

  type Card = { kind: string; label: string; text: string; meta?: string }

  function cards(entry: HistoryEntry): Card[] {
    const out: Card[] = []
    const fmt = (v: number | null) =>
      `${formatValue(v, entry.decimals)}${entry.unit}`
    if (entry.high)
      out.push({
        kind: 'high',
        label: 'Highest',
        text: fmt(entry.high.value),
        meta: [entry.high.year, entry.high.time].filter(Boolean).join(' · '),
      })
    if (entry.avg !== undefined)
      out.push({ kind: 'avg', label: 'Average', text: fmt(entry.avg) })
    if (entry.low)
      out.push({
        kind: 'low',
        label: 'Lowest',
        text: fmt(entry.low.value),
        meta: [entry.low.year, entry.low.time].filter(Boolean).join(' · '),
      })
    return out
  }
</script>

{#if groups.length > 0}
  <div class="groups">
    {#each groups as { key, entry } (key)}
      <div class="group">
        <p class="obs">{entry.label}</p>
        <div class="cards">
          {#each cards(entry) as card (card.kind)}
            <div class="card">
              <p class="card-label">{card.label}</p>
              <p class="card-value nl-num">{card.text}</p>
              {#if card.meta}<p class="card-meta nl-num">{card.meta}</p>{/if}
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

  .obs {
    font-size: var(--nl-fs-sm);
    font-weight: 500;
    color: var(--nl-text-dim);
    margin-bottom: var(--nl-space-1);
  }

  .cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
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

  .card-meta {
    font-size: var(--nl-fs-sm);
    color: var(--nl-text-dim);
    margin-top: var(--nl-space-0);
  }

  .missing {
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }
</style>
