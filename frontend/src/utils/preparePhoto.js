import { isPhotoFile, PHOTO_FORMAT_MESSAGE } from './imageUploads'

export const MAX_SOURCE_BYTES = 25 * 1024 * 1024
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024
export const PHOTO_MAX_EDGE = 2048

export function photoDimensions(width, height) {
  if (!Number.isFinite(width) || !Number.isFinite(height) || width < 1 || height < 1)
    throw new Error('This photo has invalid dimensions. Choose another photo.')
  // Bound work even when a small compressed file expands enormously.
  if (width * height > 64_000_000)
    throw new Error('This photo is over 64 megapixels. Export a smaller copy and try again.')
  const scale = Math.min(1, PHOTO_MAX_EDGE / Math.max(width, height))
  return { width: Math.max(1, Math.round(width * scale)), height: Math.max(1, Math.round(height * scale)) }
}

function loadImage(url) {
  return new Promise((resolve, reject) => {
    const image = new Image()
    const timer = setTimeout(() => finish(new Error('Photo decoding timed out.')), 20000)
    const finish = (error) => {
      clearTimeout(timer)
      image.onload = image.onerror = null
      if (error) { image.src = ''; reject(error) } else resolve(image)
    }
    image.onload = () => finish()
    image.onerror = () => finish(new Error('Browser cannot decode this photo.'))
    // Modern browsers apply EXIF orientation when drawing HTML images.
    image.src = url
  })
}

/** Clothing uploads only. Sequential callers keep large photo decodes bounded.
 * Never relabel undecoded HEIC as JPEG: pass original bytes to the server when
 * within its limit. Browser HEIC support varies; server validation remains final.
 */
export async function prepareClothingPhoto(file) {
  if (!isPhotoFile(file)) throw new Error(PHOTO_FORMAT_MESSAGE)
  if (!file.size || file.size > MAX_SOURCE_BYTES)
    throw new Error('Choose a non-empty photo no larger than 25 MB.')
  const url = URL.createObjectURL(file)
  let image
  let canvas
  try {
    try { image = await loadImage(url) } catch {
      if (file.size <= MAX_UPLOAD_BYTES) return file
      throw new Error('This browser cannot resize this photo. Export it as JPEG under 10 MB and try again.')
    }
    const size = photoDimensions(image.naturalWidth, image.naturalHeight)
    // Keep small originals; server still checks real bytes, animation and metadata.
    if (image.naturalWidth <= PHOTO_MAX_EDGE && image.naturalHeight <= PHOTO_MAX_EDGE && file.size <= MAX_UPLOAD_BYTES)
      return file
    canvas = document.createElement('canvas')
    canvas.width = size.width
    canvas.height = size.height
    const context = canvas.getContext('2d')
    if (!context) throw new Error('Could not prepare this photo. Please try a smaller copy.')
    context.fillStyle = '#ffffff'
    context.fillRect(0, 0, size.width, size.height)
    context.drawImage(image, 0, 0, size.width, size.height)
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.92))
    if (!blob || blob.type !== 'image/jpeg' || !blob.size || blob.size > MAX_UPLOAD_BYTES)
      throw new Error('Could not resize this photo for upload. Please try a smaller copy.')
    return new File([blob], `${file.name.replace(/\.[^.]+$/, '') || 'photo'}.jpg`, { type: 'image/jpeg', lastModified: file.lastModified })
  } finally {
    if (image) image.src = ''
    if (canvas) { canvas.width = 0; canvas.height = 0 }
    URL.revokeObjectURL(url)
  }
}
