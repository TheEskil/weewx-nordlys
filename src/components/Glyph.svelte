<script lang="ts">
  type Kind = 'min' | 'avg' | 'max' | 'rising' | 'falling' | 'steady'

  let { kind, label }: { kind: Kind; label: string } = $props()

  // 10x10 viewBox, hairline stroke; shares a baseline with adjacent text.
  const PATHS: Record<Kind, string> = {
    min: 'M2 3.8 L5 6.6 L8 3.8',
    max: 'M2 6.2 L5 3.4 L8 6.2',
    avg: 'M2 5 H8',
    rising: 'M2.4 7.6 L7.6 2.4 M7.6 2.4 L4.9 2.7 M7.6 2.4 L7.3 5.1',
    falling: 'M2.4 2.4 L7.6 7.6 M7.6 7.6 L4.9 7.3 M7.6 7.6 L7.3 4.9',
    steady: 'M2 5 H7.3 M5.9 3.6 L7.6 5 L5.9 6.4',
  }
</script>

<svg class="glyph" viewBox="0 0 10 10" role="img" aria-label={label}>
  <path d={PATHS[kind]} />
</svg>

<style>
  .glyph {
    width: 10px;
    height: 10px;
    flex: none;
  }

  .glyph path {
    fill: none;
    stroke: var(--nl-text-dim);
    stroke-width: 1.5;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
</style>
