import { describe, expect, it } from 'vitest'
import { parseLoopPayload } from './live'

describe('parseLoopPayload', () => {
  it('strips unit suffixes from weewx-mqtt style keys', () => {
    expect(
      parseLoopPayload('{"outTemp_C": 14.2, "windSpeed_mps": 5.1}'),
    ).toEqual({ outTemp: 14.2, windSpeed: 5.1 })
  })

  it('keeps plain observation names', () => {
    expect(parseLoopPayload('{"outHumidity": 82, "windDir": 215}')).toEqual({
      outHumidity: 82,
      windDir: 215,
    })
  })

  it('maps dayRain onto rain', () => {
    const updates = parseLoopPayload('{"dayRain_mm": 1.4}')
    expect(updates?.rain).toBe(1.4)
  })

  it('accepts numeric strings and drops non-numeric values', () => {
    expect(
      parseLoopPayload('{"outTemp": "13.5", "usUnits": "metric", "x": null}'),
    ).toEqual({ outTemp: 13.5 })
  })

  it('returns null for invalid or empty payloads', () => {
    expect(parseLoopPayload('not json')).toBeNull()
    expect(parseLoopPayload('42')).toBeNull()
    expect(parseLoopPayload('{"note": "text only"}')).toBeNull()
  })
})
