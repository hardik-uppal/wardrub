import { useState } from 'react'
import { X, Trash2, Download, Share2 } from 'lucide-react'
import ResilientImage from './ResilientImage'

export default function LookPreview({ 
  look, 
  onClose, 
  onDelete,
  isDeleting = false 
}) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  
  if (!look) return null
  
  const handleDelete = async () => {
    if (onDelete) {
      await onDelete(look.id)
      onClose()
    }
  }
  
  const handleDownload = () => {
    const a = document.createElement('a')
    a.href = look.url
    a.download = `look-${look.id}.png`
    a.target = '_blank'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }
  
  const handleShare = async () => {
    try {
      if (navigator.share) {
        await navigator.share({
          title: 'My Look',
          text: 'Check out my virtual outfit!',
          url: look.url,
        })
      } else {
        await navigator.clipboard.writeText(look.url)
        alert('Link copied!')
      }
    } catch (err) {
      console.error('Share failed:', err)
    }
  }
  
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in"
      style={{ background: 'rgba(0,0,0,0.9)', backdropFilter: 'blur(8px)' }}
    >
      <button
        type="button"
        className="absolute inset-0"
        onClick={onClose}
        aria-label="Close look preview"
      />
      <div 
        className="relative z-10 w-full max-w-md md:max-w-lg glass-card-elevated overflow-hidden animate-scale-in"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5" style={{ borderBottom: '1px solid var(--glass-border)' }}>
          <span className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
            Saved Look
          </span>
          
          <button
            onClick={onClose}
            className="w-10 h-10 flex items-center justify-center rounded-full transition-colors"
            style={{ background: 'var(--glass-bg)' }}
          >
            <X className="w-5 h-5" style={{ color: 'var(--text-primary)' }} />
          </button>
        </div>
        
        {/* Look Image */}
        <div className="max-h-[60vh] overflow-auto p-4" style={{ background: 'var(--bg-tertiary)' }}>
          <ResilientImage
            src={look.url}
            alt="Saved look"
            className="w-full h-auto rounded-lg"
            fallbackClassName="w-full min-h-64 rounded-lg"
          />
        </div>
        
        {/* Actions */}
        <div className="p-5" style={{ borderTop: '1px solid var(--glass-border)' }}>
          {showDeleteConfirm ? (
            <div className="flex flex-col gap-4">
              <p className="text-base text-center" style={{ color: 'var(--text-primary)' }}>
                Delete this look?
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="btn-ghost flex-1 py-3.5"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  disabled={isDeleting}
                  className="flex-1 py-3.5 px-4 font-medium rounded-xl flex items-center justify-center gap-2 disabled:opacity-50"
                  style={{ background: 'var(--error)', color: 'white' }}
                >
                  {isDeleting ? (
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <>
                      <Trash2 className="w-4 h-4" />
                      Delete
                    </>
                  )}
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              <div className="flex gap-3">
                <button
                  onClick={handleDownload}
                  className="btn-primary flex-1 py-3.5"
                >
                  <Download className="w-4 h-4" />
                  Save
                </button>
                <button
                  onClick={handleShare}
                  className="btn-ghost flex-1 py-3.5"
                >
                  <Share2 className="w-4 h-4" />
                  Share
                </button>
              </div>
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="w-full py-3.5 px-4 font-medium rounded-xl flex items-center justify-center gap-2"
                style={{ border: '1px solid rgba(248, 113, 113, 0.3)', color: 'var(--error)', background: 'rgba(248, 113, 113, 0.05)' }}
              >
                <Trash2 className="w-4 h-4" />
                Delete Look
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
