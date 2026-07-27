import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const image = 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22300%22%3E%3Crect width=%22200%22 height=%22300%22 fill=%22%23eeeeef%22/%3E%3C/svg%3E'

const garments = [
  { id: 'top-1', category: 'top', url: image, front_url: image, thumbnail_url: image, description: 'White tee' },
  { id: 'bottom-1', category: 'bottom', url: image, front_url: image, thumbnail_url: image, description: 'Black trousers' },
]

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('dev_mock_user', JSON.stringify({
      uid: 'dev-admin-user-id',
      email: 'admin@wardrub.test',
      displayName: 'E2E User',
    }))
    window.localStorage.setItem('wardrub_widget_minimized', 'true')
  })

  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url())
    let body

    if (url.pathname === '/api/avatar') {
      body = { avatar_url: image }
    } else if (url.pathname === '/api/wardrobe') {
      body = { garments }
    } else if (url.pathname === '/api/try-on/history') {
      body = {
        results: [{
          id: 'look-1',
          url: image,
          thumbnail_url: image,
          created_at: '2026-07-25T00:00:00Z',
          favorite: true,
          occasion: 'Work',
          garment_categories: ['top', 'bottom'],
        }],
      }
    } else if (url.pathname === '/api/profile') {
      body = { profile: null }
    } else if (url.pathname === '/api/check-legacy-data') {
      body = { has_legacy_data: false }
    } else if (url.pathname === '/api/magazine-feed') {
      body = {
        status: 'success',
        feed: {
          cover_look: {
            id: 'cover-1',
            title: 'Clean foundations',
            occasion: 'Everyday',
            why_it_works: 'A balanced, versatile combination.',
            score: 0.86,
            garment_ids: ['top-1', 'bottom-1'],
            styling_tips: [],
            swaps: [],
          },
          daily_fits: [],
          one_item_three_ways: [],
          underused_edit: null,
        },
      }
    } else {
      body = { status: 'ok' }
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(body),
    })
  })
})

test('core wardrobe journeys remain usable', async ({ page }) => {
  await page.goto('/wardrobe')
  await expect(page.getByRole('heading', { name: 'My Wardrobe', exact: true })).toBeVisible()
  await expect(page.getByRole('searchbox', { name: 'Search wardrobe' })).toBeVisible()
  await expect(page.getByText('White tee')).toBeVisible()

  await page.goto('/dressing-room')
  await expect(page.getByRole('heading', { name: 'Dressing Room', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'top', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Try On 1 Item' })).toBeVisible()

  await page.goto('/looks')
  await expect(page.getByRole('heading', { name: 'Saved Looks', exact: true })).toBeVisible()
  await expect(page.getByText('Work')).toBeVisible()

  await page.goto('/profile')
  await expect(page.getByRole('heading', { name: 'My Profile', exact: true })).toBeVisible()
  await expect(page.getByText('Style Analysis')).toBeVisible()

  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'The Looker', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: /Refresh issue/i })).toBeVisible()
  await expect(page.getByText('Strong match')).toBeVisible()
})

test('primary routes have no serious automated accessibility violations', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })

  for (const route of ['/', '/wardrobe', '/dressing-room', '/looks', '/profile']) {
    await page.goto(route)
    await expect(page.locator('main, [role="main"], h1').first()).toBeVisible()

    const results = await new AxeBuilder({ page }).analyze()
    const seriousViolations = results.violations.filter(
      violation => ['serious', 'critical'].includes(violation.impact),
    )

    expect(seriousViolations, `${route} accessibility violations`).toEqual([])
  }
})
