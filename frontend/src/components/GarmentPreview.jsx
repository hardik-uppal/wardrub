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
      className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in"
      style={{ background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(8px)' }}
      onClick={onClose}
    >
      <div 
        className="relative w-full max-w-md md:max-w-lg glass-card-elevated overflow-hidden animate-scale-in"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5" style={{ borderBottom: '1px solid var(--glass-border)' }}>
          <div className="flex items-center gap-3">
            <span
              className="px-4 py-1.5 text-sm font-medium rounded-full capitalize"
              style={{ background: 'var(--accent-gradient)', color: 'white' }}
            >
              {garment.category}
            </span>
            {hasBack && (
              <span className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
                {currentView === 'front' ? 'Front' : 'Back'} view
              </span>
            )}
          </div>
          
          <button
            onClick={onClose}
            className="w-10 h-10 flex items-center justify-center rounded-full transition-colors"
            style={{ background: 'var(--glass-bg)' }}
          >
            <X className="w-5 h-5" style={{ color: 'var(--text-primary)' }} />
          </button>
        </div>
        
        {/* Image Container */}
        <div className="relative aspect-square" style={{ background: 'var(--bg-tertiary)' }}>
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
                className="absolute left-2 top-1/2 -translate-y-1/2 w-10 h-10 flex items-center justify-center rounded-full transition-all hover:scale-110 active:scale-95"
                style={{ background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(8px)' }}
              >
                <ChevronLeft className="w-5 h-5" style={{ color: 'var(--text-primary)' }} />
              </button>
              
              <button
                onClick={toggleView}
                className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 flex items-center justify-center rounded-full transition-all hover:scale-110 active:scale-95"
                style={{ background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(8px)' }}
              >
                <ChevronRight className="w-5 h-5" style={{ color: 'var(--text-primary)' }} />
              </button>
            </>
          )}
          
          {/* Flip Button */}
          {hasBack && (
            <button
              onClick={toggleView}
              className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-full transition-all active:scale-95"
              style={{ background: 'rgba(0,0,0,0.6)', color: 'var(--text-primary)', backdropFilter: 'blur(8px)' }}
            >
              <RotateCcw className="w-4 h-4" />
              Flip to {currentView === 'front' ? 'Back' : 'Front'}
            </button>
          )}
          
          {/* View Indicators */}
          {hasBack && (
            <div className="absolute bottom-4 right-4 flex gap-1.5">
              <div
                className="w-2 h-2 rounded-full transition-colors"
                style={{ background: currentView === 'front' ? 'var(--accent)' : 'var(--glass-bg-hover)' }}
              />
              <div
                className="w-2 h-2 rounded-full transition-colors"
                style={{ background: currentView === 'back' ? 'var(--accent)' : 'var(--glass-bg-hover)' }}
              />
            </div>
          )}
        </div>
        
        {/* Actions */}
        <div className="p-5" style={{ borderTop: '1px solid var(--glass-border)' }}>
          {showDeleteConfirm ? (
            <div className="flex flex-col gap-4">
              <p className="text-base text-center" style={{ color: 'var(--text-primary)' }}>
                Delete this garment from your wardrobe?
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
                  className="flex-1 py-3.5 px-4 font-medium rounded-xl transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                  style={{ background: 'var(--error)', color: 'white' }}
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
              className="w-full py-3.5 px-4 font-medium rounded-xl transition-all flex items-center justify-center gap-2"
              style={{ border: '1px solid rgba(248, 113, 113, 0.3)', color: 'var(--error)', background: 'rgba(248, 113, 113, 0.05)' }}
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
