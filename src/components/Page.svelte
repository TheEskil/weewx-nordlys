<script lang="ts">
  import type { NordlysPayload, PageConfig } from '../lib/types'
  import Tile from './Tile.svelte'
  import PeriodPicker from './PeriodPicker.svelte'

  let {
    page,
    payload,
  }: {
    page: PageConfig
    payload: NordlysPayload
  } = $props()

  // A period picker rides on the first row, opposite its title.
  const showPicker = $derived(Boolean(page.picker || payload.period))
</script>

{#each page.layout as row, i (i)}
  <section>
    {#if row.title || (i === 0 && showPicker)}
      <div class="head">
        {#if row.title}<h2>{row.title}</h2>{/if}
        {#if i === 0 && showPicker}<PeriodPicker {page} {payload} />{/if}
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

  .head :global(.picker) {
    margin-left: auto;
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
