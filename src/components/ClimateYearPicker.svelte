<script lang="ts">
  import type { ClimateSlice, NordlysPayload } from '../lib/types'

  let { payload }: { payload: NordlysPayload } = $props()

  const years = $derived(payload.climatology?.years ?? [])
  const currentYear = $derived(years[0]?.year)

  // Snapshot the embedded current year so it can be restored without a
  // fetch. payload is App's reactive state; mutating it swaps the tiles.
  // svelte-ignore state_referenced_locally
  const embedded = {
    days: payload.climatology?.days,
    calendar: payload.climatology?.calendar,
    stats: payload.stats?.year,
  }
  const cache = new Map<string, ClimateSlice>()

  // svelte-ignore state_referenced_locally
  let selected = $state(currentYear)
  let loading = $state(false)
  let error = $state('')

  function apply(days: unknown, calendar: unknown, yearStats: unknown) {
    if (payload.climatology) {
      payload.climatology.days = days as never
      payload.climatology.calendar = calendar as never
    }
    if (payload.stats) payload.stats.year = yearStats as never
  }

  async function onChange(event: Event) {
    const year = (event.currentTarget as HTMLSelectElement).value
    selected = year
    error = ''
    if (year === currentYear) {
      apply(embedded.days, embedded.calendar, embedded.stats)
      return
    }
    let slice = cache.get(year)
    if (!slice) {
      loading = true
      try {
        const res = await fetch(`climate-${year}.json`)
        if (!res.ok) throw new Error(String(res.status))
        slice = (await res.json()) as ClimateSlice
        cache.set(year, slice)
      } catch {
        error = `Couldn't load ${year}`
        selected = currentYear
        return
      } finally {
        loading = false
      }
    }
    apply(slice.climatology?.days, slice.climatology?.calendar, slice.stats?.year)
  }
</script>

{#if years.length > 1}
  <span class="wrap">
    {#if loading}<span class="status" aria-live="polite">…</span>{/if}
    {#if error}<span class="status error" aria-live="polite">{error}</span>{/if}
    <select
      class="picker"
      aria-label="Climate year"
      value={selected}
      onchange={onChange}
    >
      {#each years as y (y.year)}
        <option value={y.year}>{y.label}</option>
      {/each}
    </select>
  </span>
{/if}

<style>
  .wrap {
    display: inline-flex;
    align-items: center;
    gap: var(--nl-space-1);
  }

  .status {
    font-size: var(--nl-fs-sm);
    color: var(--nl-text-dim);
  }

  .status.error {
    color: var(--nl-alert);
  }

  .picker {
    font: inherit;
    font-size: var(--nl-fs-sm);
    color: var(--nl-text);
    background: var(--nl-surface);
    border: 1px solid var(--nl-border);
    border-radius: var(--nl-radius);
    padding: var(--nl-space-0) var(--nl-space-1);
    cursor: pointer;
    max-width: 100%;
  }

  .picker:hover {
    border-color: var(--nl-text-dim);
  }
</style>
