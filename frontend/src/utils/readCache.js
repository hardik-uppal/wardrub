// In-memory, per-provider GET cache. Never persists tokens or private URLs.
export function createReadCache(ttl = 5 * 60 * 1000, now = Date.now) {
  const entries = new Map()
  return {
    invalidate(resource) {
      for (const key of entries.keys()) {
        if (key === resource || key.startsWith(`${resource}:`)) entries.delete(key)
      }
    },
    read(key, load, force = false) {
      let entry = entries.get(key)
      const wrap = value => ({ value, isCurrent: () => entries.get(key) === entry })
      if (entry?.pending) return entry.pending
      if (!force && entry?.ready && now() - entry.updated < ttl) {
        return Promise.resolve(wrap(entry.value))
      }
      entry = { ready: false }
      entries.set(key, entry)
      entry.pending = Promise.resolve().then(load).then(value => {
        entry.value = value
        entry.ready = true
        entry.updated = now()
        return wrap(value)
      }).catch(error => {
        // A failed request must be retryable without erasing a newer entry.
        if (entries.get(key) === entry) entries.delete(key)
        throw error
      }).finally(() => { entry.pending = null })
      return entry.pending
    },
  }
}
