<script lang="ts">
  import {
    applyChoice,
    readChoice,
    updateThemeColor,
    type ThemeChoice,
  } from '../lib/theme'

  let { skinMode }: { skinMode?: string } = $props()

  // svelte-ignore state_referenced_locally
  let choice = $state<ThemeChoice>(readChoice())

  const NEXT: Record<ThemeChoice, ThemeChoice> = {
    auto: 'light',
    light: 'dark',
    dark: 'auto',
  }
  const NAME: Record<ThemeChoice, string> = {
    auto: 'automatic',
    light: 'light',
    dark: 'dark',
  }

  $effect(() => {
    applyChoice(choice, skinMode)
  })

  $effect(() => {
    const media = matchMedia('(prefers-color-scheme: dark)')
    const onSystem = () => updateThemeColor()
    media.addEventListener('change', onSystem)
    return () => media.removeEventListener('change', onSystem)
  })

  function cycle() {
    choice = NEXT[choice]
  }
</script>

<button
  type="button"
  class="theme"
  onclick={cycle}
  title="Theme: {NAME[choice]}"
  aria-label="Switch to {NAME[NEXT[choice]]} theme"
>
  <svg viewBox="0 0 20 20" aria-hidden="true">
    {#if choice === 'auto'}
      <circle class="ring" cx="10" cy="10" r="6.5" />
      <path class="fill" d="M10 3.5 A6.5 6.5 0 0 1 10 16.5 Z" />
    {:else if choice === 'light'}
      <circle class="fill" cx="10" cy="10" r="4" />
      {#each [0, 45, 90, 135, 180, 225, 270, 315] as angle (angle)}
        <line
          class="ray"
          x1={10 + 6 * Math.cos((angle * Math.PI) / 180)}
          y1={10 + 6 * Math.sin((angle * Math.PI) / 180)}
          x2={10 + 8 * Math.cos((angle * Math.PI) / 180)}
          y2={10 + 8 * Math.sin((angle * Math.PI) / 180)}
        />
      {/each}
    {:else}
      <path
        class="fill"
        d="M13.5 12.5 A6 6 0 1 1 9 4.2 A4.8 4.8 0 0 0 13.5 12.5 Z"
      />
    {/if}
  </svg>
</button>

<style>
  .theme {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    margin: -12px 0; /* 44px touch target without growing the header */
    padding: 0;
    border: none;
    background: none;
    color: var(--nl-text-dim);
    cursor: pointer;
    border-radius: var(--nl-radius);
  }

  .theme:hover {
    color: var(--nl-text);
  }

  .theme:focus-visible {
    outline: 2px solid var(--nl-accent);
    outline-offset: 2px;
  }

  svg {
    width: 18px;
    height: 18px;
  }

  .ring {
    fill: none;
    stroke: currentColor;
    stroke-width: 1.5;
  }

  .fill {
    fill: currentColor;
  }

  .ray {
    stroke: currentColor;
    stroke-width: 1.5;
    stroke-linecap: round;
  }
</style>
