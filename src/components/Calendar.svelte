<script lang="ts">
  import type { NordlysPayload } from '../lib/types'
  import { formatValue } from '../lib/format'
  import { formatsOf, strftime } from '../lib/strftime'

  let { payload }: { payload: NordlysPayload } = $props()

  const fmts = $derived(formatsOf(payload))

  const calendar = $derived(payload.climatology?.calendar)

  const CELL = 12
  const GAP = 3
  const TOP = 16 // month labels
  const LEFT = 26 // weekday labels

  const cells = $derived.by(() => {
    if (!calendar) return []
    return calendar.days.map(([ts, value]) => {
      const date = new Date(ts * 1000)
      return { ts, value, date, weekday: (date.getDay() + 6) % 7 } // Mon = 0
    })
  })

  /** Column index per cell, advancing every Monday. */
  const layout = $derived.by(() => {
    let week = 0
    return cells.map((cell, i) => {
      if (i > 0 && cell.weekday === 0) week += 1
      return { ...cell, week }
    })
  })

  const weeks = $derived(
    layout.length > 0 ? layout[layout.length - 1].week + 1 : 0,
  )

  const range = $derived.by(() => {
    const values = cells
      .map((c) => c.value)
      .filter((v): v is number => v !== null)
    if (values.length === 0) return { min: 0, max: 1 }
    return { min: Math.min(...values), max: Math.max(...values) }
  })

  function heat(value: number): number {
    if (range.max === range.min) return 50
    return Math.round(((value - range.min) / (range.max - range.min)) * 100)
  }

  const monthLabels = $derived.by(() => {
    const labels: { week: number; text: string }[] = []
    let lastMonth = -1
    for (const cell of layout) {
      const month = cell.date.getMonth()
      if (month !== lastMonth) {
        labels.push({
          week: cell.week,
          text: strftime(cell.ts, '%b'),
        })
        lastMonth = month
      }
    }
    // Drop a first label crowding the second one.
    return labels.filter(
      (l, i) => i === 0 || l.week - labels[i - 1].week >= 3,
    )
  })

  const width = $derived(LEFT + weeks * (CELL + GAP))
  const height = TOP + 7 * (CELL + GAP)
  const weekdayLabels = [
    { row: 0, text: 'Mon' },
    { row: 2, text: 'Wed' },
    { row: 4, text: 'Fri' },
  ]

  function tooltip(cell: { ts: number; value: number | null }): string {
    const day = strftime(cell.ts, fmts.date_year)
    if (cell.value === null || !calendar) return `${day}: no data`
    return `${day}: ${formatValue(cell.value, 1)} ${calendar.unit}`
  }
</script>

{#if calendar}
  <div class="scroll">
    <!-- Natural-size cells; horizontal scroll for a full year on
         narrow screens (never stretched to the container). -->
    <svg viewBox="0 0 {width} {height}" width={width} height={height}
      role="img" aria-label="{calendar.label} calendar heatmap">
      {#each monthLabels as label (label.week + label.text)}
        <text class="month" x={LEFT + label.week * (CELL + GAP)} y="10">
          {label.text}
        </text>
      {/each}
      {#each weekdayLabels as label (label.text)}
        <text
          class="weekday"
          x={LEFT - 6}
          y={TOP + label.row * (CELL + GAP) + CELL - 3}
        >
          {label.text}
        </text>
      {/each}
      {#each layout as cell (cell.ts)}
        <rect
          class="cell"
          class:empty={cell.value === null}
          x={LEFT + cell.week * (CELL + GAP)}
          y={TOP + cell.weekday * (CELL + GAP)}
          width={CELL}
          height={CELL}
          rx="2.5"
          style:fill={cell.value === null
            ? undefined
            : `color-mix(in oklab, var(--nl-hot) ${heat(cell.value)}%, var(--nl-cold))`}
        >
          <title>{tooltip(cell)}</title>
        </rect>
      {/each}
    </svg>
  </div>
  <div class="legend nl-num">
    <span>{formatValue(range.min, 1)} {calendar.unit}</span>
    <span class="ramp" aria-hidden="true"></span>
    <span>{formatValue(range.max, 1)} {calendar.unit}</span>
    <span class="what">{calendar.label} ({calendar.aggregate})</span>
  </div>
{:else}
  <p class="missing">No calendar data</p>
{/if}

<style>
  .scroll {
    overflow-x: auto;
  }

  svg {
    display: block;
  }

  .month,
  .weekday {
    font-size: 9px;
    fill: var(--nl-text-dim);
  }

  .weekday {
    text-anchor: end;
  }

  .cell.empty {
    fill: none;
    stroke: var(--nl-border);
    stroke-width: 1;
  }

  .legend {
    display: flex;
    align-items: center;
    gap: var(--nl-space-1);
    margin-top: var(--nl-space-1);
    font-size: var(--nl-fs-sm);
    color: var(--nl-text-dim);
  }

  .ramp {
    width: 72px;
    height: 8px;
    border-radius: 4px;
    background: linear-gradient(90deg, var(--nl-cold), var(--nl-hot));
  }

  .what {
    margin-left: auto;
  }

  .missing {
    color: var(--nl-text-dim);
    font-size: var(--nl-fs-sm);
  }
</style>
