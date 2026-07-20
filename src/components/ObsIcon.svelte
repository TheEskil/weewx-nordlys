<script lang="ts">
  // A small hairline icon naming what an observation tile measures, shown in
  // the tile's top-right corner. Line style matches Glyph.svelte.
  let { obs, label }: { obs: string; label?: string } = $props()

  type Icon =
    | 'thermometer'
    | 'droplet'
    | 'wind'
    | 'rain'
    | 'sun'
    | 'cloud'
    | 'gauge'
    | 'compass'

  // Map observation keys to a representative icon. Unknown obs get none.
  const MAP: Record<string, Icon> = {
    outTemp: 'thermometer',
    appTemp: 'thermometer',
    windchill: 'thermometer',
    heatindex: 'thermometer',
    inTemp: 'thermometer',
    dewpoint: 'droplet',
    outHumidity: 'droplet',
    inHumidity: 'droplet',
    ET: 'droplet',
    barometer: 'gauge',
    pressure: 'gauge',
    windSpeed: 'wind',
    windGust: 'wind',
    windrun: 'wind',
    windDir: 'compass',
    rain: 'rain',
    rainRate: 'rain',
    UV: 'sun',
    radiation: 'sun',
    luminosity: 'sun',
    cloudbase: 'cloud',
  }

  const icon = $derived(MAP[obs])
</script>

{#if icon}
  <svg
    class="obs-icon"
    viewBox="0 0 24 24"
    role="img"
    aria-label={label ?? icon}
  >
    {#if icon === 'thermometer'}
      <path d="M14 14.76V5a2 2 0 0 0-4 0v9.76a4 4 0 1 0 4 0z" />
    {:else if icon === 'droplet'}
      <path d="M12 2.7l5.66 5.66a8 8 0 1 1-11.31 0z" />
    {:else if icon === 'wind'}
      <path
        d="M9.6 4.6A2 2 0 1 1 11 8H2m10.6 11.4A2 2 0 1 0 14 16H2m15.7-8.3A2.5 2.5 0 1 1 19.5 12H2"
      />
    {:else if icon === 'rain'}
      <path d="M20 16.6A5 5 0 0 0 18 7h-1.26A8 8 0 1 0 4 15.25" />
      <path d="M8 19v2M12 21v2M16 19v2" />
    {:else if icon === 'sun'}
      <circle cx="12" cy="12" r="5" />
      <path
        d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
      />
    {:else if icon === 'cloud'}
      <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z" />
    {:else if icon === 'gauge'}
      <path d="M4 15a8 8 0 1 1 16 0" />
      <path d="M12 15l4-3" />
    {:else if icon === 'compass'}
      <circle cx="12" cy="12" r="9" />
      <path d="M16.2 7.8l-2.1 6.3-6.3 2.1 2.1-6.3z" />
    {/if}
  </svg>
{/if}

<style>
  .obs-icon {
    width: 18px;
    height: 18px;
    flex: none;
    fill: none;
    stroke: var(--nl-text-dim);
    stroke-width: 1.6;
    stroke-linecap: round;
    stroke-linejoin: round;
    opacity: 0.45;
  }
</style>
