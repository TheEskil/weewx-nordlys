// @vitest-environment happy-dom
import { describe, expect, it } from 'vitest'
import { parseEmbeddedPayload } from './payload'

function parse(html: string): Document {
  return new DOMParser().parseFromString(html, 'text/html')
}

describe('parseEmbeddedPayload', () => {
  it('parses the embedded #nordlys-data JSON', () => {
    const doc = parse(
      '<script id="nordlys-data" type="application/json">{"meta":{"generatedAt":42}}</script>',
    )
    expect(parseEmbeddedPayload(doc).meta.generatedAt).toBe(42)
  })

  it('throws when the payload element is missing', () => {
    expect(() => parseEmbeddedPayload(parse('<div></div>'))).toThrow(
      /missing #nordlys-data/,
    )
  })

  it('throws when the payload element is empty', () => {
    expect(() =>
      parseEmbeddedPayload(parse('<script id="nordlys-data"></script>')),
    ).toThrow(/missing #nordlys-data/)
  })
})
