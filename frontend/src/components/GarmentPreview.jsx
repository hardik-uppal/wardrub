import { useState } from 'react'
import { X, Trash2, ChevronLeft, ChevronRight, RotateCcw } from 'lucide-react'

export default function GarmentPreview({ 
  garment, 
  onClose, 
  onDelete,
  isDeleting = false 
}) {
  const [currentView, setCurrentView] = useState('front')
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  
  if (!garment) return null
  
  const hasBack = !!garment.back_url
  const currentUrl = currentView === 'front' ? (garment.front_url || garment.url) : garment.back_url
  
  const toggleView = () => {
    if (hasBack) {
      setCurrentView(prev => prev === 'front' ? 'back' : 'front')
    }
  }
  
  const handleDelete = async () => {
    if (onDelete) {
      await onDelete(garment.id)
      onClose()
    }
  }
  
  return (
    <div 
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in"
      onClick={onClose}
    >
      <div 
        className="relative w-full max-w-md bg-[var(--color-cream)] rounded-3xl overflow-hidden shadow-2xl animate-scale-up"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-[var(--color-warm-gray)]/10">
          <div className="flex items-center gap-3">
            <span className="px-4 py-1.5 bg-[var(--color-charcoal)] text-white text-sm font-medium rounded-full capitalize">
              {garment.category}
            </span>
            {hasBack && (
              <span className="text-sm text-[var(--color-warm-gray)]">
                {currentView === 'front' ? 'Front' : 'Back'} view
              </span>
            )}
          </div>
          
          <button
            onClick={onClose}
            className="w-10 h-10 flex items-center justify-center rounded-full bg-[var(--color-warm-gray)]/10 transition-colors hover:bg-[var(--color-warm-gray)]/20"
          >
            <X className="w-5 h-5 text-[var(--color-charcoal)]" />
          </button>
        </div>
        
        {/* Image Container */}
        <div className="relative aspect-square bg-white">
          <img
            src={currentUrl}
            alt={`${garment.category} - ${currentView} view`}
            className="w-full h-full object-contain p-8 transition-opacity duration-300"
          />
          
          {/* View Toggle Arrows */}
          {hasBack && (
            <>
              <button
                onClick={toggleView}
                className="absolute left-2 top-1/2 -translate-y-1/2 w-10 h-10 flex items-center justify-center rounded-full bg-white/90 shadow-lg transition-all hover:scale-110 active:scale-95"
              >
                <ChevronLeft className="w-5 h-5 text-[var(--color-charcoal)]" />
              </button>
              
              <button
                onClick={toggleView}
                className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 flex items-center justify-center rounded-full bg-white/90 shadow-lg transition-all hover:scale-110 active:scale-95"
              >
                <ChevronRight className="w-5 h-5 text-[var(--color-charcoal)]" />
              </button>
            </>
          )}
          
          {/* Flip Button */}
          {hasBack && (
            <button
              onClick={toggleView}
              className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 px-4 py-2 bg-[var(--color-charcoal)]/90 text-white text-sm font-medium rounded-full transition-all hover:bg-[var(--color-charcoal)] active:scale-95"
            >
              <RotateCcw className="w-4 h-4" />
              Flip to {currentView === 'front' ? 'Back' : 'Front'}
            </button>
          )}
          
          {/* View Indicators */}
          {hasBack && (
            <div className="absolute bottom-4 right-4 flex gap-1.5">
              <div className={`w-2 h-2 rounded-full transition-colors ${
                currentView === 'front' 
                  ? 'bg-[var(--color-terracotta)]' 
                  : 'bg-[var(--color-warm-gray)]/30'
              }`} />
              <div className={`w-2 h-2 rounded-full transition-colors ${
                currentView === 'back' 
                  ? 'bg-[var(--color-terracotta)]' 
                  : 'bg-[var(--color-warm-gray)]/30'
              }`} />
            </div>
          )}
        </div>
        
        {/* Actions */}
        <div className="p-5 border-t border-[var(--color-warm-gray)]/10">
          {showDeleteConfirm ? (
            <div className="flex flex-col gap-4">
              <p className="text-base text-center text-[var(--color-charcoal)]">
                Delete this garment from your wardrobe?
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
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="w-full py-3.5 px-4 border-2 border-[var(--color-terracotta)]/30 text-[var(--color-terracotta)] font-medium rounded-xl transition-all hover:bg-[var(--color-terracotta)]/10 flex items-center justify-center gap-2"
            >
              <Trash2 className="w-4 h-4" />
              Remove from Wardrobe
            </button>
          )}
        </div>
      </div>
    </div>
  )
}


