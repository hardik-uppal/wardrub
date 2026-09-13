import { expect, test } from '@playwright/test'
import { setupDesign } from './design-fixtures'

test('Today and wardrobe stay quiet; optional controls remain reachable', async ({ page }) => {
  await setupDesign(page)
  await page.goto('/')
  await expect(page.getByRole('button', { name: 'Save outfit', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Refresh', exact: true })).toHaveCount(0)
  await expect(page.getByRole('link', { name: 'Location', exact: true })).toHaveCount(0)
  await expect(page.getByText('Readiness unknown', { exact: true })).toHaveCount(0)
  await page.goto('/wardrobe')
  await expect(page.getByRole('button', { name: 'View Linen shirt' })).toBeVisible()
  await expect(page.getByRole('checkbox', { name: 'Select Linen shirt' })).toHaveCount(0)
  await expect(page.getByText('Ready', { exact: true })).toHaveCount(0)
  await page.locator('summary').filter({ hasText: 'Filters' }).click()
  await expect(page.getByRole('checkbox', { name: 'Manage clothes' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.goto('/profile?section=refresh')
  await page.getByRole('button', { name: 'Refresh', exact: true }).click()
  await expect(page.getByText('Wardrobe refreshed.', { exact: true })).toBeVisible()
  await page.goto('/profile?section=location')
  await expect(page.getByRole('button', { name: 'Use current location' })).toBeVisible()
})
