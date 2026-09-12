import { expect, it } from 'vitest'
import { editionLabel } from './magazineEdition'

it('formats the returned calendar date explicitly in UTC', () => {
  expect(editionLabel('2026-09-12')).toBe('SEP 12, 2026 · UTC')
})

it.each([undefined, '', 'not-a-date', '2026-02-30', '2026-13-01'])('does not invent an edition for %s', value => {
  expect(editionLabel(value)).toBe('EDITION DATE UNAVAILABLE')
})
