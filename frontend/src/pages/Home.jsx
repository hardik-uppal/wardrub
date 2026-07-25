import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { MoreVertical, Plus, Search, Shirt, Trash2, User } from 'lucide-react'
import { useWardrobe } from '../context/WardrobeContext'
import LoadingOverlay from '../components/LoadingOverlay'
import GarmentPreview from '../components/GarmentPreview'
import BottomNav from '../components/BottomNav'
import ResilientImage from '../components/ResilientImage'

const categories = [
  { id: 'all', label: 'All' },
  { id: 'top', label: 'Tops' },
  { id: 'bottom', label: 'Bottoms' },
  { id: 'dress', label: 'Dresses' },
  { id: 'outerwear', label: 'Outerwear' },
]

function getGarmentName(garment) {
  if (typeof garment.description === 'string' && garment.description.trim()) {
    return garment.description
  }

  const description = garment.description || {}
  return description.short || description.name || `${garment.category || 'Wardrobe'} item`
}

export default function Home() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { 
    avatarUrl, 
    garments,
    isLoading, 
    loadingMessage,
    error,
    fetchGarments,
    deleteGarment,
    clearError 
  } = useWardrobe()
  
  const requestedCategory = searchParams.get('category')
  const [activeCategory, setActiveCategory] = useState(
    categories.some(category => category.id === requestedCategory)
      ? requestedCategory
      : 'all',
  )
  const [query, setQuery] = useState('')
  const [sortMode, setSortMode] = useState('recent')
  const [openMenuId, setOpenMenuId] = useState(null)
  const [selectedGarment, setSelectedGarment] = useState(null)
  const [pendingDelete, setPendingDelete] = useState(null)
  const [isDeleting, setIsDeleting] = useState(false)

  useEffect(() => {
    fetchGarments()
  }, [fetchGarments])

  const handleCategoryChange = (categoryId) => {
    setActiveCategory(categoryId)
    setOpenMenuId(null)
  }

  const handleDeleteGarment = async (garmentId) => {
    setIsDeleting(true)
    try {
      await deleteGarment(garmentId)
      setPendingDelete(null)
      setOpenMenuId(null)
    } catch (err) {
      console.error('Delete failed:', err)
    } finally {
      setIsDeleting(false)
    }
  }
  
  const categoryCounts = useMemo(() => Object.fromEntries(
    categories.map(category => [
      category.id,
      category.id === 'all'
        ? garments.length
        : garments.filter(garment => garment.category === category.id).length,
    ]),
  ), [garments])

  const filteredGarments = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()
    const filtered = garments.filter((garment) => {
      const matchesCategory = activeCategory === 'all' || garment.category === activeCategory
      const searchableText = `${getGarmentName(garment)} ${garment.category || ''}`.toLowerCase()
      return matchesCategory && (!normalizedQuery || searchableText.includes(normalizedQuery))
    })

    if (sortMode === 'name') {
      return [...filtered].sort((a, b) => getGarmentName(a).localeCompare(getGarmentName(b)))
    }
    if (sortMode === 'category') {
      return [...filtered].sort((a, b) => (a.category || '').localeCompare(b.category || ''))
    }
    return filtered
  }, [activeCategory, garments, query, sortMode])

  return (
    <div className="min-h-screen safe-top safe-bottom" style={{ background: 'var(--bg-primary)' }}>
      {isLoading && <LoadingOverlay message={loadingMessage} />}
      
      {/* Error Toast */}
      {error && (
        <button
          type="button"
          className="fixed top-4 left-4 right-4 z-50 px-5 py-4 rounded-2xl shadow-lg animate-fade-in cursor-pointer"
          style={{ background: 'var(--error)', color: 'white' }}
          onClick={clearError}
          aria-label="Dismiss error"
        >
          <p className="text-sm font-medium">{error}</p>
          <p className="text-xs opacity-70 mt-1">Tap to dismiss</p>
        </button>
      )}

      {/* Main Content */}
      <div className="page-container nav-bottom-spacing">
        
        {/* Header */}
        <header className="glass-card-static mx-4 mt-4 flex items-center justify-between p-5">
          <div className="w-10" />
          <div className="text-center">
            <h1 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
              My Wardrobe
            </h1>
            <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
              {garments.length} {garments.length === 1 ? 'item' : 'items'}
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

        {/* Search, sort, and category filters */}
        <div className="mx-4 mt-4 glass-card-static p-4 space-y-3">
          <div className="grid grid-cols-[minmax(0,1fr)_44px] gap-2 sm:flex">
            <label className="relative col-span-2 min-w-0 sm:col-span-1 sm:flex-1">
              <span className="sr-only">Search wardrobe</span>
              <Search
                className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4"
                style={{ color: 'var(--text-tertiary)' }}
                aria-hidden="true"
              />
              <input
                type="search"
                value={query}
                onChange={event => setQuery(event.target.value)}
                placeholder="Search your wardrobe"
                className="w-full h-11 pl-10 pr-3 rounded-md text-sm"
                style={{
                  color: 'var(--text-primary)',
                  background: 'var(--bg-primary)',
                  border: '1px solid var(--glass-border)',
                }}
              />
            </label>
            <label className="min-w-0">
              <span className="sr-only">Sort wardrobe</span>
              <select
                value={sortMode}
                onChange={event => setSortMode(event.target.value)}
                className="w-full h-11 px-3 rounded-md text-sm sm:w-auto"
                style={{
                  color: 'var(--text-primary)',
                  background: 'var(--bg-primary)',
                  border: '1px solid var(--glass-border)',
                }}
              >
                <option value="recent">Recent</option>
                <option value="name">Name</option>
                <option value="category">Category</option>
              </select>
            </label>
            <button
              type="button"
              onClick={() => navigate('/capture')}
              className="w-11 h-11 rounded-md flex items-center justify-center"
              style={{ color: 'white', background: 'var(--accent)' }}
              aria-label="Add clothes"
            >
              <Plus className="w-5 h-5" />
            </button>
          </div>

          <div className="flex gap-2 overflow-x-auto scrollbar-hide pb-1">
            {categories.map(cat => (
              <button
                key={cat.id}
                onClick={() => handleCategoryChange(cat.id)}
                className="px-4 py-2 rounded-full text-sm font-semibold transition-all whitespace-nowrap"
                style={{
                  background: activeCategory === cat.id ? 'var(--accent)' : 'var(--glass-bg)',
                  color: activeCategory === cat.id ? 'white' : 'var(--text-secondary)',
                  border: activeCategory === cat.id ? '1px solid var(--accent)' : '1px solid var(--glass-border)',
                  boxShadow: 'none',
                }}
              >
                {cat.label} <span className="opacity-70">{categoryCounts[cat.id]}</span>
              </button>
            ))}
          </div>
          <div className="flex items-center justify-between text-xs" style={{ color: 'var(--text-secondary)' }}>
            <span>{filteredGarments.length} shown</span>
            {(query || activeCategory !== 'all') && (
              <button
                type="button"
                className="underline"
                onClick={() => {
                  setQuery('')
                  setActiveCategory('all')
                }}
              >
                Clear filters
              </button>
            )}
          </div>
        </div>

        {/* Clothes Grid */}
        <div className="mx-4 mt-4 glass-card-static p-4 md:p-5">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            {/* Add Button */}
            <button
              onClick={() => navigate('/capture')}
              className="aspect-square rounded-xl flex flex-col items-center justify-center gap-2 transition-all hover:scale-[1.02] active:scale-95"
              style={{
                border: '2px dashed var(--accent)',
                background: 'rgba(224, 120, 80, 0.05)',
              }}
            >
              <Plus className="w-7 h-7" style={{ color: 'var(--accent)' }} />
              <span className="text-xs font-semibold" style={{ color: 'var(--accent)' }}>Add</span>
            </button>
            
            {/* Garment Items */}
            {filteredGarments.map((garment, i) => (
              <article
                key={garment.id}
                className="relative rounded-xl overflow-visible animate-fade-in"
                style={{
                  background: 'var(--glass-bg-elevated)',
                  border: '1px solid var(--glass-border)',
                  animationDelay: `${i * 0.03}s`,
                }}
              >
                <button
                  type="button"
                  onClick={() => setSelectedGarment(garment)}
                  className="block w-full aspect-square rounded-t-xl overflow-hidden transition-transform active:scale-[0.98]"
                  aria-label={`View ${getGarmentName(garment)}`}
                >
                  <ResilientImage
                    src={garment.thumbnail_url || garment.front_url || garment.url}
                    alt={getGarmentName(garment)}
                    className="w-full h-full object-contain p-3"
                    loading="lazy"
                  />
                </button>
                <div className="flex items-center gap-2 px-3 py-2 border-t" style={{ borderColor: 'var(--glass-border)' }}>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                      {getGarmentName(garment)}
                    </p>
                    <p className="text-xs capitalize" style={{ color: 'var(--text-secondary)' }}>
                      {garment.category}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setOpenMenuId(current => current === garment.id ? null : garment.id)}
                    className="w-9 h-9 rounded-full flex items-center justify-center"
                    style={{ background: 'var(--bg-secondary)' }}
                    aria-label={`More options for ${getGarmentName(garment)}`}
                    aria-expanded={openMenuId === garment.id}
                  >
                    <MoreVertical className="w-4 h-4" />
                  </button>
                </div>

                {openMenuId === garment.id && (
                  <div
                    className="absolute right-2 bottom-12 z-20 min-w-36 rounded-md overflow-hidden shadow-lg"
                    style={{ background: 'var(--bg-primary)', border: '1px solid var(--glass-border)' }}
                  >
                    <button
                      type="button"
                      className="w-full px-4 py-3 text-left text-sm"
                      onClick={() => {
                        setSelectedGarment(garment)
                        setOpenMenuId(null)
                      }}
                    >
                      View details
                    </button>
                    <button
                      type="button"
                      className="w-full px-4 py-3 text-left text-sm flex items-center gap-2"
                      style={{ color: 'var(--error)', borderTop: '1px solid var(--glass-border)' }}
                      onClick={() => setPendingDelete(garment)}
                    >
                      <Trash2 className="w-4 h-4" />
                      Delete…
                    </button>
                  </div>
                )}
              </article>
            ))}
          </div>
          
          {/* Empty State */}
          {filteredGarments.length === 0 && (
            <div className="flex flex-col items-center justify-center text-center py-20">
              <div
                className="w-20 h-20 rounded-full flex items-center justify-center mb-6"
                style={{ background: 'var(--glass-bg)' }}
              >
                <Shirt className="w-10 h-10" style={{ color: 'var(--text-tertiary)' }} />
              </div>
              <p className="text-lg font-semibold" style={{ color: 'var(--text-secondary)' }}>
                {garments.length === 0 ? 'Your wardrobe is empty' : 'No items match your filters'}
              </p>
              <p className="text-sm mt-2" style={{ color: 'var(--text-tertiary)' }}>
                {garments.length === 0 ? 'Add your first item to get started' : 'Try another search or category'}
              </p>
            </div>
          )}
        </div>
      </div>
      
      {/* Garment Preview Modal */}
      {selectedGarment && (
        <GarmentPreview
          garment={selectedGarment}
          onClose={() => setSelectedGarment(null)}
          onDelete={handleDeleteGarment}
          isDeleting={isDeleting}
        />
      )}

      {pendingDelete && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.72)' }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-garment-title"
        >
          <div className="w-full max-w-sm glass-card-elevated p-6">
            <h2 id="delete-garment-title" className="text-lg font-bold">Delete this item?</h2>
            <p className="text-sm mt-2" style={{ color: 'var(--text-secondary)' }}>
              {getGarmentName(pendingDelete)} will be removed from your wardrobe.
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
                onClick={() => handleDeleteGarment(pendingDelete.id)}
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
