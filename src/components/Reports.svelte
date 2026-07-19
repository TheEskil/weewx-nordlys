<script lang="ts">
  import type { ArchiveLink, NordlysPayload } from '../lib/types'
  import { formatValue } from '../lib/format'

  let { payload }: { payload: NordlysPayload } = $props()

  const archives = $derived(payload.archives)

  /** Years newest first, each with its months in calendar order. */
  const grouped = $derived.by(() => {
    if (!archives) return []
    return [...archives.years].reverse().map((year) => ({
      year,
      months: archives.months.filter((m) => m.year === year.id),
    }))
  })

  function miniStats(link: ArchiveLink): string {
    return (link.stats ?? [])
      .map((s) => {
        const v = formatValue(s.value, s.decimals)
        return s.unit ? `${v} ${s.unit}` : v
      })
      .join(' · ')
  }
</script>

{#if grouped.length > 0}
  <div class="sections">
    <section>
      <h4>Period browser</h4>
      {#each grouped as { year, months } (year.id)}
        <div class="period">
          <div class="period-head">
            <a class="year nl-num" href={year.page}>{year.label}</a>
            {#if year.stats}<span class="mini nl-num">{miniStats(year)}</span>{/if}
          </div>
          <div class="cells">
            {#each months as m (m.id)}
              <a class="cell" href={m.page}>
                <span class="cell-label">{m.month ?? m.label}</span>
                {#if m.stats}<span class="mini nl-num">{miniStats(m)}</span>{/if}
              </a>
            {/each}
          </div>
        </div>
      {/each}
    </section>
    <section>
      <h4>NOAA reports</h4>
      {#each grouped as { year, months } (year.id)}
        <div class="row">
          {#if year.noaa}<a class="year nl-num" href={year.noaa}>{year.label}</a>{/if}
          <span class="months">
            {#each months as m (m.id)}
              {#if m.noaa}<a href={m.noaa}>{m.month ?? m.label}</a>{/if}
            {/each}
          </span>
        </div>
      {/each}
    </section>
  </div>
{:else}
  <p class="missing">No archive periods yet</p>
{/if}

<style>
  .sections {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: var(--nl-space-3) var(--nl-space-4);
  }

  h4 {
    font-size: 0.6875rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--nl-text-dim);
    margin-bottom: var(--nl-space-1);
  }

  .period + .period {
    margin-top: var(--nl-space-2);
    border-top: 1px solid var(--nl-border);
    padding-top: var(--nl-space-2);
  }

  .period-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--nl-space-2);
  }

  .cells {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(84px, 1fr));
    gap: var(--nl-space-1);
    margin-top: var(--nl-space-1);
  }

  .cell {
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding: var(--nl-space-0) var(--nl-space-1);
    border: 1px solid var(--nl-border);
    border-radius: var(--nl-radius);
    text-decoration: none;
    color: var(--nl-text);
  }

  .cell:hover {
    border-color: var(--nl-accent);
  }

  .cell-label {
    font-weight: 500;
    font-size: var(--nl-fs-sm);
  }

  .mini {
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }

  .year {
    font-weight: 600;
    min-width: 3.5em;
  }

  .row {
    display: flex;
    align-items: baseline;
    gap: var(--nl-space-2);
    padding: var(--nl-space-0) 0;
  }

  .row + .row {
    border-top: 1px solid var(--nl-border);
  }

  .months {
    display: flex;
    flex-wrap: wrap;
    gap: var(--nl-space-0) var(--nl-space-1);
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
