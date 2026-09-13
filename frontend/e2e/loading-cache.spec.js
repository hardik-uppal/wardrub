import { expect, test } from '@playwright/test'

// Controlled navigation benchmark, not production network or signed-image latency.
test('empty wardrobe navigation reuses a single successful read', async ({ page }, testInfo) => {
  const counts = {}
  const unexpected = []
  await page.addInitScript(() => {
    localStorage.setItem('dev_mock_user', JSON.stringify({ uid: 'loading-test', email: 'admin@wardrub.test', displayName: 'Loading Test' }))
    localStorage.setItem('wardrub_widget_minimized', 'true')
  })
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    counts[path] = (counts[path] || 0) + 1
    const fixtures = {
      '/api/avatar': { avatar_url: 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="20" height="20"/%3E' },
      '/api/profile': { profile: null },
      '/api/closet-library': {version:0,outfits:{},days:{},locations:{},styles:[]},
      '/api/closet-state': {garments:[]},
      '/api/wardrobe': { garments: [] },
      '/api/try-on/history': { results: [] },
      '/api/check-legacy-data': { has_legacy_data: false },
    }
    if (!(path in fixtures)) {
      unexpected.push(path)
      await route.fulfill({ status: 500, json: { error: 'unexpected endpoint' } })
      return
    }
    await new Promise(resolve => setTimeout(resolve, 100))
    await route.fulfill({ status: 200, json: fixtures[path] })
  })
  await page.goto('/wardrobe')
  await expect(page.getByRole('heading', { name: 'Wardrobe', exact: true })).toBeVisible()
  await expect.poll(() => counts['/api/wardrobe']).toBeGreaterThan(0)
  await page.waitForTimeout(200) // Let the simulated first response settle before navigating.
  await page.getByRole('link', { name: 'Outfits', exact: true }).click()
  await page.getByRole('link', { name: 'Create a try-on', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Create a try-on', exact: true })).toBeVisible()
  await page.waitForTimeout(200)
  await page.getByRole('link', { name: 'Wardrobe', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Wardrobe', exact: true })).toBeVisible()
  await page.waitForTimeout(200)
  await testInfo.attach('request-counts', { body: JSON.stringify({ counts, unexpected }, null, 2), contentType: 'application/json' })
  console.log('LOADING_REQUEST_COUNTS', testInfo.project.name, JSON.stringify(counts))
  expect(unexpected).toEqual([])
  expect(counts['/api/wardrobe']).toBe(1)
  expect(counts['/api/avatar']).toBe(1)
  expect(counts['/api/profile']).toBe(1)
})
