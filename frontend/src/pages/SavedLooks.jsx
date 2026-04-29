import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Image, User, Trash2, Sparkles } from 'lucide-react'
import { useWardrobe } from '../context/WardrobeContext'
import LoadingOverlay from '../components/LoadingOverlay'
import LookPreview from '../components/LookPreview'
import BottomNav from '../components/BottomNav'

export default function SavedLooks() {
  const navigate = useNavigate()
  const { 
    avatarUrl, 
    looks,
    isLoading, 
    loadingMessage,
    error,
    fetchLooks,
    deleteLook,
    clearError 
  } = useWardrobe()
  
  const [deleteMode, setDeleteMode] = useState(false)
  const [pressTimer, setPressTimer] = useState(null)
  const [selectedLook, setSelectedLook] = useState(null)
  const [isDeleting, setIsDeleting] = useState(false)

  useEffect(() => {
    fetchLooks()
  }, [fetchLooks])

  const handleLongPress = () => {
    setDeleteMode(true)
  }

  const handlePressStart = () => {
    const timer = setTimeout(handleLongPress, 500)
    setPressTimer(timer)
  }

  const handlePressEnd = () => {
    if (pressTimer) {
      clearTimeout(pressTimer)
      setPressTimer(null)
    }
  }

  const handleDeleteLook = async (lookId) => {
    setIsDeleting(true)
    try {
      await deleteLook(lookId)
    } catch (err) {
      console.error('Delete look failed:', err)
    } finally {
      setIsDeleting(false)
    }
  }
  
  const handleLookClick = (look) => {
    if (deleteMode) {
      handleDeleteLook(look.id)
    } else {
      setSelectedLook(look)
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-[var(--color-cream)] safe-top safe-bottom">
      {isLoading && <LoadingOverlay message={loadingMessage} />}
      
      {/* Error Toast */}
      {error && (
        <div 
          className="fixed top-4 left-4 right-4 z-50 bg-[var(--color-terracotta)] text-white px-4 py-3 rounded-2xl shadow-lg animate-fade-in max-w-md mx-auto"
          onClick={clearError}
        >
          <p className="text-sm">{error}</p>
          <p className="text-xs opacity-70 mt-1">Tap to dismiss</p>
        </div>
      )}

      <div className="flex-1 flex flex-col page-container space-y-6">
        {/* Header Card */}
        <header 
          className="mx-4 mt-4 flex items-center justify-between flex-shrink-0"
          style={{
            backgroundColor: '#FFFFFF',
            borderRadius: '24px',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
            padding: '24px',
          }}
        >
          {/* Spacer for centering */}
          <div className="w-12" />
          
          <div className="text-center">
            <h1 className="text-xl font-bold text-[var(--color-charcoal)]">
              Saved Looks
            </h1>
            <p className="text-sm text-[var(--color-warm-gray)] mt-1">
              {looks.length} {looks.length === 1 ? 'look' : 'looks'}
            </p>
          </div>
          
          <button
            onClick={() => avatarUrl ? navigate('/profile') : navigate('/create-avatar')}
            className="w-12 h-12 rounded-full overflow-hidden border-2 border-[var(--color-terracotta)] transition-transform hover:scale-105 active:scale-95 flex-shrink-0"
          >
            {avatarUrl ? (
              <img 
                src={avatarUrl} 
                alt="Your avatar" 
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full bg-[var(--color-blush)]/30 flex items-center justify-center">
                <User className="w-5 h-5 text-[var(--color-terracotta)]" />
              </div>
            )}
          </button>
        </header>

        {/* Delete Mode Hint */}
        {deleteMode && (
          <div className="mx-4 bg-[var(--color-blush)] rounded-2xl px-5 py-4 flex-shrink-0">
            <p className="text-sm text-[var(--color-terracotta)] text-center font-medium">
              Tap looks to delete • Tap outside to cancel
            </p>
          </div>
        )}

        {/* Looks Grid Card */}
        <div 
          className="mx-4 flex-1 bg-white rounded-3xl shadow-sm p-6 mb-4 overflow-y-auto"
          onClick={() => deleteMode && setDeleteMode(false)}
        >
          {looks.length === 0 ? (
            <div className="flex flex-col items-center justify-center text-center py-16">
              <div className="w-20 h-20 rounded-full bg-[var(--color-terracotta)]/10 flex items-center justify-center mb-6">
                <Image className="w-10 h-10 text-[var(--color-terracotta)]" />
              </div>
              <h3 className="text-lg font-semibold text-[var(--color-charcoal)] mb-2">
                No saved looks yet
              </h3>
              <p className="text-sm text-[var(--color-warm-gray)] max-w-xs mb-6">
                Try on clothes in the dressing room to create and save your favorite outfits
              </p>
              <button
                onClick={() => navigate('/dressing-room')}
                className="px-6 py-3 bg-[var(--color-terracotta)] text-white rounded-xl font-medium text-sm flex items-center gap-2 hover:bg-[var(--color-terracotta)]/90 transition-colors"
              >
                <Sparkles className="w-4 h-4" />
                Try On Clothes
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 nav-bottom-spacing">
              {looks.map((look) => (
                <button
                  key={look.id}
                  className={`relative aspect-[3/4] rounded-2xl overflow-hidden bg-[var(--color-cream)] transition-all active:scale-95 hover:shadow-md ${
                    deleteMode ? 'animate-pulse-soft' : ''
                  }`}
                  onTouchStart={handlePressStart}
                  onTouchEnd={handlePressEnd}
                  onMouseDown={handlePressStart}
                  onMouseUp={handlePressEnd}
                  onMouseLeave={handlePressEnd}
                  onClick={() => handleLookClick(look)}
                >
                  <img
                    src={look.url}
                    alt="Saved look"
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                  {deleteMode && (
                    <div className="absolute inset-0 bg-[var(--color-terracotta)]/80 flex items-center justify-center">
                      <Trash2 className="w-6 h-6 text-white" />
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
      
      {/* Look Preview Modal */}
      {selectedLook && (
        <LookPreview
          look={selectedLook}
          onClose={() => setSelectedLook(null)}
          onDelete={handleDeleteLook}
          isDeleting={isDeleting}
        />
      )}
      
      {/* Bottom Navigation */}
      <BottomNav />
    </div>
  )
}

