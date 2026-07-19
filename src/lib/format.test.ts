import { describe, expect, it } from 'vitest'
import { degToCompass, formatTrend, formatValue } from './format'

describe('formatValue', () => {
  it('formats with the given decimals', () => {
    expect(formatValue(13.64, 1)).toBe('13.6')
    expect(formatValue(79, 0)).toBe('79')
  })

  it('renders missing values as a dash', () => {
    expect(formatValue(null)).toBe('-')
    expect(formatValue(undefined)).toBe('-')
    expect(formatValue(NaN)).toBe('-')
  })
})

describe('degToCompass', () => {
  it('maps degrees to 16-point compass names', () => {
    expect(degToCompass(0)).toBe('N')
    expect(degToCompass(215)).toBe('SW')
    expect(degToCompass(202.5)).toBe('SSW')
    expect(degToCompass(348.75)).toBe('N')
  })

  it('normalizes out-of-range degrees', () => {
    expect(degToCompass(360)).toBe('N')
    expect(degToCompass(-90)).toBe('W')
    expect(degToCompass(450)).toBe('E')
  })

  it('handles missing values', () => {
    expect(degToCompass(null)).toBe('-')
  })
})

describe('formatTrend', () => {
  it('shows direction and magnitude', () => {
    expect(formatTrend(0.4, 1)).toBe('↗ 0.4')
    expect(formatTrend(-1.2, 1)).toBe('↘ 1.2')
    expect(formatTrend(0, 1)).toBe('→ 0.0')
  })
})
