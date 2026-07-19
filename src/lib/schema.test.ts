import { describe, expect, it } from 'vitest'
import Ajv from 'ajv/dist/2020'
import schema from '../../docs/config.schema.json'
import today from '../../fixtures/today.json'
import extremes from '../../fixtures/extremes.json'

const ajv = new Ajv({ allErrors: true })
const validate = ajv.compile(schema)

describe('config.schema.json', () => {
  it('accepts the today fixture config', () => {
    const valid = validate(today.config)
    expect(validate.errors ?? []).toEqual([])
    expect(valid).toBe(true)
  })

  it('accepts the extremes fixture config', () => {
    const valid = validate(extremes.config)
    expect(validate.errors ?? []).toEqual([])
    expect(valid).toBe(true)
  })

  it('rejects an unknown tile type', () => {
    expect(
      validate({
        pages: [
          {
            id: 'p',
            title: 'P',
            layout: [{ tiles: [{ type: 'sparkline' }] }],
          },
        ],
      }),
    ).toBe(false)
  })

  it('rejects a live config without a websocket broker', () => {
    expect(
      validate({ live: { broker: 'http://x' }, pages: [] }),
    ).toBe(false)
  })

  it('accepts a history tile', () => {
    const valid = validate({
      pages: [
        {
          id: 'today',
          title: 'Today',
          layout: [
            {
              tiles: [
                {
                  type: 'history',
                  obs: ['outTemp', 'windGust', 'rain'],
                  options: { span: 'day' },
                },
              ],
            },
          ],
        },
      ],
    })
    expect(validate.errors ?? []).toEqual([])
    expect(valid).toBe(true)
  })
})
