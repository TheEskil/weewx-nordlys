<script lang="ts">
  import type { ArchiveLink, NordlysPayload } from '../lib/types'

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

  function monthsOf(
    months: ArchiveLink[],
    kind: 'page' | 'noaa',
  ): { label: string; href: string; id: string }[] {
    return months.map((m) => ({
      label: m.month ?? m.id,
      href: kind === 'page' ? m.page : m.noaa,
      id: m.id,
    }))
  }
</script>

{#if grouped.length > 0}
  <div class="sections">
    <section>
      <h4>Archive pages</h4>
      {#each grouped as { year, months } (year.id)}
        <div class="row">
          <a class="year nl-num" href={year.page}>{year.label}</a>
          <span class="months">
            {#each monthsOf(months, 'page') as m (m.id)}
              <a href={m.href}>{m.label}</a>
            {/each}
          </span>
        </div>
      {/each}
    </section>
    <section>
      <h4>NOAA reports</h4>
      {#each grouped as { year, months } (year.id)}
        <div class="row">
          <a class="year nl-num" href={year.noaa}>{year.label}</a>
          <span class="months">
            {#each monthsOf(months, 'noaa') as m (m.id)}
              <a href={m.href}>{m.label}</a>
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
    gap: var(--nl-space-2) var(--nl-space-4);
  }

  h4 {
    font-size: 0.6875rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--nl-text-dim);
    margin-bottom: var(--nl-space-1);
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

  .year {
    font-weight: 600;
    min-width: 3.5em;
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
