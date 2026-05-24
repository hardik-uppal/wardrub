import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Shirt, User, Plus, Trash2 } from 'lucide-react'
import { useWardrobe } from '../context/WardrobeContext'
import LoadingOverlay from '../components/LoadingOverlay'
import GarmentPreview from '../components/GarmentPreview'
import BottomNav from '../components/BottomNav'

const categories = [
  { id: 'all', label: 'All' },
  { id: 'top', label: 'Tops' },
  { id: 'bottom', label: 'Bottoms' },
  { id: 'dress', label: 'Dresses' },
  { id: 'outerwear', label: 'Outerwear' },
]

export default function Home() {
  const navigate = useNavigate()
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
  
  const [activeCategory, setActiveCategory] = useState('all')
  const [deleteMode, setDeleteMode] = useState(false)
  const [pressTimer, setPressTimer] = useState(null)
  const [selectedGarment, setSelectedGarment] = useState(null)
  const [isDeleting, setIsDeleting] = useState(false)

  useEffect(() => {
    fetchGarments(activeCategory === 'all' ? null : activeCategory)
  }, [activeCategory, fetchGarments])

  const handleCategoryChange = (categoryId) => {
    setActiveCategory(categoryId)
    setDeleteMode(false)
  }

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

  const handleDeleteGarment = async (garmentId) => {
    setIsDeleting(true)
    try {
      await deleteGarment(garmentId)
    } catch (err) {
      console.error('Delete failed:', err)
    } finally {
      setIsDeleting(false)
    }
  }
  
  const handleGarmentClick = (garment) => {
    if (deleteMode) {
      handleDeleteGarment(garment.id)
    } else {
      setSelectedGarment(garment)
    }
  }

  const filteredGarments = activeCategory === 'all' 
    ? garments 
    : garments.filter(g => g.category === activeCategory)

  return (
    <div className="min-h-screen safe-top safe-bottom" style={{ background: 'var(--bg-primary)' }}>
      {isLoading && <LoadingOverlay message={loadingMessage} />}
      
      {/* Error Toast */}
      {error && (
        <div 
          className="fixed top-4 left-4 right-4 z-50 px-5 py-4 rounded-2xl shadow-lg animate-fade-in cursor-pointer"
          style={{ background: 'var(--error)', color: 'white' }}
          onClick={clearError}
        >
          <p className="text-sm font-medium">{error}</p>
          <p className="text-xs opacity-70 mt-1">Tap to dismiss</p>
        </div>
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

        {/* Category Filter — Horizontal pills on ALL screen sizes (no sidebar overlap issue) */}
        <div className="mx-4 mt-4 glass-card-static p-4">
          <div className="flex gap-2 flex-wrap justify-center">
            {categories.map(cat => (
              <button
                key={cat.id}
                onClick={() => handleCategoryChange(cat.id)}
                className="px-5 py-2.5 rounded-full text-sm font-semibold transition-all"
                style={{
                  background: activeCategory === cat.id ? 'var(--accent)' : 'var(--glass-bg)',
                  color: activeCategory === cat.id ? 'white' : 'var(--text-secondary)',
                  border: activeCategory === cat.id ? '1px solid var(--accent)' : '1px solid var(--glass-border)',
                  boxShadow: 'none',
                }}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        {/* Delete Mode Hint */}
        {deleteMode && (
          <div className="mx-4 mt-4 rounded-2xl px-5 py-4" style={{ background: 'rgba(248, 113, 113, 0.15)', border: '1px solid rgba(248, 113, 113, 0.3)' }}>
            <p className="text-sm text-center font-medium" style={{ color: 'var(--error)' }}>
              Tap items to delete • Tap outside to cancel
            </p>
          </div>
        )}

        {/* Clothes Grid */}
        <div 
          className="mx-4 mt-4 glass-card-static p-5"
          onClick={() => deleteMode && setDeleteMode(false)}
        >
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            {/* Add Button */}
            <button
              onClick={(e) => { e.stopPropagation(); navigate('/capture'); }}
              className="aspect-square rounded-2xl flex flex-col items-center justify-center gap-2 transition-all hover:scale-[1.03] active:scale-95"
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
              <button
                key={garment.id}
                className={`relative aspect-square rounded-2xl overflow-hidden transition-all hover:scale-[1.03] active:scale-95 animate-fade-in ${
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
                onClick={(e) => { e.stopPropagation(); handleGarmentClick(garment); }}
              >
                <img
                  src={garment.front_url || garment.url}
                  alt={garment.category}
                  className="w-full h-full object-contain p-3"
                  loading="lazy"
                />
                {/* Category badge */}
                <div
                  className="absolute bottom-2 left-2 px-2 py-0.5 rounded-md text-[9px] font-semibold uppercase tracking-wider"
                  style={{
                    background: 'rgba(0,0,0,0.6)',
                    color: 'var(--text-secondary)',
                    backdropFilter: 'blur(8px)',
                  }}
                >
                  {garment.category}
                </div>
                {deleteMode && (
                  <div
                    className="absolute inset-0 flex items-center justify-center"
                    style={{ background: 'rgba(248, 113, 113, 0.8)' }}
                  >
                    <Trash2 className="w-6 h-6 text-white" />
                  </div>
                )}
              </button>
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
                {activeCategory === 'all' ? 'Your wardrobe is empty' : `No ${categories.find(c => c.id === activeCategory)?.label.toLowerCase()} yet`}
              </p>
              <p className="text-sm mt-2" style={{ color: 'var(--text-tertiary)' }}>
                Tap the + button to add clothes
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
      
      {/* Bottom Navigation */}
      <BottomNav />
    </div>
  )
}
