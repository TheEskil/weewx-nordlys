<script lang="ts">
  import type { NordlysPayload, PeriodStat, TileConfig } from '../lib/types'
  import { formatValue } from '../lib/format'
  import ObsIcon from './ObsIcon.svelte'

  let { tile, payload }: { tile: TileConfig; payload: NordlysPayload } =
    $props()

  const archives = $derived(payload.archives)
  // view = archive (the month/year browser) | noaa (the text reports);
  // omitted renders both, for a bare reports tile.
  const view = $derived((tile.options?.view as string | undefined) ?? 'both')

  /** Years newest first, each with its months in calendar order. */
  const grouped = $derived.by(() => {
    if (!archives) return []
    return [...archives.years].reverse().map((year) => ({
      year,
      months: archives.months.filter((m) => m.year === year.id),
    }))
  })

  function fmt(s: PeriodStat): string {
    const v = formatValue(s.value, s.decimals)
    return s.unit ? `${v} ${s.unit}` : v
  }
  // Year headers spell out the aggregate ("avg." / "total").
  const AGG_LABEL: Record<string, string> = { avg: 'avg.', sum: 'total' }
</script>

{#if grouped.length > 0}
  {#if view === 'archive' || view === 'both'}
    <div class="browser">
      {#each grouped as { year, months } (year.id)}
        <div class="period">
          <div class="period-head">
            <a class="year nl-num" href={year.page}>{year.label}</a>
            {#if year.stats}
              <span class="year-stats nl-num">
                {#each year.stats as s (s.obs)}
                  <span class="year-stat">
                    {fmt(s)}<span class="agg">{AGG_LABEL[s.aggregate] ?? ''}</span
                    >
                  </span>
                {/each}
              </span>
            {/if}
          </div>
          <div class="cells">
            {#each months as m (m.id)}
              <a class="cell" href={m.page}>
                <span class="cell-label">{m.month ?? m.label}</span>
                {#if m.stats}
                  <span class="cell-stats nl-num">
                    {#each m.stats as s (s.obs)}
                      <span class="cell-stat">
                        <ObsIcon obs={s.obs} label={s.obs} />
                        <span>{fmt(s)}</span>
                      </span>
                    {/each}
                  </span>
                {/if}
              </a>
            {/each}
          </div>
        </div>
      {/each}
    </div>
  {/if}

  {#if view === 'noaa' || view === 'both'}
    <div class="noaa">
      {#each grouped as { year, months } (year.id)}
        <div class="row">
          {#if year.noaa}<a class="year nl-num" href={year.noaa}>{year.label}</a
            >{/if}
          <span class="months">
            {#each months as m (m.id)}
              {#if m.noaa}<a href={m.noaa}>{m.month ?? m.label}</a>{/if}
            {/each}
          </span>
        </div>
      {/each}
    </div>
  {/if}
{:else}
  <p class="missing">No archive periods yet</p>
{/if}

<style>
  .period + .period {
    margin-top: var(--nl-space-3);
    border-top: 1px solid var(--nl-border);
    padding-top: var(--nl-space-2);
  }

  .period-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--nl-space-2);
    flex-wrap: wrap;
  }

  .year-stats {
    display: flex;
    gap: var(--nl-space-3);
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }

  .agg {
    margin-left: 0.35em;
    opacity: 0.75;
  }

  .cells {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(128px, 1fr));
    gap: var(--nl-space-2);
    margin-top: var(--nl-space-2);
  }

  .cell {
    display: flex;
    flex-direction: column;
    gap: var(--nl-space-1);
    padding: var(--nl-space-2);
    border: 1px solid var(--nl-border);
    border-radius: var(--nl-radius);
    text-decoration: none;
    color: var(--nl-text);
  }

  .cell:hover {
    border-color: var(--nl-accent);
  }

  .cell-label {
    font-weight: 600;
    font-size: var(--nl-fs-base);
  }

  .cell-stats {
    display: flex;
    flex-direction: column;
    gap: var(--nl-space-0);
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }

  .cell-stat {
    display: flex;
    align-items: center;
    gap: 0.4em;
  }

  .cell-stat :global(.obs-icon) {
    opacity: 0.7;
  }

  .year {
    font-weight: 600;
    min-width: 3.5em;
  }

  .row {
    display: flex;
    align-items: baseline;
    gap: var(--nl-space-2);
    padding: var(--nl-space-1) 0;
  }

  .row + .row {
    border-top: 1px solid var(--nl-border);
  }

  .months {
    display: flex;
    flex-wrap: wrap;
    gap: var(--nl-space-0) var(--nl-space-2);
    font-size: var(--nl-fs-sm);
  }

  .months a {
    color: var(--nl-text-dim);
  }

  .months a:hover {
    color: var(--nl-accent);
  }

  .missing {
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }
</style>
