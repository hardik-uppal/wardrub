import { describe, expect, it } from 'vitest'
import { isPhotoFile } from './imageUploads'
import { validateStylePhotos } from './styleAnalysis'

describe('upload format hints', () => {
  it.each(['image/heic', 'image/heif', '', 'application/octet-stream'])('accepts HEIC with MIME %s', type => {
    const file = new File(['photo'], 'IPHONE.HEIC', { type })
    expect(isPhotoFile(file)).toBe(true)
    expect(validateStylePhotos([file])).toBe(null)
  })
  it('rejects unsupported formats and misleading explicit MIME before upload', () => {
    expect(isPhotoFile(new File(['bad'], 'fake.heic', { type: 'application/pdf' }))).toBe(false)
    expect(isPhotoFile(new File(['bad'], 'photo.gif', { type: 'image/gif' }))).toBe(false)
    expect(isPhotoFile(new File(['bad'], 'unknown'))).toBe(false)
  })
})
