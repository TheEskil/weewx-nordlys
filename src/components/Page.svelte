<script lang="ts">
  import type { NordlysPayload, PageConfig } from '../lib/types'
  import { formatsOf, strftime } from '../lib/strftime'
  import Tile from './Tile.svelte'
  import PeriodPicker from './PeriodPicker.svelte'
  import ClimateYearPicker from './ClimateYearPicker.svelte'

  let {
    page,
    payload,
  }: {
    page: PageConfig
    payload: NordlysPayload
  } = $props()

  // A period picker rides on the first row, opposite its title.
  const showPicker = $derived(Boolean(page.picker || payload.period))

  // The Climate page (year-scoped content, no navigation picker) gets a
  // year picker that swaps data in place instead of navigating.
  const isClimate = $derived(
    !page.picker &&
      !payload.period &&
      page.layout.some((row) =>
        row.tiles.some(
          (t) =>
            t.type === 'climatology' ||
            (t.type === 'chart' && t.options?.chart === 'calendar') ||
            (t.type === 'table' &&
              t.options?.table === 'stats' &&
              t.options?.span === 'year'),
        ),
      ),
  )
  const showClimateYear = $derived(
    isClimate && (payload.climatology?.years?.length ?? 0) > 1,
  )

  // The report's generation time rides inline on the live landing page's first
  // title (e.g. "Now · 20 Jul 2026, 14:30") - it marks the freshness of the
  // current conditions. Other pages (yesterday, week, …) show past-period data,
  // where a generation timestamp beside the title would only mislead, so it is
  // left to the footer there.
  const isLanding = $derived(payload.config.pages[0]?.id === page.id)
  const fmts = $derived(formatsOf(payload))
  const generated = $derived(strftime(payload.meta.generatedAt, fmts.datetime))
  const showGenerated = $derived(isLanding && !showPicker && !showClimateYear)

  // A row may declare `date = <span>` to append that period's date to its
  // title, e.g. "Yesterday's Observations · 19 Jul 2026". Resolved against the
  // report generation time (yesterday = one day back).
  const DATE_OFFSET_S: Record<string, number> = { yesterday: 86400, day: 0 }
  function rowDate(span: string | undefined): string | null {
    if (span === undefined) return null
    const offset = DATE_OFFSET_S[span]
    if (offset === undefined) return null
    return strftime(payload.meta.generatedAt - offset, fmts.date_year)
  }
</script>

{#each page.layout as row, i (i)}
  {@const rd = rowDate(row.date)}
  <section>
    {#if row.title || (i === 0 && (showPicker || showClimateYear))}
      <div class="head">
        {#if row.title}
          <h2>
            {row.title}{#if i === 0 && showGenerated}<span class="h2-date"
                >&nbsp;&middot; {generated}</span
              >{:else if rd}<span class="h2-date">&nbsp;&middot; {rd}</span>{/if}
          </h2>
        {/if}
        {#if i === 0 && showPicker}<PeriodPicker {page} {payload} />{/if}
        {#if i === 0 && showClimateYear}<ClimateYearPicker {payload} />{/if}
      </div>
    {/if}
    <div class="grid" style:--row-cols={row.columns ?? 4}>
      {#each row.tiles as tile, j (j)}
        <Tile {tile} {payload} />
      {/each}
    </div>
  </section>
{/each}

<style>
  section + section {
    margin-top: var(--nl-space-4);
  }

  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--nl-space-2);
    margin-bottom: var(--nl-space-2);
    min-height: 1.6rem;
  }

  h2 {
    font-size: var(--nl-fs-sm);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--nl-text-dim);
  }

  .head :global(.picker),
  .head :global(.wrap) {
    margin-left: auto;
  }

  /* The generated date sits inline after the section title (e.g. "Now"),
     but reads as plain text, not part of the uppercase heading. */
  .h2-date {
    font-weight: 400;
    letter-spacing: normal;
    text-transform: none;
    color: var(--nl-text-dim);
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(var(--row-cols), minmax(0, 1fr));
    gap: var(--nl-space-2);
  }

  @media (max-width: 900px) {
    .grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 560px) {
    .grid {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
