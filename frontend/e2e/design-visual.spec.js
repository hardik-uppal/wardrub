import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { setupDesign } from './design-fixtures'
test('light and dark screens remain accessible at the current viewport', async ({
  page,
}, testInfo) => {
  await setupDesign(page, { avatar: true })
  const errors = []
  page.on('pageerror', (e) => errors.push(e.message))
  for (const scheme of ['light', 'dark']) {
    await page.emulateMedia({ colorScheme: scheme, reducedMotion: 'reduce' })
    for (const [name, path] of [
      ['today', '/'],
      ['wardrobe', '/wardrobe'],
      ['outfits', '/looks'],
      ['capture', '/capture'],
      ['avatar', '/create-avatar'],
      ['tryon', '/dressing-room'],
      ['profile', '/profile'],
      ['style', '/profile?analysis=fit'],
      ['recovery', '/profile?section=recovery'],
    ]) {
      await page.goto(path)
      await expect(page.locator('h1').first()).toBeVisible()
      if (name === 'today')
        await expect(
          page.getByRole('button', { name: 'Save outfit', exact: true }),
        ).toBeEnabled()
      const audit = await new AxeBuilder({ page }).analyze()
      expect(
        audit.violations.filter((v) =>
          ['serious', 'critical'].includes(v.impact),
        ),
        `${name} ${scheme}`,
      ).toEqual([])
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        `${name} overflow`,
      ).toBe(true)
      await page.screenshot({
        path: testInfo.outputPath(`${name}-${scheme}.png`),
        fullPage: true,
      })
    }
  }
  expect(errors).toEqual([])
})
