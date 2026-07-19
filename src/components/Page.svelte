<script lang="ts">
  import type { NordlysPayload, PageConfig } from '../lib/types'
  import Tile from './Tile.svelte'

  let {
    page,
    payload,
  }: {
    page: PageConfig
    payload: NordlysPayload
  } = $props()
</script>

{#each page.layout as row, i (i)}
  <section>
    {#if row.title}
      <h2>{row.title}</h2>
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

  h2 {
    font-size: var(--nl-fs-sm);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--nl-text-dim);
    margin-bottom: var(--nl-space-2);
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
