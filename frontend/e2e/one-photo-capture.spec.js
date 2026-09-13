import { expect, test } from '@playwright/test'
import { setupDesign, photo } from './design-fixtures'
for (const inputName of ['Clothing photos', 'Camera photo']) {
  test(`one photo labels clothes and retains visible fit via ${inputName}`, async ({
    page,
  }, testInfo) => {
    const { items } = await setupDesign(page)
    let uploads = 0
    await page.route('**/api/process-uploaded-clothes', async (route) => {
      uploads++
      const body = route.request().postData()
      expect(body).toContain('name="file"')
      expect(body).not.toContain('name="category"')
      expect(body).not.toContain('name="back')
      const item = {
        id: 'new-shirt',
        name: 'Green sweatshirt',
        category: 'top',
        url: items[0].url,
        front_url: items[0].url,
        readiness: 'unknown',
        version: 0,
        fit_observation: {
          source: 'worn',
          fit: 'loose',
          drape: 'Fabric falls away from the torso',
          evidence: ['Dropped shoulder and room through torso'],
          confidence: 0.85,
          visibility: 'clear',
        },
      }
      items.push(item)
      await route.fulfill({
        json: { garments: [item], failed_count: 0, status: 'processed' },
      })
    })
    await page.goto('/capture?from=wardrobe')
    await expect(
      page.getByRole('heading', { name: 'Add clothes' }),
    ).toBeVisible()
    await expect(
      page.getByRole('button', { name: 'Choose photo' }),
    ).toBeVisible()
    await expect(
      page.getByRole('button', { name: 'Take photo', exact: true }),
    ).toBeVisible()
    await expect(
      page.getByText(
        /front|back photo|What type of clothing|Clean up garment/i,
      ),
    ).toHaveCount(0)
    await page.screenshot({
      path: testInfo.outputPath('one-photo-start.png'),
      fullPage: true,
    })
    await page.getByLabel(inputName, { exact: true }).setInputFiles(photo)
    await page.getByRole('button', { name: 'Add clothes', exact: true }).click()
    await expect(page.getByText('Added 1 piece')).toBeVisible()
    expect(uploads).toBe(1)
    await page.getByRole('button', { name: 'Done', exact: true }).click()
    await expect(page).toHaveURL(/\/wardrobe$/)
    await page.reload()
    await page.getByRole('button', { name: 'View Green sweatshirt' }).click()
    await expect(page.getByText('Fit in this photo · loose')).toBeVisible()
    await page.getByText('Fit in this photo · loose').click()
    await expect(
      page.getByText('Fabric falls away from the torso'),
    ).toBeVisible()
  })
}
test('wardrobe hides secondary filters while keeping them usable', async ({
  page,
}, testInfo) => {
  await setupDesign(page)
  await page.goto('/wardrobe')
  await expect(page.getByRole('button', {name:'View Linen shirt'})).toBeVisible()
  await expect(
    page.getByRole('button', { name: 'Tops', exact: true }),
  ).not.toBeVisible()
  await page.screenshot({
    path: testInfo.outputPath('wardrobe-simple.png'),
    fullPage: true,
  })
  await page.getByText('Filters', { exact: true }).click()
  await page.getByRole('button', { name: 'Tops', exact: true }).click()
  await expect(
    page.getByRole('button', { name: 'View Everyday trousers' }),
  ).toHaveCount(0)
  await page.getByRole('button', { name: 'All', exact: true }).click()
  await expect(
    page.getByRole('button', { name: 'View Everyday trousers' }),
  ).toBeVisible()
})
