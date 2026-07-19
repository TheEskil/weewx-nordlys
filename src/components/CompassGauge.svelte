<script lang="ts">
  import type { Observation } from '../lib/types'
  import { degToCompass, formatValue } from '../lib/format'

  let { obs, title }: { obs: Observation; title?: string } = $props()

  const CX = 50
  const CY = 41
  const R = 30

  function point(angle: number, radius: number): [number, number] {
    const rad = (angle * Math.PI) / 180
    return [CX + radius * Math.sin(rad), CY - radius * Math.cos(rad)]
  }

  const cardinals = [
    { label: 'N', angle: 0 },
    { label: 'E', angle: 90 },
    { label: 'S', angle: 180 },
    { label: 'W', angle: 270 },
  ]
  const intercardinals = [45, 135, 225, 315]

  const needle = $derived(
    obs.value === null
      ? null
      : { outer: point(obs.value, R), inner: point(obs.value, R - 8) },
  )
</script>

<article>
  <svg
    viewBox="0 0 100 82"
    role="img"
    aria-label="{title ?? obs.label}: {degToCompass(obs.value)} ({formatValue(
      obs.value,
      0,
    )}°)"
  >
    <circle class="track" cx={CX} cy={CY} r={R} />
    {#each intercardinals as angle (angle)}
      {@const [x1, y1] = point(angle, R - 3)}
      {@const [x2, y2] = point(angle, R)}
      <line class="tick" {x1} {y1} {x2} {y2} />
    {/each}
    {#each cardinals as c (c.label)}
      {@const [x, y] = point(c.angle, R + 7)}
      <text class="cardinal" {x} y={y + 2}>{c.label}</text>
    {/each}
    {#if needle}
      <line
        class="needle"
        x1={needle.inner[0]}
        y1={needle.inner[1]}
        x2={needle.outer[0]}
        y2={needle.outer[1]}
      />
    {/if}
    <text class="value" x={CX} y={CY - 1}>{degToCompass(obs.value)}</text>
    <text class="degrees nl-num" x={CX} y={CY + 11}>
      {formatValue(obs.value, 0)}°
    </text>
  </svg>
  <h3>{title ?? obs.label}</h3>
</article>

<style>
  article {
    text-align: center;
  }

  svg {
    display: block;
    width: 100%;
    max-width: 180px;
    margin: 0 auto;
  }

  .track {
    fill: none;
    stroke: var(--nl-border);
    stroke-width: 1.5;
  }

  .tick {
    stroke: var(--nl-border);
    stroke-width: 1.5;
  }

  .needle {
    stroke: var(--nl-accent);
    stroke-width: 3;
    stroke-linecap: round;
  }

  text {
    text-anchor: middle;
  }

  .cardinal {
    font-size: 6px;
    fill: var(--nl-text-dim);
  }

  .value {
    font-size: 12px;
    font-weight: 600;
    fill: var(--nl-text);
  }

  .degrees {
    font-size: 6.5px;
    fill: var(--nl-text-dim);
  }

  h3 {
    font-size: var(--nl-fs-sm);
    font-weight: 500;
    color: var(--nl-text-dim);
    margin-top: var(--nl-space-1);
  }
</style>
