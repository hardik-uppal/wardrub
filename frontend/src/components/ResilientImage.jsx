import { useState } from 'react'
import { ImageOff } from 'lucide-react'

export default function ResilientImage({
  src,
  alt,
  className = '',
  fallbackClassName = '',
  style,
  onError,
  loading = 'lazy',
  decoding = 'async',
  ...imageProps
}) {
  const [failedSrc, setFailedSrc] = useState(null)
  const hasFailed = !src || failedSrc === src

  if (hasFailed) {
    return (
      <div
        role="img"
        aria-label={`${alt || 'Image'} unavailable`}
        className={`flex items-center justify-center bg-[var(--bg-secondary)] text-[var(--text-tertiary)] ${fallbackClassName || className}`}
        style={style}
      >
        <ImageOff className="w-6 h-6" aria-hidden="true" />
      </div>
    )
  }

  return (
    <img
      {...imageProps}
      src={src}
      alt={alt}
      className={className}
      style={style}
      loading={loading}
      decoding={decoding}
      onError={(event) => {
        setFailedSrc(src)
        onError?.(event)
      }}
    />
  )
}
