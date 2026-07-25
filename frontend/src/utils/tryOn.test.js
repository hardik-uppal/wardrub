import { describe, expect, it } from 'vitest'
import { buildMultiTryOnGarments, getTryOnResultUrl } from './tryOn'

describe('multi-item try-on contract', () => {
  it('builds the API payload from selected garment objects', () => {
    expect(buildMultiTryOnGarments([
      {
        id: 'top-1',
        front_url: 'https://example.com/top.png',
        category: 'top',
      },
      {
        id: 'bottom-1',
        url: 'https://example.com/bottom.png',
        category: 'bottom',
      },
    ])).toEqual([
      { id: 'top-1', url: 'https://example.com/top.png', category: 'top' },
      { id: 'bottom-1', url: 'https://example.com/bottom.png', category: 'bottom' },
    ])
  })

  it('rejects IDs and malformed garments before making an API request', () => {
    expect(() => buildMultiTryOnGarments(['top-1'])).toThrow(
      'One or more selected garments are invalid',
    )
  })

  it('extracts the generated image URL from the API response', () => {
    expect(getTryOnResultUrl({ result_url: 'https://example.com/look.png' }))
      .toBe('https://example.com/look.png')
    expect(getTryOnResultUrl({ status: 'success' })).toBeNull()
  })
})
