const VALID_GARMENT_CATEGORIES = new Set([
  'top',
  'bottom',
  'dress',
  'outerwear',
])

export function buildMultiTryOnGarments(garments) {
  if (!Array.isArray(garments) || garments.length === 0) {
    throw new Error('Please select at least one garment')
  }

  return garments.map((garment) => {
    const url = garment?.front_url || garment?.url
    const category = garment?.category

    if (!url || !VALID_GARMENT_CATEGORIES.has(category)) {
      throw new Error('One or more selected garments are invalid')
    }

    return { id: garment.id || null, url, category }
  })
}

export function getTryOnResultUrl(result) {
  return typeof result === 'string' ? result : result?.result_url || null
}
