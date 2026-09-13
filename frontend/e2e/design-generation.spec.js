import { expect, test } from '@playwright/test'
import { setupDesign, photo } from './design-fixtures'
test('avatar candidate preserves outfit through reload and try-on failure', async ({
  page,
}) => {
  const { failures, history } = await setupDesign(page)
  await page.goto('/')
  await page.getByRole('button', { name: 'Try on me', exact: true }).click()
  await page.getByRole('button', { name: 'Create Avatar', exact: true }).click()
  await page.locator('input[type=file]').first().setInputFiles(photo)
  await page.getByRole('button', { name: 'Create Avatar', exact: true }).click()
  await expect(
    page.getByRole('heading', { name: 'Review your avatar' }),
  ).toBeVisible()
  await page.getByRole('button', { name: 'Use this avatar' }).click()
  await expect(page).toHaveURL(/dressing-room/)
  await page.reload()
  failures.generation = true
  await page.getByRole('button', { name: 'Try On 2 Items' }).click()
  await expect(page.getByText('Preview unavailable. Try again.')).toBeVisible()
  failures.generation = false
  await page.getByRole('button', { name: 'Try On 2 Items' }).click()
  await expect(
    page.getByText('Saved automatically to Wardrobe → Outfits → Try-ons'),
  ).toBeVisible()
  await page.getByRole('button', { name: 'View my try-ons' }).click()
  await expect(
    page.getByRole('button', { name: /Open look from/ }),
  ).toBeVisible()
  expect(history).toHaveLength(1)
})
test('unconfirmed save and stale feed never report success', async ({
  page,
}) => {
  const { failures, state } = await setupDesign(page)
  await page.goto('/')
  failures.save = true
  await page.getByRole('button', { name: 'Save outfit', exact: true }).click()
  await expect(page.getByText('Save was not confirmed.').first()).toBeVisible()
  expect(Object.keys(state.outfits)).toHaveLength(0)
  failures.feed = true
  await page.getByRole('button', { name: 'Refresh', exact: true }).click()
  await expect(page.getByText('Suggestions unavailable.')).toBeVisible()
  await expect(
    page.getByRole('heading', { name: 'An easy start' }),
  ).toHaveCount(0)
})
