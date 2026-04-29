import { useState } from 'react'
import { X, Trash2, Download, Share2 } from 'lucide-react'

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
      className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4 animate-fade-in"
      onClick={onClose}
    >
      <div 
        className="relative w-full max-w-md bg-[var(--color-cream)] rounded-3xl overflow-hidden shadow-2xl animate-scale-up"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-[var(--color-warm-gray)]/10">
          <span className="text-base font-semibold text-[var(--color-charcoal)]">
            Saved Look
          </span>
          
          <button
            onClick={onClose}
            className="w-10 h-10 flex items-center justify-center rounded-full bg-[var(--color-warm-gray)]/10 transition-colors hover:bg-[var(--color-warm-gray)]/20"
          >
            <X className="w-5 h-5 text-[var(--color-charcoal)]" />
          </button>
        </div>
        
        {/* Look Image */}
        <div className="bg-white max-h-[60vh] overflow-auto p-4">
          <img
            src={look.url}
            alt="Saved look"
            className="w-full h-auto rounded-lg"
          />
        </div>
        
        {/* Actions */}
        <div className="p-5 border-t border-[var(--color-warm-gray)]/10">
          {showDeleteConfirm ? (
            <div className="flex flex-col gap-4">
              <p className="text-base text-center text-[var(--color-charcoal)]">
                Delete this look?
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="flex-1 py-3.5 px-4 bg-[var(--color-warm-gray)]/10 text-[var(--color-charcoal)] font-medium rounded-xl"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  disabled={isDeleting}
                  className="flex-1 py-3.5 px-4 bg-[var(--color-terracotta)] text-white font-medium rounded-xl flex items-center justify-center gap-2"
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
                  className="flex-1 py-3.5 px-4 bg-[var(--color-charcoal)] text-white font-medium rounded-xl flex items-center justify-center gap-2"
                >
                  <Download className="w-4 h-4" />
                  Save
                </button>
                <button
                  onClick={handleShare}
                  className="flex-1 py-3.5 px-4 bg-[var(--color-sage)] text-white font-medium rounded-xl flex items-center justify-center gap-2"
                >
                  <Share2 className="w-4 h-4" />
                  Share
                </button>
              </div>
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="w-full py-3.5 px-4 border-2 border-[var(--color-terracotta)]/30 text-[var(--color-terracotta)] font-medium rounded-xl flex items-center justify-center gap-2"
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


