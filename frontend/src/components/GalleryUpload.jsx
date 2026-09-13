import { useEffect, useRef, useState } from 'react'
import { useWardrobe } from '../context/WardrobeContext'
import { isPhotoFile, PHOTO_ACCEPT } from '../utils/imageUploads'
import UploadPreview from './UploadPreview'

const MAX_PHOTOS = 5
const MAX_BYTES = 10 * 1024 * 1024

export default function GalleryUpload({ onDone }) {
  const { processUploadedClothes, isLoading } = useWardrobe()
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const running = useRef(false)
  const mounted = useRef(false)
  const urls = useRef(new Set())
  const input = useRef(null)

  useEffect(() => {
    mounted.current = true
    const previews = urls.current
    return () => {
      mounted.current = false
      for (const url of previews) URL.revokeObjectURL(url)
      previews.clear()
    }
  }, [])

  function select(event) {
    const files = Array.from(event.target.files || [])
    event.target.value = ''
    if (running.current || !files.length) return
    if (items.length + files.length > MAX_PHOTOS) {
      setError(`Choose up to ${MAX_PHOTOS} photos per batch. Remove a photo or start a new batch.`)
      return
    }
    if (files.some(file => file.size === 0 || file.size > MAX_BYTES || !isPhotoFile(file))) {
      setError('Choose JPEG, PNG, WebP, HEIC, or HEIF files between 1 byte and 10 MB each.')
      return
    }
    setError('')
    setItems(previous => [...previous, ...files.map(file => {
      const preview = URL.createObjectURL(file)
      urls.current.add(preview)
      return { id: preview, file, preview, status: 'pending', message: 'Ready' }
    })])
  }

  function remove(id) {
    if (running.current) return
    URL.revokeObjectURL(id)
    urls.current.delete(id)
    setItems(previous => previous.filter(item => item.id !== id))
  }

  async function process(queue) {
    if (running.current || isLoading || !queue.length) return
    running.current = true
    setBusy(true)
    const update = (id, patch) => {
      if (mounted.current) setItems(previous => previous.map(item => item.id === id ? { ...item, ...patch } : item))
    }
    try {
      for (const [index, item] of queue.entries()) {
        if (!mounted.current) break
        update(item.id, { status: 'processing', message: `Processing photo ${index + 1} of ${queue.length}…` })
        try {
          const data = await processUploadedClothes(item.file)
          if (!data?.garments?.length) throw new Error('No clothes detected. Try a clearer photo.')
          update(item.id, { status: 'success', message: `Added ${data.garments.length} garment(s)` })
        } catch (failure) {
          update(item.id, { status: 'failed', message: failure.message || 'Upload failed. Please retry.' })
        }
      }
    } finally {
      running.current = false
      if (mounted.current) setBusy(false)
    }
  }

  const pending = items.filter(item => item.status === 'pending')
  const failed = items.filter(item => item.status === 'failed')
  return <section className="px-5 py-4 space-y-4" aria-label="Gallery upload">
    <p>Up to 5 photos per batch, 10 MB each. Photos are processed one at a time.</p>
    <input ref={input} type="file" accept={PHOTO_ACCEPT} multiple onChange={select} disabled={busy} className="hidden" aria-label="Clothing photos" />
    <button className="btn-primary" onClick={() => input.current?.click()} disabled={busy || items.length >= MAX_PHOTOS}>Select from Gallery</button>
    {error && <p role="alert">{error}</p>}
    <p>{items.length} photo(s) selected</p>
    <div role="status" aria-live="polite">
      {items.length > 0 && <p>{items.filter(item => item.status === 'success').length} succeeded · {failed.length} failed · {pending.length} waiting</p>}
      {busy && <p>Keep this page open. Leaving stops the queue after the current photo.</p>}
    </div>
    <ul className="space-y-4">
      {items.map(item => <li key={item.id} className="rounded-xl border p-3">
        <UploadPreview src={item.preview} alt={`Preview of ${item.file.name}`} className="h-32 w-full object-contain" />
        <p className="break-all">{item.file.name}</p>
        <p role="status">{item.message}</p>
        <button disabled={busy} onClick={() => remove(item.id)} aria-label={`Remove ${item.file.name}`}>Remove</button>
        {item.status === 'failed' && <button disabled={busy || isLoading} onClick={() => process([item])} aria-label={`Retry ${item.file.name}`}>Retry</button>}
      </li>)}
    </ul>
    {pending.length > 0 && <button className="btn-primary" disabled={busy || isLoading} onClick={() => process(pending)}>Detect &amp; Add {pending.length} photo(s)</button>}
    {!busy && items.some(item => item.status === 'success') && onDone && <button className="btn-secondary" onClick={onDone}>Continue with added clothes</button>}
    {failed.length > 0 && <p>Only retry failed photos; successful photos will not be processed again. A network failure may occur after saving—check your wardrobe before retrying.</p>}
  </section>
}
