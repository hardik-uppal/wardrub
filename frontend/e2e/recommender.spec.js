import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const image = 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22300%22%3E%3Crect width=%22200%22 height=%22300%22 fill=%22%23eeeeef%22/%3E%3C/svg%3E'

test('swap, laundry, return and undo preserve a usable daily loop', async ({ page }, testInfo) => {
  const states = [
    { id: 'a', name: 'White tee', category: 'top', readiness: 'unknown', version: 0 },
    { id: 'b', name: 'Black trousers', category: 'bottom', readiness: 'ready', version: 0 },
    { id: 'c', name: 'Blue tee', category: 'top', readiness: 'ready', version: 0 },
  ]
  const makeLook = (top = 'a') => ({
    id: `outfit-${top}`, title: `${top === 'a' ? 'White' : 'Blue'} tee and trousers`,
    garment_ids: [top, 'b'], policy_version: 'closet-rules-v1', score: 0.7,
    why_it_works: 'A combination from your wardrobe. Check readiness.', swaps: [],
  })
  const writes = []
  await page.addInitScript(() => {
    localStorage.setItem('dev_mock_user', JSON.stringify({ uid: 'dev-admin-user-id', email: 'admin@wardrub.test' }))
    localStorage.setItem('wardrub_widget_minimized', 'true')
  })
  await page.route('**/api/**', async route => {
    const req = route.request(), path = new URL(req.url()).pathname
    let body = { status: 'ok' }
    if (path === '/api/avatar') body = { avatar_url: null }
    if (path === '/api/profile') body = { profile: null }
    if (path === '/api/wardrobe') body = { garments: states.map(g => ({ ...g, description: { short: g.name }, url: image })) }
    if (path === '/api/check-legacy-data') body = { has_legacy_data: false }
    if (path === '/api/closet-state') body = { garments: states }
    if (path.startsWith('/api/closet-state/')) {
      const input = req.postDataJSON(), item = states.find(g => path.endsWith(g.id))
      writes.push(input)
      expect(input.expected_version).toBe(item.version)
      item.readiness = input.readiness
      item.version++
      body = { garment: item }
    }
    if (path.startsWith('/api/magazine-feed')) {
      const available = states.filter(g => g.readiness !== 'laundry')
      const top = available.find(g => g.category === 'top')
      const bottom = available.some(g => g.id === 'b')
      body = { status: 'success', feed: {
        date: '2026-09-13', policy_version: 'closet-rules-v1', weather_status: 'unavailable',
        cover_look: top && bottom ? makeLook(top.id) : null, daily_fits: [],
      } }
    }
    if (path === '/api/outfits/swap') {
      expect(req.postDataJSON()).toEqual({ garment_ids: ['a', 'b'], replace_item_id: 'a' })
      body = { status: 'success', look: makeLook('c') }
    }
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify(body) })
  })
  await page.goto('/')
  await expect(page.getByText('Weather unavailable. These suggestions do not use weather.')).toBeVisible()
  await page.getByRole('button', { name: 'View details for White tee and trousers' }).click()
  await page.getByRole('button', { name: 'Swap Top' }).click()
  await expect(page.getByRole('button', { name: 'Swap Bottom' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Blue tee and trousers' }).last()).toBeVisible()
  await page.getByRole('button', { name: 'Close', exact: true }).click()
  await page.getByText('Clothing readiness · 0 in laundry').click()
  await page.getByLabel('Black trousers · bottom').selectOption('laundry')
  await expect(page.getByRole('heading', { name: 'No outfit available yet' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Undo last readiness change' })).toBeVisible()
  await page.getByRole('button', { name: 'Undo last readiness change' }).click()
  await expect(page.getByRole('button', { name: 'View details for White tee and trousers' })).toBeVisible()
  expect(writes).toEqual([{ readiness: 'laundry', expected_version: 0 }, { readiness: 'ready', expected_version: 1 }])
  await expect(page.getByLabel('Black trousers · bottom')).toHaveValue('ready')
  const a11y = await new AxeBuilder({ page }).analyze()
  expect(a11y.violations.filter(v => ['serious', 'critical'].includes(v.impact))).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('recommender.png'), fullPage: true })
})
