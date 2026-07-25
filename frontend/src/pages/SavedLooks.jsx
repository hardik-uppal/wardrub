import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Heart, Image, MoreVertical, Share2, Sparkles, Trash2, User } from 'lucide-react'
import { useWardrobe } from '../context/WardrobeContext'
import LoadingOverlay from '../components/LoadingOverlay'
import LookPreview from '../components/LookPreview'
import BottomNav from '../components/BottomNav'
import ResilientImage from '../components/ResilientImage'

const OCCASIONS = ['Everyday', 'Work', 'Weekend', 'Evening', 'Event']

function formatLookDate(value) {
  if (!value) return 'Saved look'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Saved look'
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() === new Date().getFullYear() ? undefined : 'numeric',
  }).format(date)
}

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
    updateLook,
    clearError 
  } = useWardrobe()
  
  const [selectedLook, setSelectedLook] = useState(null)
  const [openMenuId, setOpenMenuId] = useState(null)
  const [viewMode, setViewMode] = useState('all')
  const [sortMode, setSortMode] = useState('newest')
  const [pendingDelete, setPendingDelete] = useState(null)
  const [isDeleting, setIsDeleting] = useState(false)

  useEffect(() => {
    fetchLooks()
  }, [fetchLooks])

  const handleDeleteLook = async (lookId) => {
    setIsDeleting(true)
    try {
      await deleteLook(lookId)
      setPendingDelete(null)
      setOpenMenuId(null)
    } catch (err) {
      console.error('Delete look failed:', err)
    } finally {
      setIsDeleting(false)
    }
  }

  const handleUpdateLook = async (lookId, updates) => {
    try {
      await updateLook(lookId, updates)
    } catch (updateError) {
      console.error('Update look failed:', updateError)
    } finally {
      setOpenMenuId(null)
    }
  }
  
  const handleShareLook = async (look) => {
    try {
      if (navigator.share) {
        await navigator.share({
          title: 'My Wardrub look',
          text: 'A look from my Wardrub',
          url: look.url,
        })
      } else {
        await navigator.clipboard.writeText(look.url)
      }
    } catch (shareError) {
      if (shareError?.name !== 'AbortError') {
        console.error('Share failed:', shareError)
      }
    }
    setOpenMenuId(null)
  }

  const visibleLooks = useMemo(() => {
    const filtered = viewMode === 'favorites'
      ? looks.filter(look => look.favorite)
      : [...looks]

    return filtered.sort((a, b) => {
      const aTime = a.created_at ? new Date(a.created_at).getTime() : 0
      const bTime = b.created_at ? new Date(b.created_at).getTime() : 0
      return sortMode === 'oldest' ? aTime - bTime : bTime - aTime
    })
  }, [looks, sortMode, viewMode])

  return (
    <div className="min-h-screen flex flex-col safe-top safe-bottom" style={{ background: 'var(--bg-primary)' }}>
      {isLoading && <LoadingOverlay message={loadingMessage} />}
      
      {/* Error Toast */}
      {error && (
        <button
          type="button"
          className="fixed top-4 left-4 right-4 z-50 px-4 py-3 rounded-2xl shadow-lg animate-fade-in max-w-md mx-auto cursor-pointer"
          style={{ background: 'var(--error)', color: 'white' }}
          onClick={clearError}
          aria-label="Dismiss error"
        >
          <p className="text-sm">{error}</p>
          <p className="text-xs opacity-70 mt-1">Tap to dismiss</p>
        </button>
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
            aria-label="Open profile"
          >
            {avatarUrl ? (
              <ResilientImage
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

        <div className="mx-4 flex items-center gap-2">
          <div className="flex p-1 rounded-md flex-1" style={{ background: 'var(--bg-secondary)' }}>
            {[
              ['all', 'All'],
              ['favorites', 'Favorites'],
            ].map(([value, label]) => (
              <button
                key={value}
                type="button"
                className="flex-1 px-3 py-2 rounded text-sm font-medium"
                style={{
                  background: viewMode === value ? 'var(--bg-primary)' : 'transparent',
                  color: viewMode === value ? 'var(--text-primary)' : 'var(--text-secondary)',
                }}
                onClick={() => setViewMode(value)}
              >
                {label}
              </button>
            ))}
          </div>
          <label>
            <span className="sr-only">Sort looks</span>
            <select
              value={sortMode}
              onChange={event => setSortMode(event.target.value)}
              className="h-11 px-3 rounded-md text-sm"
              style={{ background: 'var(--bg-primary)', border: '1px solid var(--glass-border)' }}
            >
              <option value="newest">Newest</option>
              <option value="oldest">Oldest</option>
            </select>
          </label>
        </div>

        {/* Looks Grid */}
        <div className="mx-4 flex-1 glass-card-static p-4 md:p-5 mb-4 overflow-y-auto">
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
          ) : visibleLooks.length === 0 ? (
            <div className="flex flex-col items-center justify-center text-center py-16">
              <Heart className="w-10 h-10 mb-4" style={{ color: 'var(--text-tertiary)' }} />
              <h3 className="text-lg font-semibold">No favorite looks yet</h3>
              <p className="text-sm mt-2" style={{ color: 'var(--text-secondary)' }}>
                Mark a look as favorite to keep it close.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4 nav-bottom-spacing">
              {visibleLooks.map((look, i) => (
                <article
                  key={look.id}
                  className="relative rounded-xl animate-fade-in"
                  style={{
                    background: 'var(--glass-bg-elevated)',
                    border: '1px solid var(--glass-border)',
                    animationDelay: `${i * 0.03}s`,
                  }}
                >
                  <button
                    type="button"
                    className="relative block w-full aspect-[3/4] rounded-t-xl overflow-hidden active:scale-[0.99]"
                    onClick={() => setSelectedLook(look)}
                    aria-label={`Open look from ${formatLookDate(look.created_at)}`}
                  >
                    <ResilientImage
                      src={look.thumbnail_url || look.url}
                      alt={`Look from ${formatLookDate(look.created_at)}`}
                      className="w-full h-full object-cover object-top"
                      loading="lazy"
                    />
                    {look.favorite && (
                      <span className="absolute top-2 left-2 w-8 h-8 rounded-full flex items-center justify-center bg-black/70">
                        <Heart className="w-4 h-4 fill-white text-white" aria-label="Favorite" />
                      </span>
                    )}
                  </button>

                  <div className="flex items-start gap-2 px-3 py-3">
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
                        {look.occasion || formatLookDate(look.created_at)}
                      </p>
                      <p className="text-xs capitalize truncate mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                        {look.garment_categories?.length
                          ? look.garment_categories.join(' + ')
                          : formatLookDate(look.created_at)}
                      </p>
                    </div>
                    <button
                      type="button"
                      className="w-9 h-9 rounded-full flex items-center justify-center"
                      style={{ background: 'var(--bg-secondary)' }}
                      onClick={() => setOpenMenuId(current => current === look.id ? null : look.id)}
                      aria-label="Look options"
                      aria-expanded={openMenuId === look.id}
                    >
                      <MoreVertical className="w-4 h-4" />
                    </button>
                  </div>

                  {openMenuId === look.id && (
                    <div
                      className="absolute right-2 bottom-12 z-20 min-w-44 rounded-md overflow-hidden shadow-lg"
                      style={{ background: 'var(--bg-primary)', border: '1px solid var(--glass-border)' }}
                    >
                      <button
                        type="button"
                        className="w-full px-4 py-3 text-left text-sm flex items-center gap-2"
                        onClick={() => handleUpdateLook(look.id, { favorite: !look.favorite })}
                      >
                        <Heart className={`w-4 h-4 ${look.favorite ? 'fill-current' : ''}`} />
                        {look.favorite ? 'Remove favorite' : 'Add favorite'}
                      </button>
                      <label
                        className="block px-4 py-3 text-sm"
                        style={{ borderTop: '1px solid var(--glass-border)' }}
                      >
                        <span className="block text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>
                          Occasion
                        </span>
                        <select
                          className="w-full bg-transparent"
                          value={look.occasion || ''}
                          onChange={event => handleUpdateLook(
                            look.id,
                            { occasion: event.target.value },
                          )}
                        >
                          <option value="">None</option>
                          {OCCASIONS.map(occasion => (
                            <option key={occasion} value={occasion}>{occasion}</option>
                          ))}
                        </select>
                      </label>
                      <button
                        type="button"
                        className="w-full px-4 py-3 text-left text-sm flex items-center gap-2"
                        style={{ borderTop: '1px solid var(--glass-border)' }}
                        onClick={() => handleShareLook(look)}
                      >
                        <Share2 className="w-4 h-4" />
                        Share
                      </button>
                      <button
                        type="button"
                        className="w-full px-4 py-3 text-left text-sm flex items-center gap-2"
                        style={{ color: 'var(--error)', borderTop: '1px solid var(--glass-border)' }}
                        onClick={() => setPendingDelete(look)}
                      >
                        <Trash2 className="w-4 h-4" />
                        Delete…
                      </button>
                    </div>
                  )}
                </article>
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

      {pendingDelete && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.72)' }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-look-title"
        >
          <div className="w-full max-w-sm glass-card-elevated p-6">
            <h2 id="delete-look-title" className="text-lg font-bold">Delete this look?</h2>
            <p className="text-sm mt-2" style={{ color: 'var(--text-secondary)' }}>
              This cannot be undone.
            </p>
            <div className="flex gap-3 mt-6">
              <button
                type="button"
                className="btn-ghost flex-1"
                onClick={() => setPendingDelete(null)}
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="flex-1 py-3 px-4 rounded-md font-medium"
                style={{ color: 'white', background: 'var(--error)' }}
                onClick={() => handleDeleteLook(pendingDelete.id)}
                disabled={isDeleting}
              >
                {isDeleting ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Bottom Navigation */}
      <BottomNav />
    </div>
  )
}
