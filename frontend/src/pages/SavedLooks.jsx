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
    <div className="min-h-screen flex flex-col safe-top safe-bottom" style={{ background: 'var(--bg-primary)' }}>
      {isLoading && <LoadingOverlay message={loadingMessage} />}
      
      {/* Error Toast */}
      {error && (
        <div 
          className="fixed top-4 left-4 right-4 z-50 px-4 py-3 rounded-2xl shadow-lg animate-fade-in max-w-md mx-auto cursor-pointer"
          style={{ background: 'var(--error)', color: 'white' }}
          onClick={clearError}
        >
          <p className="text-sm">{error}</p>
          <p className="text-xs opacity-70 mt-1">Tap to dismiss</p>
        </div>
      )}

      <div className="flex-1 flex flex-col page-container space-y-5">
        {/* Header */}
        <header className="mx-4 mt-4 glass-card-static flex items-center justify-between p-5 flex-shrink-0">
          <div className="w-11" />
          <div className="text-center">
            <h1 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
              Saved Looks
            </h1>
            <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
              {looks.length} {looks.length === 1 ? 'look' : 'looks'}
            </p>
          </div>
          <button
            onClick={() => avatarUrl ? navigate('/profile') : navigate('/create-avatar')}
            className="w-11 h-11 rounded-full overflow-hidden flex-shrink-0 transition-transform hover:scale-105 active:scale-95"
            style={{
              border: '1px solid var(--accent)',
            }}
          >
            {avatarUrl ? (
              <img 
                src={avatarUrl} 
                alt="Your avatar" 
                className="w-full h-full object-cover" 
                style={{ objectPosition: 'top center' }}
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center" style={{ background: 'var(--glass-bg)' }}>
                <User className="w-5 h-5" style={{ color: 'var(--accent)' }} />
              </div>
            )}
          </button>
        </header>

        {/* Delete Mode Hint */}
        {deleteMode && (
          <div className="mx-4 rounded-2xl px-5 py-4 flex-shrink-0" style={{ background: 'rgba(248, 113, 113, 0.15)', border: '1px solid rgba(248, 113, 113, 0.3)' }}>
            <p className="text-sm text-center font-medium" style={{ color: 'var(--error)' }}>
              Tap looks to delete • Tap outside to cancel
            </p>
          </div>
        )}

        {/* Looks Grid */}
        <div 
          className="mx-4 flex-1 glass-card-static p-5 mb-4 overflow-y-auto"
          onClick={() => deleteMode && setDeleteMode(false)}
        >
          {looks.length === 0 ? (
            <div className="flex flex-col items-center justify-center text-center py-16">
              <div
                className="w-20 h-20 rounded-2xl flex items-center justify-center mb-6"
                style={{ background: 'var(--accent-glow)' }}
              >
                <Image className="w-10 h-10" style={{ color: 'var(--accent-light)' }} />
              </div>
              <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
                No saved looks yet
              </h3>
              <p className="text-sm max-w-xs mb-6" style={{ color: 'var(--text-secondary)' }}>
                Try on clothes in the dressing room to create and save your favorite outfits
              </p>
              <button onClick={() => navigate('/dressing-room')} className="btn-primary">
                <Sparkles className="w-4 h-4" />
                Try On Clothes
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4 nav-bottom-spacing">
              {looks.map((look, i) => (
                <button
                  key={look.id}
                  className={`relative aspect-[3/4] rounded-2xl overflow-hidden transition-all active:scale-95 hover:scale-[1.03] animate-fade-in ${
                    deleteMode ? 'animate-pulse-soft' : ''
                  }`}
                  style={{
                    background: 'var(--glass-bg-elevated)',
                    border: '1px solid var(--glass-border)',
                    animationDelay: `${i * 0.03}s`,
                  }}
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
                    className="w-full h-full object-cover object-top"
                    loading="lazy"
                  />
                  {deleteMode && (
                    <div className="absolute inset-0 flex items-center justify-center" style={{ background: 'rgba(248, 113, 113, 0.8)' }}>
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
