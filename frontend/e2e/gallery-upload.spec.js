/* global Buffer */
import { expect, test } from '@playwright/test'

test('gallery batch retains successes and retries only a failed photo', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('dev_mock_user', JSON.stringify({ uid: 'gallery-test', email: 'admin@wardrub.test', displayName: 'Gallery Test' }))
    localStorage.setItem('wardrub_widget_minimized', 'true')
  })
  let uploads = 0
  let active = 0
  let peakActive = 0
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/process-uploaded-clothes') {
      uploads++
      active++
      peakActive = Math.max(peakActive, active)
      await new Promise(resolve => setTimeout(resolve, 150))
      active--
      if (uploads === 2) {
        await route.fulfill({ status: 422, json: { detail: 'No garment found in second photo' } })
      } else {
        await route.fulfill({ json: { garments: [{ id: `garment-${uploads}`, front_url: '', category: 'top' }] } })
      }
      return
    }
    await route.fulfill({ json: { avatar_url: null, profile: null, garments: [] } })
  })
  await page.goto('/capture')
  await page.getByRole('button', { name: /Upload Photo/ }).click()
  // Tiny valid PNG; no private photos or actual inference used by this test.
  const buffer = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=', 'base64')
  await page.getByLabel('Clothing photos').setInputFiles([
    { name: 'shirt.png', mimeType: 'image/png', buffer },
    { name: 'trousers.png', mimeType: 'image/png', buffer },
    { name: 'remove.png', mimeType: 'image/png', buffer },
  ])
  await expect(page.getByText('3 photo(s) selected')).toBeVisible()
  await page.getByRole('button', { name: 'Remove remove.png' }).click()
  await page.getByRole('button', { name: 'Detect & Add 2 photo(s)' }).click()
  await expect(page.getByText('No garment found in second photo')).toBeVisible()
  await expect(page.getByText('Added 1 garment(s)', { exact: true })).toHaveCount(1)
  await page.getByRole('button', { name: 'Retry trousers.png' }).click()
  await expect(page.getByText('Added 1 garment(s)', { exact: true })).toHaveCount(2)
  expect(uploads).toBe(3)
  expect(peakActive).toBe(1)
})
