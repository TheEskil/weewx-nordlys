<script lang="ts">
  import type { NordlysPayload, PageConfig } from '../lib/types'

  let { page, payload }: { page: PageConfig; payload: NordlysPayload } =
    $props()

  // Live pages declare a picker kind; archive pages take it from the
  // period they represent.
  const kind = $derived(page.picker ?? payload.period?.kind)
  const links = $derived(
    kind
      ? [
          ...(payload.archives?.[`${kind}s` as 'weeks' | 'months' | 'years'] ??
            []),
        ].reverse()
      : [],
  )
  const period = $derived(payload.period)
  // On an archive page the current period is selected; on a live page the
  // synthetic "This <kind>" entry is.
  const selected = $derived(period?.id ?? '__current__')

  function onChange(event: Event) {
    const value = (event.currentTarget as HTMLSelectElement).value
    if (value === '__back__') {
      // Return to the live page's canonical URL (week.html/month.html/…).
      window.location.href = `${kind}.html`
    } else if (value !== '__current__') {
      const link = links.find((l) => l.id === value)
      if (link) window.location.href = link.page
    }
  }
</script>

{#if kind && links.length > 0}
  <select
    class="picker"
    aria-label="Jump to a {kind}"
    value={selected}
    onchange={onChange}
  >
    {#if period}
      <option value="__back__">‹ Current</option>
    {:else}
      <option value="__current__">This {kind}</option>
    {/if}
    {#each links as link (link.id)}
      <option value={link.id}>{link.label}</option>
    {/each}
  </select>
{/if}

<style>
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
