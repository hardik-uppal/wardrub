import { expect, test } from '@playwright/test'
import { Buffer } from 'node:buffer'
import AxeBuilder from '@axe-core/playwright'

const palette = { best: ['Coral', 'Peach'], good: ['Ivory'], avoid: [] }
const upload = {
  name: 'photo.png', mimeType: 'image/png',
  buffer: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=', 'base64'),
}

test('color-first analysis guides fit uploads, survives retries and resumes after reload', async ({ page }) => {
  let savedProfile = null
  let attempts = 0
  const submittedStages = []
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.addInitScript(() => {
    localStorage.setItem('dev_mock_user', JSON.stringify({ uid: 'dev-admin-user-id', displayName: 'Style Test' }))
    localStorage.setItem('wardrub_widget_minimized', 'true')
  })
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    let body = {}
    if (path === '/api/profile/analyze') {
      const request = route.request().postDataBuffer().toString()
      submittedStages.push(request.match(/name="stage"\r\n\r\n([^\r]+)/)?.[1])
      attempts += 1
      const readyColor = { status: 'ready' }
      const fit = attempts === 1
        ? { status: 'needs_input', requested_input: { photo_type: 'full_length', instructions: 'Add a full-length photo for better fit analysis.' } }
        : attempts === 2
          ? { status: 'needs_input', requested_input: { photo_type: 'full_length', reason: 'Loose clothing hides your proportions.', instructions: 'Choose comfortable clothes that follow your shape.' } }
          : attempts === 3 ? { status: 'failed' } : { status: 'ready' }
      savedProfile = {
        skin_tone: { season: 'spring', undertone: 'warm', depth: 'medium' },
        body_type: attempts >= 4 ? 'rectangle' : null,
        style_analysis: { color: readyColor, fit },
      }
      body = { profile: savedProfile, color_recommendations: palette, fit_recommendations: null, status: attempts === 3 ? 'failed' : 'analyzed' }
    } else if (path === '/api/profile') body = { profile: savedProfile }
    else if (path === '/api/profile/color-recommendations') body = { recommendations: palette }
    else if (path === '/api/profile/fit-recommendations') body = { recommendations: {} }
    else if (path === '/api/check-legacy-data') body = { has_legacy_data: false }
    else if (path === '/api/avatar') body = { avatar_url: null }
    else if (path === '/api/wardrobe') body = { garments: [] }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
  })

  await page.goto('/profile?section=style')
  await page.getByLabel('Choose style analysis photos').setInputFiles(upload)
  await page.getByRole('button', { name: 'Analyze My Style' }).click()
  await expect(page.getByText('Coral', { exact: true })).toBeVisible()
  await expect(page.getByText('Your colors · Ready')).toBeVisible()
  await expect(page.getByText('Your fit · Photo needed')).toBeVisible()

  await page.getByLabel('Analysis focus').selectOption('fit')
  await expect(page).toHaveURL(/analysis=fit/)
  await expect(page.getByLabel('Analysis focus')).toHaveValue('fit')
  await page.getByLabel('Choose style analysis photos').setInputFiles(upload)
  await page.getByRole('button', { name: 'Analyze My Style' }).click()
  await expect(page.getByText('Loose clothing hides your proportions.')).toBeVisible()
  await expect(page.getByText('Coral', { exact: true })).toBeVisible()

  await page.reload()
  await expect(page.getByText('Loose clothing hides your proportions.')).toBeVisible()
  await expect(page.getByText('Coral', { exact: true })).toBeVisible()
  await page.getByLabel('Choose style analysis photos').setInputFiles(upload)
  await page.getByRole('button', { name: 'Analyze My Style' }).click()
  await expect(page.getByText('Your fit · Retry available')).toBeVisible()
  await expect(page.getByText('1 selected', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Analyze My Style' }).click()
  await expect(page.getByText('Your fit · Ready')).toBeVisible()
  expect(submittedStages).toEqual(['auto', 'fit', 'fit', 'fit'])
  await expect(page.getByText('Coral', { exact: true })).toBeVisible()
  const results = await new AxeBuilder({ page }).analyze()
  expect(results.violations.filter(v => ['serious', 'critical'].includes(v.impact))).toEqual([])
  expect(errors).toEqual([])
})
