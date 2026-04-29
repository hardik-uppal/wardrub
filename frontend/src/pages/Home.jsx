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
    <div className="min-h-screen bg-[var(--color-cream)] safe-top safe-bottom">
      {isLoading && <LoadingOverlay message={loadingMessage} />}
      
      {/* Error Toast */}
      {error && (
        <div 
          className="fixed top-4 left-4 right-4 z-50 bg-[var(--color-terracotta)] text-white px-5 py-4 rounded-2xl shadow-lg animate-fade-in page-container"
          onClick={clearError}
        >
          <p className="text-sm font-medium">{error}</p>
          <p className="text-xs opacity-70 mt-1">Tap to dismiss</p>
        </div>
      )}

      {/* Main Content - Stack of Cards */}
      <div className="page-container pb-32 space-y-6">
        
        {/* Header Card */}
        <header 
          className="mx-4 mt-4 flex items-center justify-between"
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
              My Wardrobe
            </h1>
            <p className="text-sm text-[var(--color-warm-gray)] mt-1">
              {garments.length} {garments.length === 1 ? 'item' : 'items'}
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

        {/* Category Filter Card */}
        <div className="mx-4 bg-white rounded-3xl shadow-sm p-6">
          <p className="text-xs font-semibold text-[var(--color-warm-gray)] uppercase tracking-wider mb-5 text-center">
            Filter by Category
          </p>
          <div className="flex gap-3 flex-wrap justify-center">
            {categories.map(cat => (
              <button
                key={cat.id}
                onClick={() => handleCategoryChange(cat.id)}
                style={{
                  height: '48px',
                  paddingLeft: '32px',
                  paddingRight: '32px',
                  borderRadius: '9999px',
                  fontSize: '14px',
                  fontWeight: '600',
                  transition: 'all 0.2s',
                  backgroundColor: activeCategory === cat.id ? '#2D2D2D' : '#F5F5F5',
                  color: activeCategory === cat.id ? '#FFFFFF' : '#6B6B6B',
                  boxShadow: activeCategory === cat.id ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none',
                }}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        {/* Delete Mode Hint */}
        {deleteMode && (
          <div className="mx-4 bg-[var(--color-blush)] rounded-2xl px-5 py-4">
            <p className="text-sm text-[var(--color-terracotta)] text-center font-medium">
              Tap items to delete • Tap outside to cancel
            </p>
          </div>
        )}

        {/* Clothes Grid Card */}
        <div 
          className="mx-4 bg-white rounded-3xl shadow-sm p-6"
          onClick={() => deleteMode && setDeleteMode(false)}
        >
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-5">
            {/* Add Button */}
            <button
              onClick={(e) => { e.stopPropagation(); navigate('/capture'); }}
              className="aspect-square rounded-2xl border-2 border-dashed border-[var(--color-terracotta)]/50 flex flex-col items-center justify-center gap-3 hover:border-[var(--color-terracotta)] hover:bg-[var(--color-blush)]/30 transition-all"
            >
              <Plus className="w-8 h-8 text-[var(--color-terracotta)]" />
              <span className="text-sm font-semibold text-[var(--color-terracotta)]">Add</span>
            </button>
            
            {/* Garment Items */}
            {filteredGarments.map((garment) => (
              <button
                key={garment.id}
                className={`relative aspect-square rounded-2xl overflow-hidden bg-[var(--color-cream)] transition-all active:scale-95 hover:shadow-lg ${
                  deleteMode ? 'animate-pulse-soft' : ''
                }`}
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
                {deleteMode && (
                  <div className="absolute inset-0 bg-[var(--color-terracotta)]/85 flex items-center justify-center">
                    <Trash2 className="w-6 h-6 text-white" />
                  </div>
                )}
              </button>
            ))}
          </div>
          
          {/* Empty State */}
          {filteredGarments.length === 0 && (
            <div className="flex flex-col items-center justify-center text-center py-20">
              <div className="w-20 h-20 rounded-full bg-[var(--color-cream)] flex items-center justify-center mb-6">
                <Shirt className="w-10 h-10 text-[var(--color-warm-gray)]/50" />
              </div>
              <p className="text-lg font-semibold text-[var(--color-warm-gray)]">
                {activeCategory === 'all' ? 'Your wardrobe is empty' : `No ${categories.find(c => c.id === activeCategory)?.label.toLowerCase()} yet`}
              </p>
              <p className="text-sm text-[var(--color-warm-gray)]/70 mt-2">
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
