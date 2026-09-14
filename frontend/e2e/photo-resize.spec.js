import { expect, test } from '@playwright/test'
import { Buffer } from 'node:buffer'
import { setupDesign } from './design-fixtures'

for (const [width, height, input, rotated] of [[8000, 6000, 'Clothing photos', false], [4284, 5712, 'Camera photo', false], [8000, 6000, 'Clothing photos', true]]) {
  test(`${width}x${height} photo (EXIF rotated: ${rotated}) is resized before clothing upload`, async ({ page }) => {
    await setupDesign(page)
    let uploaded
    await page.route('**/api/process-uploaded-clothes', async (route) => {
      const body = route.request().postDataBuffer()
      const start = body.indexOf('\r\n\r\n') + 4
      const end = body.indexOf('\r\n--', start)
      expect(body.subarray(0, start).toString()).toContain('filename="iphone.jpg"')
      uploaded = body.subarray(start, end)
      await route.fulfill({ json: { garments: [{ id: 'resized', category: 'top', name: 'Test shirt' }], failed_count: 0 } })
    })
    await page.goto('/capture')
    const data = await page.evaluate(([w, h]) => {
      const canvas = document.createElement('canvas')
      canvas.width = w; canvas.height = h
      const ctx = canvas.getContext('2d')
      ctx.fillStyle = '#4d7350'; ctx.fillRect(0, 0, w, h)
      const encoded = canvas.toDataURL('image/jpeg', 0.95).split(',')[1]
      canvas.width = 0; canvas.height = 0
      return encoded
    }, [width, height])
    let buffer = Buffer.from(data, 'base64')
    if (rotated) {
      // Real EXIF orientation 6 (90 degrees clockwise), little-endian TIFF.
      const exif = Buffer.from('ffe1002245786966000049492a0008000000010012010300010000000600000000000000', 'hex')
      buffer = Buffer.concat([buffer.subarray(0, 2), exif, buffer.subarray(2)])
    }
    await page.getByLabel(input, { exact: true }).setInputFiles({ name: 'iphone.jpeg', mimeType: 'image/jpeg', buffer })
    await page.getByRole('button', { name: 'Add clothes', exact: true }).click()
    await expect(page.getByText('Added 1 piece')).toBeVisible()
    expect(uploaded.length).toBeLessThan(10 * 1024 * 1024)
    expect(uploaded[0]).toBe(0xff); expect(uploaded[1]).toBe(0xd8)
    const size = await page.evaluate(async (b64) => {
      const blob = await (await fetch(`data:image/jpeg;base64,${b64}`)).blob()
      const bitmap = await createImageBitmap(blob)
      const size = [bitmap.width, bitmap.height]
      bitmap.close()
      return size
    }, uploaded.toString('base64'))
    expect(size).toEqual(width > height && !rotated ? [2048, 1536] : [1536, 2048])
  })
}
