import { localDay } from './localDay'

const key = (uid) => `wardrub:daily-location:${uid}`
export function locationPreference(uid) {
  try { return JSON.parse(localStorage.getItem(key(uid)) || 'null') } catch { return null }
}
export function setLocationPreference(uid, enabled, day = null) {
  if (!uid) return
  try { localStorage.setItem(key(uid), JSON.stringify({ enabled, day })) } catch { /* Storage may be unavailable. */ }
}
const pending = new Map()
export function refreshDailyLocation(uid, save) {
  if (!uid) return Promise.resolve()
  if (pending.has(uid)) return pending.get(uid)
  const preference = locationPreference(uid)
  if (!preference?.enabled || preference.day === localDay()) return Promise.resolve()
  // Record attempts too: denied permission must not cause repeated prompts.
  setLocationPreference(uid, true, localDay())
  const task = (async () => {
    try {
      if (!navigator.geolocation || !navigator.permissions) return
      const permission = await navigator.permissions.query({ name: 'geolocation' })
      if (permission.state !== 'granted') return
      const position = await new Promise((resolve, reject) =>
        navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 10000, maximumAge: 0 }),
      )
      if (locationPreference(uid)?.enabled)
        await save(position.coords.latitude, position.coords.longitude, 'Current location')
    } catch { /* Keep the saved city when location is unavailable. */ }
  })().finally(() => pending.delete(uid))
  pending.set(uid, task)
  return task
}
