import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { setupDesign } from './design-fixtures'
test('daily correction survives reload, keeps readiness and taste, and can be undone', async ({
  page,
}) => {
  const { state, items } = await setupDesign(page)
  await page.goto('/')
  await page.getByText('Not right for today?', { exact: true }).click()
  await page.getByRole('button', { name: 'Not comfortable today' }).click()
  await expect(
    page.getByRole('heading', { name: 'A little blue' }),
  ).toBeVisible()
  await page.reload()
  await expect(
    page.getByRole('heading', { name: 'A little blue' }),
  ).toBeVisible()
  expect(state.styles).toEqual([])
  expect(items.every((item) => item.readiness === 'ready')).toBe(true)
  await page.getByRole('link', { name: 'Review or undo corrections' }).click()
  await page.getByRole('button', { name: 'Undo correction' }).click()
  await expect(page.getByText('Correction removed.')).toBeVisible()
  await page.goto('/')
  await expect(
    page.getByRole('heading', { name: 'An easy start' }),
  ).toBeVisible()
})
test('saved outfit, plan, wear, swap and laundry loop survives reload', async ({
  page,
}, testInfo) => {
  const { state, items } = await setupDesign(page)
  await page.goto('/')
  await expect(
    page.getByRole('heading', { name: 'Today', exact: true }),
  ).toBeVisible()
  await page.getByRole('button', { name: 'Save outfit', exact: true }).click()
  await expect(
    page.getByRole('button', { name: 'Saved outfit', exact: true }),
  ).toBeDisabled()
  await page.getByRole('button', { name: 'Plan for today' }).click()
  await page.getByRole('button', { name: 'I wore this' }).click()
  await page.reload()
  await page.getByRole('button', { name: 'Undo wear' }).click()
  await page.getByRole('button', { name: 'Undo plan' }).click()
  await page.getByRole('button', { name: 'Swap top' }).click()
  await page.getByRole('button', { name: 'Blue tee' }).click()
  await expect(
    page.getByRole('heading', { name: 'A little blue' }),
  ).toBeVisible()
  await page.goto('/wardrobe')
  await page.locator('summary').filter({ hasText: 'Filters' }).click()
  await page.getByRole('checkbox', { name: 'Manage clothes' }).check()
  await page.getByRole('checkbox', { name: 'Select Linen shirt' }).check()
  await page.getByRole('checkbox', { name: 'Select Everyday trousers' }).check()
  await page.getByRole('button', { name: 'Send to laundry' }).click()
  await expect(page.getByText('Clothing readiness updated.')).toBeVisible()
  expect(items.filter((g) => g.readiness === 'laundry')).toHaveLength(2)
  await page.getByRole('button', { name: 'Undo last readiness change' }).click()
  await expect(page.getByText('Readiness change undone.')).toBeVisible()
  expect(items.filter((g) => g.readiness === 'laundry')).toHaveLength(0)
  await page.getByRole('button', { name: 'View Linen shirt' }).click()
  await page.getByText('Manage this piece', { exact: true }).click()
  await page
    .getByRole('dialog')
    .getByLabel('Storage location (optional)')
    .fill('Bedroom · top drawer')
  await page.getByRole('button', { name: 'Save location', exact: true }).click()
  await page.getByRole('button', { name: 'Close', exact: true }).click()
  expect(state.locations.a).toBe('Bedroom · top drawer')
  await page.screenshot({
    path: testInfo.outputPath('wardrobe.png'),
    fullPage: true,
  })
  await page.goto('/looks')
  await expect(
    page.getByRole('heading', { name: 'An easy start' }),
  ).toBeVisible()
  await page.goto('/')
  await expect(
    page.getByRole('heading', { name: 'An easy start' }),
  ).toBeVisible()
  const result = await new AxeBuilder({ page }).analyze()
  expect(
    result.violations.filter((v) => ['serious', 'critical'].includes(v.impact)),
  ).toEqual([])
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true)
  await page.screenshot({
    path: testInfo.outputPath('today.png'),
    fullPage: true,
  })
})
