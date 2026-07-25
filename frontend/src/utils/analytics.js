const API_URL = import.meta.env.VITE_API_URL || ''
const ACTIVATION_STORAGE_PREFIX = 'wardrub_activation_'

export async function trackActivationEvent(name, getToken, properties = {}) {
  const storageKey = `${ACTIVATION_STORAGE_PREFIX}${name}`

  try {
    if (window.localStorage.getItem(storageKey) === 'true') return

    const token = await getToken()
    if (!token) return

    const response = await fetch(`${API_URL}/api/analytics/events`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ name, properties }),
      keepalive: true,
    })

    if (response.ok) {
      window.localStorage.setItem(storageKey, 'true')
    }
  } catch (error) {
    // Analytics must never interrupt a product task.
    console.debug('Activation event was not recorded:', error)
  }
}
