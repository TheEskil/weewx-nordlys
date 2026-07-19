import { describe, expect, it } from 'vitest'
import { cssColor, valueColor } from './color'

describe('cssColor', () => {
  it('wraps token names in the --nl- custom property', () => {
    expect(cssColor('accent-2')).toBe('var(--nl-accent-2)')
  })

  it('passes literal colors through', () => {
    expect(cssColor('#8be9fd')).toBe('#8be9fd')
    expect(cssColor('rgb(1, 2, 3)')).toBe('rgb(1, 2, 3)')
  })

  it('returns undefined for no color', () => {
    expect(cssColor(undefined)).toBeUndefined()
  })
})

describe('valueColor', () => {
  const options = { cold_below: 0, hot_above: 25 }

  it('applies semantic tokens beyond the thresholds', () => {
    expect(valueColor(-3, options)).toBe('var(--nl-cold)')
    expect(valueColor(28, options)).toBe('var(--nl-hot)')
  })

  it('uses the configured color inside the thresholds', () => {
    expect(valueColor(12, options)).toBeUndefined()
    expect(valueColor(12, { ...options, color: 'accent-3' })).toBe(
      'var(--nl-accent-3)',
    )
  })

  it('bounds are exclusive', () => {
    expect(valueColor(0, options)).toBeUndefined()
    expect(valueColor(25, options)).toBeUndefined()
  })

  it('ignores thresholds for missing values', () => {
    expect(valueColor(null, options)).toBeUndefined()
    expect(valueColor(null, { color: 'warm' })).toBe('var(--nl-warm)')
  })
})
