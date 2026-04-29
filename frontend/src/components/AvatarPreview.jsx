import { useState } from 'react'
import { X, Trash2, RefreshCw, User } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function AvatarPreview({ 
  avatarUrl, 
  onClose, 
  onDelete,
  isDeleting = false 
}) {
  const navigate = useNavigate()
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  
  if (!avatarUrl) return null
  
  const handleDelete = async () => {
    if (onDelete) {
      await onDelete()
      onClose()
    }
  }
  
  const handleUpdate = () => {
    onClose()
    navigate('/create-avatar')
  }
  
  return (
    <div 
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in"
      onClick={onClose}
    >
      <div 
        className="relative w-full max-w-sm bg-[var(--color-cream)] rounded-3xl overflow-hidden shadow-2xl animate-scale-up"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-[var(--color-warm-gray)]/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[var(--color-terracotta)]/10 flex items-center justify-center">
              <User className="w-5 h-5 text-[var(--color-terracotta)]" />
            </div>
            <span className="text-base font-semibold text-[var(--color-charcoal)]">
              Your Avatar
            </span>
          </div>
          
          <button
            onClick={onClose}
            className="w-10 h-10 flex items-center justify-center rounded-full bg-[var(--color-warm-gray)]/10 transition-colors hover:bg-[var(--color-warm-gray)]/20"
          >
            <X className="w-5 h-5 text-[var(--color-charcoal)]" />
          </button>
        </div>
        
        {/* Avatar Image */}
        <div className="relative bg-white p-4">
          <div className="aspect-[9/16] max-h-[60vh]">
            <img
              src={avatarUrl}
              alt="Your avatar"
              className="w-full h-full object-contain"
            />
          </div>
        </div>
        
        {/* Actions */}
        <div className="p-5 border-t border-[var(--color-warm-gray)]/10 space-y-3">
          {showDeleteConfirm ? (
            <div className="flex flex-col gap-4">
              <p className="text-base text-center text-[var(--color-charcoal)]">
                Delete your avatar? You'll need to create a new one.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="flex-1 py-3.5 px-4 bg-[var(--color-warm-gray)]/10 text-[var(--color-charcoal)] font-medium rounded-xl transition-all hover:bg-[var(--color-warm-gray)]/20"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  disabled={isDeleting}
                  className="flex-1 py-3.5 px-4 bg-[var(--color-terracotta)] text-white font-medium rounded-xl transition-all hover:bg-[var(--color-terracotta)]/90 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isDeleting ? (
                    <>
                      <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Deleting...
                    </>
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
            <>
              {/* Update Avatar Button */}
              <button
                onClick={handleUpdate}
                className="w-full py-3.5 px-4 bg-[var(--color-charcoal)] text-white font-medium rounded-xl transition-all hover:bg-[var(--color-charcoal)]/90 flex items-center justify-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Update Avatar
              </button>
              
              {/* Delete Button */}
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="w-full py-3.5 px-4 border-2 border-[var(--color-terracotta)]/30 text-[var(--color-terracotta)] font-medium rounded-xl transition-all hover:bg-[var(--color-terracotta)]/10 flex items-center justify-center gap-2"
              >
                <Trash2 className="w-4 h-4" />
                Delete Avatar
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}


