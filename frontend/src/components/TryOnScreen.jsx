import { useState, useRef, useMemo } from 'react'
import { Sparkles, ChevronLeft, ChevronRight, Check, X } from 'lucide-react'

// Category configuration
const CATEGORIES = [
  { id: 'top', label: 'Tops', icon: '👕' },
  { id: 'bottom', label: 'Bottoms', icon: '👖' },
  { id: 'dress', label: 'Dresses', icon: '👗' },
  { id: 'outerwear', label: 'Outerwear', icon: '🧥' },
]

export default function TryOnScreen({ 
  avatarUrl, 
  garments, 
  onTryOn, 
  onTryOnMultiple,
  isLoading,
  multiSelect = true // Enable multi-select by default
}) {
  // Multi-selection state: { top: garment, bottom: garment, dress: garment, outerwear: garment }
  const [selectedGarments, setSelectedGarments] = useState({})
  const carouselRefs = useRef({})

  // Group garments by category
  const garmentsByCategory = useMemo(() => {
    const grouped = {}
    CATEGORIES.forEach(cat => {
      grouped[cat.id] = garments.filter(g => g.category === cat.id)
    })
    return grouped
  }, [garments])

  // Get selected garments as array
  const selectedGarmentsArray = useMemo(() => {
    return Object.values(selectedGarments).filter(Boolean)
  }, [selectedGarments])

  const selectedCount = selectedGarmentsArray.length

  // Handle garment selection with category-based logic
  const handleSelectGarment = (garment) => {
    if (!multiSelect) {
      // Single select mode - just select this garment
      setSelectedGarments({ [garment.category]: garment })
      return
    }

    setSelectedGarments(prev => {
      const newSelection = { ...prev }
      
      // If already selected, deselect it
      if (prev[garment.category]?.id === garment.id) {
        delete newSelection[garment.category]
        return newSelection
      }
      
      // Handle dress vs top/bottom mutual exclusivity
      if (garment.category === 'dress') {
        delete newSelection.top
        delete newSelection.bottom
        newSelection.dress = garment
      } else if (garment.category === 'top' || garment.category === 'bottom') {
        delete newSelection.dress
        newSelection[garment.category] = garment
      } else {
        newSelection[garment.category] = garment
      }
      
      return newSelection
    })
  }

  const isGarmentSelected = (garment) => {
    return selectedGarments[garment.category]?.id === garment.id
  }

  const scrollCarousel = (categoryId, direction) => {
    const ref = carouselRefs.current[categoryId]
    if (!ref) return
    const scrollAmount = direction === 'left' ? -120 : 120
    ref.scrollBy({ left: scrollAmount, behavior: 'smooth' })
  }

  const handleTryOn = () => {
    if (selectedCount === 0) return
    
    if (multiSelect && onTryOnMultiple) {
      onTryOnMultiple(selectedGarmentsArray)
    } else if (onTryOn && selectedGarmentsArray[0]) {
      onTryOn(selectedGarmentsArray[0])
    }
  }

  const clearSelection = () => {
    setSelectedGarments({})
  }

  return (
    <div className="flex flex-col h-full">
      {/* Avatar Display - 50% */}
      <div className="flex-[5] flex p-4 gap-4">
        {avatarUrl ? (
          <>
            {/* Avatar */}
            <div className="relative w-32 aspect-[9/16] rounded-2xl overflow-hidden bg-white shadow-xl flex-shrink-0">
              <img
                src={avatarUrl}
                alt="Your avatar"
                className="w-full h-full object-cover"
              />
            </div>
            
            {/* Selection Summary */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-medium text-[var(--color-charcoal)]">
                  Your Outfit
                </p>
                {selectedCount > 0 && (
                  <button
                    onClick={clearSelection}
                    className="text-xs text-[var(--color-terracotta)] font-medium"
                  >
                    Clear
                  </button>
                )}
              </div>
              
              {selectedCount === 0 ? (
                <p className="text-xs text-[var(--color-warm-gray)]">
                  Select items below to build your look
                </p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {selectedGarmentsArray.map(garment => (
                    <div 
                      key={garment.id}
                      className="flex items-center gap-1.5 bg-white rounded-lg px-2 py-1.5 shadow-sm"
                    >
                      <img 
                        src={garment.url} 
                        alt={garment.category}
                        className="w-8 h-8 object-contain rounded"
                      />
                      <span className="text-xs text-[var(--color-charcoal)] capitalize">
                        {garment.category}
                      </span>
                      <button
                        onClick={() => handleSelectGarment(garment)}
                        className="w-4 h-4 rounded-full bg-[var(--color-charcoal)]/10 flex items-center justify-center ml-1"
                      >
                        <X className="w-2.5 h-2.5 text-[var(--color-charcoal)]" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="w-full max-w-[260px] aspect-[9/16] rounded-3xl bg-[var(--color-warm-gray)]/10 flex items-center justify-center mx-auto">
            <p className="text-sm text-[var(--color-warm-gray)] text-center px-4">
              Create an avatar to start trying on clothes
            </p>
          </div>
        )}
      </div>

      {/* Garment Categories - 50% */}
      <div className="flex-[5] bg-white rounded-t-3xl shadow-lg overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto px-4 pt-4 pb-2">
          {CATEGORIES.map(category => {
            const categoryGarments = garmentsByCategory[category.id]
            if (categoryGarments.length === 0) return null
            
            return (
              <div key={category.id} className="mb-4">
                {/* Category Header */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm">{category.icon}</span>
                    <span className="text-xs font-medium text-[var(--color-charcoal)]">
                      {category.label}
                    </span>
                  </div>
                  <div className="flex gap-1">
                    <button
                      onClick={() => scrollCarousel(category.id, 'left')}
                      className="w-6 h-6 rounded-full bg-[var(--color-charcoal)]/5 flex items-center justify-center"
                    >
                      <ChevronLeft className="w-3 h-3" />
                    </button>
                    <button
                      onClick={() => scrollCarousel(category.id, 'right')}
                      className="w-6 h-6 rounded-full bg-[var(--color-charcoal)]/5 flex items-center justify-center"
                    >
                      <ChevronRight className="w-3 h-3" />
                    </button>
                  </div>
                </div>
                
                {/* Category Carousel */}
                <div 
                  ref={el => carouselRefs.current[category.id] = el}
                  className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide -mx-4 px-4"
                >
                  {categoryGarments.map(garment => {
                    const selected = isGarmentSelected(garment)
                    return (
                      <button
                        key={garment.id}
                        onClick={() => handleSelectGarment(garment)}
                        className={`relative flex-shrink-0 w-16 h-16 rounded-xl overflow-hidden transition-all ${
                          selected
                            ? 'ring-2 ring-[var(--color-terracotta)] ring-offset-1 scale-105'
                            : 'bg-[var(--color-cream)]'
                        }`}
                      >
                        <img
                          src={garment.url}
                          alt={garment.category}
                          className="w-full h-full object-contain p-0.5"
                        />
                        {selected && (
                          <div className="absolute top-0.5 right-0.5 w-4 h-4 rounded-full bg-[var(--color-terracotta)] flex items-center justify-center">
                            <Check className="w-2.5 h-2.5 text-white" />
                          </div>
                        )}
                      </button>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>

        {/* Try On Button */}
        <div className="px-4 pb-4 pt-2">
          <button
            onClick={handleTryOn}
            disabled={selectedCount === 0 || !avatarUrl || isLoading}
            className="w-full flex items-center justify-center gap-2 py-3 bg-[var(--color-terracotta)] text-white rounded-2xl font-medium text-sm transition-all active:scale-98 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Sparkles className="w-4 h-4" />
            {selectedCount === 0 
              ? 'Select items' 
              : `Try On ${selectedCount} Item${selectedCount > 1 ? 's' : ''}`
            }
          </button>
        </div>
      </div>
    </div>
  )
}
