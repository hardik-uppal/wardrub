import { useEffect, useRef, useState } from 'react'
import { useWardrobe } from '../context/WardrobeContext'
import { isPhotoFile, PHOTO_ACCEPT } from '../utils/imageUploads'
import { MAX_SOURCE_BYTES } from '../utils/preparePhoto'
import UploadPreview from './UploadPreview'
import Dialog from './Dialog'

const MAX_PHOTOS = 5

export default function GalleryUpload({ onDone }) {
  const { processUploadedClothes, isLoading } = useWardrobe()
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const running = useRef(false)
  const mounted = useRef(false)
  const urls = useRef(new Set())
  const input = useRef(null)
  const cameraInput = useRef(null)
  const video = useRef(null)
  const stream = useRef(null)
  const cameraRequest = useRef(0)
  const [cameraOpen, setCameraOpen] = useState(false)
  const [cameraReady, setCameraReady] = useState(false)
  function closeCamera() {
    cameraRequest.current++
    stream.current?.getTracks().forEach((track) => track.stop())
    stream.current = null
    setCameraOpen(false)
    setCameraReady(false)
  }
  async function openCamera() {
    const revision = ++cameraRequest.current
    setCameraOpen(true)
    setCameraReady(false)
    try {
      const media = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
        audio: false,
      })
      if (!mounted.current || revision !== cameraRequest.current) {
        media.getTracks().forEach((track) => track.stop())
        return
      }
      stream.current = media
      if (video.current) {
        video.current.srcObject = media
        await video.current.play()
      }
    } catch {
      if (!mounted.current || revision !== cameraRequest.current) return
      closeCamera()
      cameraInput.current?.click()
    }
  }
  function takePhoto() {
    if (!video.current?.videoWidth || !video.current?.videoHeight) return
    const canvas = document.createElement('canvas')
    canvas.width = video.current.videoWidth
    canvas.height = video.current.videoHeight
    canvas.getContext('2d').drawImage(video.current, 0, 0)
    canvas.toBlob(
      (blob) => {
        if (!blob || !mounted.current) return
        selectFiles([
          new File([blob], 'camera-photo.jpg', { type: 'image/jpeg' }),
        ])
        closeCamera()
      },
      'image/jpeg',
      0.92,
    )
  }

  useEffect(() => {
    mounted.current = true
    const previews = urls.current
    return () => {
      mounted.current = false
      stream.current?.getTracks().forEach((track) => track.stop())
      for (const url of previews) URL.revokeObjectURL(url)
      previews.clear()
    }
  }, [])

  function select(event) {
    const files = Array.from(event.target.files || [])
    event.target.value = ''
    selectFiles(files)
  }
  function selectFiles(files) {
    if (running.current || !files.length) return
    if (items.length + files.length > MAX_PHOTOS) {
      setError(
        `Choose up to ${MAX_PHOTOS} photos per batch. Remove a photo or start a new batch.`,
      )
      return
    }
    if (
      files.some(
        (file) =>
          file.size === 0 || file.size > MAX_SOURCE_BYTES || !isPhotoFile(file),
      )
    ) {
      setError(
        'Choose JPEG, PNG, WebP, HEIC, or HEIF files between 1 byte and 25 MB each.',
      )
      return
    }
    setError('')
    setItems((previous) => [
      ...previous,
      ...files.map((file) => {
        const preview = URL.createObjectURL(file)
        urls.current.add(preview)
        return {
          id: preview,
          file,
          preview,
          status: 'pending',
          message: 'Ready',
        }
      }),
    ])
  }

  function remove(id) {
    if (running.current) return
    URL.revokeObjectURL(id)
    urls.current.delete(id)
    setItems((previous) => previous.filter((item) => item.id !== id))
  }

  async function process(queue) {
    if (running.current || isLoading || !queue.length) return
    running.current = true
    setBusy(true)
    const update = (id, patch) => {
      if (mounted.current)
        setItems((previous) =>
          previous.map((item) =>
            item.id === id ? { ...item, ...patch } : item,
          ),
        )
    }
    try {
      for (const [index, item] of queue.entries()) {
        if (!mounted.current) break
        update(item.id, {
          status: 'processing',
          message: `Adding photo ${index + 1} of ${queue.length}…`,
        })
        try {
          const data = await processUploadedClothes(item.file)
          if (!data?.garments?.length)
            throw new Error('No clothes detected. Try a clearer photo.')
          update(item.id, {
            status: data.failed_count ? 'partial' : 'success',
            message: `Added ${data.garments.length} piece${data.garments.length === 1 ? '' : 's'}`,
            garments: data.garments,
            warning: data.failed_count
              ? 'Some pieces could not be added. Your saved pieces are kept; photograph only the missing ones.'
              : '',
          })
        } catch (failure) {
          update(item.id, {
            status: 'failed',
            message: failure.message || 'Upload failed. Please retry.',
          })
        }
      }
    } finally {
      running.current = false
      if (mounted.current) setBusy(false)
    }
  }

  const pending = items.filter((item) => item.status === 'pending')
  const failed = items.filter((item) => item.status === 'failed')
  const saved = items.some((item) =>
    ['success', 'partial'].includes(item.status),
  )
  return (
    <section className="photo-intake" aria-label="Add clothing photos">
      <input
        ref={input}
        type="file"
        accept={PHOTO_ACCEPT}
        multiple
        onChange={select}
        disabled={busy}
        className="hidden"
        aria-label="Clothing photos"
      />
      <input
        ref={cameraInput}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={select}
        disabled={busy}
        className="hidden"
        aria-label="Camera photo"
      />
      {!items.length && (
        <div className="actions photo-start">
          <button
            className="btn-primary"
            onClick={() => input.current?.click()}
          >
            Choose photo
          </button>
          <button className="btn-secondary" onClick={openCamera}>
            Take photo
          </button>
        </div>
      )}
      {error && <p role="alert">{error}</p>}
      {items.length > 1 && <p className="muted">{items.length} photos</p>}
      {busy && <p role="status">Adding your clothes. Keep this page open.</p>}
      <ul className="photo-queue">
        {items.map((item) => (
          <li key={item.id}>
            {['pending', 'processing', 'failed'].includes(item.status) && (
              <UploadPreview
                src={item.preview}
                alt={`Preview of ${item.file.name}`}
                className="capture-main-image"
              />
            )}
            {item.status !== 'pending' && <p role="status">{item.message}</p>}
            {item.garments && (
              <div className="added-pieces">
                {item.garments.map((garment) => (
                  <div key={garment.id}>
                    <UploadPreview
                      src={garment.front_url}
                      alt={garment.name || garment.category || 'Added clothing'}
                      className="added-piece-image"
                    />
                    <span>{garment.name || garment.category}</span>
                  </div>
                ))}
              </div>
            )}
            {item.warning && <p className="muted">{item.warning}</p>}
            {['pending', 'failed'].includes(item.status) && (
              <button
                className="text-action"
                disabled={busy}
                onClick={() => remove(item.id)}
                aria-label={`Remove ${item.file.name}`}
              >
                Remove
              </button>
            )}
            {item.status === 'failed' && (
              <button
                className="text-action"
                disabled={busy || isLoading}
                onClick={() => process([item])}
                aria-label={`Retry ${item.file.name}`}
              >
                Retry
              </button>
            )}
          </li>
        ))}
      </ul>
      <div className="actions">
        {pending.length > 0 && (
          <button
            className="btn-primary"
            disabled={busy || isLoading}
            onClick={() => process(pending)}
          >
            Add clothes
          </button>
        )}
        {!busy && saved && onDone && (
          <button
            className={pending.length ? 'btn-secondary' : 'btn-primary'}
            onClick={onDone}
          >
            Done
          </button>
        )}
        {!!items.length && !busy && (
          <button
            className="text-action"
            onClick={() => {
              if (
                items.every((item) =>
                  ['success', 'partial'].includes(item.status),
                )
              ) {
                items.forEach((item) => {
                  URL.revokeObjectURL(item.id)
                  urls.current.delete(item.id)
                })
                setItems([])
              }
              input.current?.click()
            }}
            disabled={
              items.length >= MAX_PHOTOS &&
              !items.every((item) =>
                ['success', 'partial'].includes(item.status),
              )
            }
          >
            Add another photo
          </button>
        )}
      </div>
      {failed.length > 0 && (
        <p className="muted">
          Check your wardrobe before retrying: a connection error can happen
          after saving.
        </p>
      )}
      {cameraOpen && (
        <Dialog title="Take a photo" onClose={closeCamera}>
          <video
            ref={(element) => {
              video.current = element
              if (element && stream.current) element.srcObject = stream.current
            }}
            autoPlay
            playsInline
            muted
            onLoadedData={() => setCameraReady(true)}
            className="capture-main-image"
          />
          <button
            className="btn-primary"
            disabled={!cameraReady}
            onClick={takePhoto}
          >
            Use photo
          </button>
        </Dialog>
      )}
    </section>
  )
}
