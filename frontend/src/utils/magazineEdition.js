export function editionLabel(day) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day || '')) return 'EDITION DATE UNAVAILABLE'
  const date = new Date(`${day}T00:00:00Z`)
  if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0, 10) !== day) return 'EDITION DATE UNAVAILABLE'
  return `${date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' }).toUpperCase()} · UTC`
}
