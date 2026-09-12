import { isPhotoFile, PHOTO_FORMAT_MESSAGE } from './imageUploads'

export const MAX_STYLE_PHOTOS = 4
export const MAX_STYLE_PHOTO_BYTES = 10 * 1024 * 1024

export function getStyleProgress(profile) {
  const stages = ['color', 'fit'].map(name => {
    const hasResult = Boolean(name === 'color' ? profile?.skin_tone : profile?.body_type)
    const saved = profile?.style_analysis?.[name]
    const status = saved?.status || (hasResult ? 'ready' : 'not_started')
    const instructions = saved?.requested_input?.instructions || (name === 'color'
      ? 'Add a face photo in indirect daylight, without filters or colored lighting.'
      : 'Add a full-length photo for better fit analysis.')
    return {
      name, status, hasResult,
      done: status === 'ready' && hasResult,
      reason: saved?.requested_input?.reason,
      message: status === 'failed'
        ? 'Analysis is temporarily unavailable. Retry with the same photos; your saved recommendations are unchanged.'
        : instructions,
      attempts: saved?.attempts || 0,
    }
  })
  const next = stages.find(stage => !stage.done)
  return { stages, next, done: !next }
}

export function validateStylePhotos(files) {
  if (!files.length || files.length > MAX_STYLE_PHOTOS) return 'Choose between 1 and 4 photos.'
  if (files.some(file => file.size === 0 || file.size > MAX_STYLE_PHOTO_BYTES)) {
    return 'Each photo must be non-empty and no larger than 10 MB.'
  }
  if (files.some(file => !isPhotoFile(file))) {
    return PHOTO_FORMAT_MESSAGE
  }
  return null
}
