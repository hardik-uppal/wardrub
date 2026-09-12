import { useCallback, useEffect, useState } from 'react'

/** Readiness is a user confirmation, independent of liking or wearing an outfit. */
export default function ClosetReadiness({ authFetch, apiUrl, onChanged, onBusyChange, disabled = false }) {
  const [items, setItems] = useState([])
  const [query, setQuery] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [undo, setUndo] = useState(null)
  const [message, setMessage] = useState('')
  const load = useCallback(async () => {
    const response = await authFetch(`${apiUrl}/api/closet-state`)
    if (!response.ok) throw new Error('Could not read clothing readiness. Please retry.')
    const data = await response.json()
    setItems(data.garments)
  }, [apiUrl, authFetch])

  useEffect(() => {
    let active = true
    const read = async () => {
      try {
        const response = await authFetch(`${apiUrl}/api/closet-state`)
        if (!response.ok) throw new Error('Could not read clothing readiness. Please retry.')
        const data = await response.json()
        if (active) setItems(data.garments)
      } catch (err) {
        if (active) setError(err.message)
      }
    }
    read()
    return () => { active = false }
  }, [apiUrl, authFetch])

  const update = async (item, readiness, isUndo = false) => {
    if (busy || disabled) return
    setBusy(true)
    onBusyChange?.(true)
    setError('')
    setMessage('')
    try {
      const response = await authFetch(`${apiUrl}/api/closet-state/${encodeURIComponent(item.id)}`, {
        method: 'PUT',
        body: JSON.stringify({ readiness, expected_version: item.version }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Readiness was not confirmed. Refresh before retrying.')
      setItems(previous => previous.map(g => g.id === item.id ? data.garment : g))
      setUndo(isUndo ? null : { item: data.garment, readiness: item.readiness })
      setMessage(isUndo ? 'Readiness change undone.' : 'Readiness updated. Outfits refreshed.')
      await onChanged()
    } catch (err) {
      setError(err.message)
      setUndo(null)
      // A lost response might have followed a successful write. Refresh the versions
      // and recommendations; never automatically repeat an uncertain mutation.
      try { await load() } catch { /* Keep the actionable original error. */ }
      await onChanged()
    } finally {
      setBusy(false)
      onBusyChange?.(false)
    }
  }

  const visible = items.filter(item => `${item.name} ${item.category}`.toLowerCase().includes(query.toLowerCase()))
  return (
    <details className="mx-4 mb-6 p-4 glass-card-static">
      <summary className="cursor-pointer font-semibold">Clothing readiness · {items.filter(g => g.readiness === 'laundry').length} in laundry</summary>
      <p className="text-sm my-3">Mark pieces ready or in laundry. Unconfirmed pieces stay labelled unknown.</p>
      {error && <div role="alert" className="my-2">{error} <button type="button" onClick={() => load().then(() => setError('')).catch(err => setError(err.message))}>Retry reading</button></div>}
      <p role="status" aria-live="polite">{message}</p>
      {undo && <button type="button" className="btn-secondary my-2" disabled={busy || disabled} onClick={() => update(undo.item, undo.readiness, true)}>Undo last readiness change</button>}
      <label className="block my-2">Find a garment <input className="input-field mt-1" value={query} onChange={e => setQuery(e.target.value)} /></label>
      <ul className="max-h-72 overflow-auto space-y-2">
        {visible.map(item => <li key={item.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--glass-border)] py-2">
          <label htmlFor={`readiness-${item.id}`} className="text-sm">{item.name} · {item.category}</label>
          <select id={`readiness-${item.id}`} className="input-field w-auto" disabled={busy || disabled} value={item.readiness} onChange={e => update(item, e.target.value)}>
            <option value="unknown">Unknown</option>
            <option value="ready">Ready to wear</option>
            <option value="laundry">In laundry</option>
          </select>
        </li>)}
      </ul>
    </details>
  )
}
