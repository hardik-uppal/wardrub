const API_URL = import.meta.env.VITE_API_URL || ''
const ACTIVATION_STORAGE_PREFIX = 'wardrub_activation_'

export async function trackActivationEvent(name, getToken, properties = {}) {
  try {
    const token = await getToken()
    if (!token) return

    // Decode only to namespace this browser preference, never for authorization.
    // The backend verifies the token and derives the real UID independently.
    let uid
    try {
      const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
      uid = JSON.parse(atob(payload)).sub
    } catch {
      // Local dev tokens aren't JWTs: deliver without cross-user suppression.
    }
    const storageKey = typeof uid === 'string' && uid
      ? `${ACTIVATION_STORAGE_PREFIX}${uid}:${name}` : null
    if (storageKey && window.localStorage.getItem(storageKey) === 'true') return

    const response = await fetch(`${API_URL}/api/analytics/events`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ name, properties }),
      keepalive: true,
    })

    if (response.ok && storageKey) {
      window.localStorage.setItem(storageKey, 'true')
    }
  } catch (error) {
    // Analytics must never interrupt a product task.
    console.debug('Activation event was not recorded:', error)
  }
}
