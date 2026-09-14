import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { photoDimensions, prepareClothingPhoto } from './preparePhoto'

let dimensions, failDecode, output, draw, canvas
beforeEach(() => {
  dimensions = [8000, 6000]
  failDecode = false
  output = new Blob(['jpeg'], { type: 'image/jpeg' })
  draw = vi.fn()
  vi.stubGlobal('URL', { createObjectURL: vi.fn(() => 'blob:photo'), revokeObjectURL: vi.fn() })
  vi.stubGlobal('Image', class {
    constructor() { [this.naturalWidth, this.naturalHeight] = dimensions }
    set src(value) { if (value) queueMicrotask(() => failDecode ? this.onerror?.() : this.onload?.()) }
  })
  const original = document.createElement.bind(document)
  vi.spyOn(document, 'createElement').mockImplementation((tag) => {
    if (tag !== 'canvas') return original(tag)
    canvas = { width: 0, height: 0, getContext: () => ({ fillRect: vi.fn(), drawImage: draw }), toBlob: (done) => done(output) }
    return canvas
  })
})
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals() })
const photo = (name = 'iphone.jpeg', type = 'image/jpeg') => new File(['original'], name, { type })

test('48 MP landscape and 24 MP portrait preserve aspect ratio', () => {
  expect(photoDimensions(8000, 6000)).toEqual({ width: 2048, height: 1536 })
  expect(photoDimensions(4284, 5712)).toEqual({ width: 1536, height: 2048 })
  expect(() => photoDimensions(10000, 10000)).toThrow('64 megapixels')
})
test('large photos become actual JPEG files and resources are released', async () => {
  const result = await prepareClothingPhoto(photo())
  expect(result.name).toBe('iphone.jpg')
  expect(result.type).toBe('image/jpeg')
  expect(draw).toHaveBeenCalledWith(expect.anything(), 0, 0, 2048, 1536)
  expect(canvas.width).toBe(0)
  expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:photo')
})
test('small originals are not unnecessarily re-encoded', async () => {
  dimensions = [1200, 1600]
  const original = photo()
  expect(await prepareClothingPhoto(original)).toBe(original)
  expect(draw).not.toHaveBeenCalled()
})
test('undecodable HEIC bytes remain original for server fallback even with jpeg name', async () => {
  failDecode = true
  const original = photo('iphone.jpeg', 'image/heic')
  expect(await prepareClothingPhoto(original)).toBe(original)
  expect(URL.revokeObjectURL).toHaveBeenCalledOnce()
})
test('undecodable oversized input gets an actionable error, not an oversized upload', async () => {
  failDecode = true
  const original = photo('iphone.heic', 'image/heic')
  Object.defineProperty(original, 'size', { value: 11 * 1024 * 1024 })
  await expect(prepareClothingPhoto(original)).rejects.toThrow('Export it as JPEG under 10 MB')
})
test('rejects inputs over 25 MB before decoding', async () => {
  const original = photo()
  Object.defineProperty(original, 'size', { value: 26 * 1024 * 1024 })
  await expect(prepareClothingPhoto(original)).rejects.toThrow('25 MB')
  expect(URL.createObjectURL).not.toHaveBeenCalled()
})
test('accepts legacy image/jpg MIME', async () => {
  expect((await prepareClothingPhoto(photo('phone.jpg', 'image/jpg'))).type).toBe('image/jpeg')
})
test('encoder failure is explicit and cleans up', async () => {
  output = null
  await expect(prepareClothingPhoto(photo())).rejects.toThrow('Could not resize')
  expect(URL.revokeObjectURL).toHaveBeenCalledOnce()
  expect(canvas.width).toBe(0)
})
