export const PHOTO_ACCEPT = 'image/jpeg,image/png,image/webp,image/heic,image/heif,.jpg,.jpeg,.png,.webp,.heic,.heif'
export const PHOTO_FORMAT_MESSAGE = 'Use JPEG, PNG, WebP, HEIC, or HEIF photos.'
export function isPhotoFile(file) {
  if (['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/heic', 'image/heif'].includes(file.type.toLowerCase())) return true
  // Some iOS/file providers omit MIME; the backend still verifies actual bytes.
  return (!file.type || file.type === 'application/octet-stream') && /\.(jpe?g|png|webp|heic|heif)$/i.test(file.name)
}
