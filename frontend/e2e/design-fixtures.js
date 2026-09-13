import { Buffer } from 'node:buffer'
import { expect } from '@playwright/test'
const svg = (shape, color) =>
  `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="240" height="300" viewBox="0 0 240 300"><path d="${shape}" fill="${color}" stroke="#596452" stroke-width="2"/></svg>`)}`
const shirt =
  'M75 40 L45 55 L15 115 L55 130 L70 105 L70 260 L170 260 L170 105 L185 130 L225 115 L195 55 L165 40 Q120 70 75 40 Z'
const trousers = 'M65 35 L175 35 L185 270 L130 270 L120 110 L110 270 L55 270 Z'
export const photo = {
  name: 'outfit.png',
  mimeType: 'image/png',
  buffer: Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/lWQAAAAASUVORK5CYII=',
    'base64',
  ),
}
export async function setupDesign(page, { avatar = false } = {}) {
  const items = [
    {
      id: 'a',
      name: 'Linen shirt',
      category: 'top',
      readiness: 'ready',
      version: 0,
      url: svg(shirt, '#e1dccb'),
    },
    {
      id: 'b',
      name: 'Everyday trousers',
      category: 'bottom',
      readiness: 'ready',
      version: 0,
      url: svg(trousers, '#565d4c'),
    },
    {
      id: 'c',
      name: 'Blue tee',
      category: 'top',
      readiness: 'ready',
      version: 0,
      url: svg(shirt, '#8da5af'),
    },
  ]
  let avatarUrl = avatar ? items[0].url : null
  const history = []
  const state = {
    version: 0,
    outfits: {},
    days: {},
    locations: {},
    styles: [],
    feedback: {},
  }
  const look = (id = 'a') => ({
    id: `outfit-${id}`,
    title: id === 'a' ? 'An easy start' : 'A little blue',
    garment_ids: [id, 'b'],
    why_it_works:
      'A combination from your wardrobe. All pieces are marked ready to wear.',
  })
  const failures = { generation: false, save: false, feed: false }
  await page.addInitScript(() =>
    localStorage.setItem(
      'dev_mock_user',
      JSON.stringify({ uid: 'design-test', email: 'design@wardrub.test' }),
    ),
  )
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    const method = route.request().method()
    let body = { status: 'ok' },
      status = 200
    if (path === '/api/avatar') body = { avatar_url: avatarUrl }
    else if (path === '/api/wardrobe')
      body = {
        garments: items.map((g) => ({
          ...g,
          front_url: g.url,
          description: { short: g.name },
        })),
      }
    else if (path === '/api/profile') body = { profile: null }
    else if (path === '/api/check-legacy-data')
      body = { has_legacy_data: false }
    else if (path === '/api/closet-state') body = { garments: items }
    else if (path === '/api/closet-library') body = state
    else if (path === '/api/closet-library/actions') {
      const input = route.request().postDataJSON()
      expect(input.expected_version).toBe(state.version)
      if (failures.save) {
        status = 503
        body = { detail: 'Save was not confirmed.' }
      } else {
        const outfit = {
          ...look(input.garment_ids?.[0]),
          title: input.title,
          garment_ids: input.garment_ids,
        }
        if (input.action === 'save') state.outfits[outfit.id] = outfit
        if (input.action === 'delete') delete state.outfits[input.outfit_id]
        if (['plan', 'wore'].includes(input.action))
          state.days[input.day] = { ...outfit, worn: input.action === 'wore' }
        if (input.action === 'unwear') state.days[input.day].worn = false
        if (input.action === 'unplan') delete state.days[input.day]
        if (input.action === 'location')
          input.garment_ids.forEach(
            (id) => (state.locations[id] = input.location),
          )
        if (input.action === 'styles') state.styles = input.styles
        if (input.action === 'feedback')
          state.feedback[input.operation_id] = {
            id: input.operation_id,
            outfit_id: outfit.id,
            day: input.day,
            reason: input.reason,
          }
        if (input.action === 'undo_feedback')
          delete state.feedback[input.outfit_id]
        state.version++
        body = state
      }
    } else if (path === '/api/closet-state/batch') {
      const { changes } = route.request().postDataJSON()
      for (const change of changes) {
        const item = items.find((g) => g.id === change.id)
        expect(change.expected_version).toBe(item.version)
        item.version++
        item.readiness = change.readiness
      }
      body = { garments: items }
    } else if (path === '/api/magazine-feed') {
      if (failures.feed) {
        status = 503
        body = { detail: 'Suggestions unavailable.' }
      } else {
        const day = new URL(route.request().url()).searchParams.get('local_day')
        const skipped = Object.values(state.feedback)
          .filter((entry) => entry.day === day)
          .map((entry) => entry.outfit_id)
        const top = items.find(
          (g) =>
            g.category === 'top' &&
            g.readiness !== 'laundry' &&
            !skipped.includes(look(g.id).id),
        )
        body = {
          status: 'success',
          feed: {
            date: new Date().toISOString().slice(0, 10),
            policy_version: 'closet-rules-v1',
            weather_status: 'unavailable',
            skipped_for_day: skipped.length > 0,
            cover_look:
              top && items[1].readiness !== 'laundry' ? look(top.id) : null,
            daily_fits: [],
          },
        }
      }
    } else if (path === '/api/outfits/swap')
      body = {
        status: 'success',
        look: look(route.request().postDataJSON().with_item_id),
      }
    else if (path === '/api/create-avatar') {
      expect(route.request().postData()).toContain('false')
      body = {
        candidate_id: '11111111-1111-4111-8111-111111111111',
        avatar_url: items[0].url,
      }
    } else if (path.includes('/avatar-candidates/')) {
      avatarUrl = items[0].url
      body = { avatar_url: avatarUrl, status: 'active' }
    } else if (path === '/api/try-on-multiple') {
      const input = route.request().postDataJSON()
      expect(input.garments.map((g) => g.id)).toEqual(['a', 'b'])
      if (failures.generation) {
        status = 503
        body = { detail: 'Preview unavailable. Try again.' }
      } else {
        const result = {
          id: 'render-1',
          url: items[0].url,
          garment_ids: ['a', 'b'],
          created_at: '2026-09-13T00:00:00Z',
        }
        history.push(result)
        body = {
          status: 'success',
          result_url: result.url,
          id: result.id,
          garment_count: 2,
        }
      }
    } else if (path === '/api/try-on/history')
      body = { results: history, next_offset: null }
    else if (path.startsWith('/api/look/') && method === 'DELETE') {
      history.length = 0
    }
    await route.fulfill({ status, json: body })
  })
  return { items, state, history, failures }
}
