import { describe, expect, it } from 'vitest'
import { strftime } from './strftime'

// 2026-07-19 16:55:07 local time.
const ts = new Date(2026, 6, 19, 16, 55, 7).getTime() / 1000

describe('strftime', () => {
  it('formats 24-hour time', () => {
    expect(strftime(ts, '%H:%M')).toBe('16:55')
    expect(strftime(ts, '%H:%M:%S')).toBe('16:55:07')
  })

  it('formats European dates with abbreviated months', () => {
    expect(strftime(ts, '%d %b')).toBe('19 Jul')
    expect(strftime(ts, '%d %b %Y')).toBe('19 Jul 2026')
    expect(strftime(ts, '%d %b %Y, %H:%M')).toBe('19 Jul 2026, 16:55')
  })

  it('formats weekday and numeric month', () => {
    expect(strftime(ts, '%a %H:%M')).toBe('Sun 16:55')
    expect(strftime(ts, '%m')).toBe('07')
  })

  it('supports 12-hour and meridiem', () => {
    expect(strftime(ts, '%I %p')).toBe('04 PM')
    const morning = new Date(2026, 6, 19, 6, 5, 0).getTime() / 1000
    expect(strftime(morning, '%I:%M %p')).toBe('06:05 AM')
    const midnight = new Date(2026, 6, 19, 0, 0, 0).getTime() / 1000
    expect(strftime(midnight, '%I %p')).toBe('12 AM')
  })

  it('passes through literals and escapes %%', () => {
    expect(strftime(ts, 'Generated %d %b %Y')).toBe('Generated 19 Jul 2026')
    expect(strftime(ts, '100%%')).toBe('100%')
  })
})
