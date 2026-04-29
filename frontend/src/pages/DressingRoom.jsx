import { useState, useEffect, useRef, useMemo } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Sparkles, X, Download, Share2, ChevronLeft, ChevronRight, Check, Save } from 'lucide-react'
import { useWardrobe } from '../context/WardrobeContext'
import LoadingOverlay from '../components/LoadingOverlay'
import BottomNav from '../components/BottomNav'

// Category configuration
const CATEGORIES = [
  { id: 'top', label: 'Tops', icon: '👕' },
  { id: 'bottom', label: 'Bottoms', icon: '👖' },
  { id: 'dress', label: 'Dresses', icon: '👗' },
  { id: 'outerwear', label: 'Outerwear', icon: '🧥' },
]

export default function DressingRoom() {
  const navigate = useNavigate()
  const location = useLocation()
  const { 
    avatarUrl, 
    garments, 
    fetchGarments, 
    tryOnMultiple,
    saveLook,
    isLoading, 
    loadingMessage,
    error,
    clearError 
  } = useWardrobe()
  
  // Multi-selection state: { top: garment, bottom: garment, dress: garment, outerwear: garment }
  const [selectedGarments, setSelectedGarments] = useState({})
  const [tryOnResult, setTryOnResult] = useState(null)
  const [showResult, setShowResult] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const carouselRefs = useRef({})

  useEffect(() => {
    fetchGarments()
  }, [fetchGarments])

  // Preselect garments if coming from Daily Looks with preselected IDs (only once)
  const hasAppliedPreselection = useRef(false)
  useEffect(() => {
    const preselectedIds = location.state?.preselectedGarmentIds
    if (preselectedIds && preselectedIds.length > 0 && garments.length > 0 && !hasAppliedPreselection.current) {
      const newSelection = {}
      preselectedIds.forEach(id => {
        const garment = garments.find(g => g.id === id)
        if (garment) {
          newSelection[garment.category] = garment
        }
      })
      if (Object.keys(newSelection).length > 0) {
        setSelectedGarments(newSelection)
        hasAppliedPreselection.current = true
      }
    }
  }, [location.state, garments])

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
    setSelectedGarments(prev => {
      const newSelection = { ...prev }
      
      // If already selected, deselect it
      if (prev[garment.category]?.id === garment.id) {
        delete newSelection[garment.category]
        return newSelection
      }
      
      // Handle dress vs top/bottom mutual exclusivity
      if (garment.category === 'dress') {
        // Selecting a dress removes top and bottom
        delete newSelection.top
        delete newSelection.bottom
        newSelection.dress = garment
      } else if (garment.category === 'top' || garment.category === 'bottom') {
        // Selecting top or bottom removes dress
        delete newSelection.dress
        newSelection[garment.category] = garment
      } else {
        // Outerwear can be combined with anything
        newSelection[garment.category] = garment
      }
      
      return newSelection
    })
  }

  const isGarmentSelected = (garment) => {
    return selectedGarments[garment.category]?.id === garment.id
  }

  const handleTryOn = async () => {
    if (selectedCount === 0 || !avatarUrl) return

    try {
      const result = await tryOnMultiple(selectedGarmentsArray)
      setTryOnResult(result.result_url)
      setShowResult(true)
      setSaveSuccess(false)
    } catch (err) {
      console.error('Try-on failed:', err)
    }
  }

  const handleCloseResult = () => {
    setShowResult(false)
    setTryOnResult(null)
    setSaveSuccess(false)
  }

  const handleSaveLook = async () => {
    if (!tryOnResult || isSaving) return
    
    setIsSaving(true)
    try {
      await saveLook(tryOnResult)
      setSaveSuccess(true)
    } catch (err) {
      console.error('Save failed:', err)
    } finally {
      setIsSaving(false)
    }
  }

  const handleDownload = async () => {
    if (!tryOnResult) return
    
    try {
      const a = document.createElement('a')
      a.href = tryOnResult
      a.download = `tryon-${Date.now()}.png`
      a.target = '_blank'
      a.rel = 'noopener noreferrer'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    } catch (err) {
      console.error('Download failed:', err)
      window.open(tryOnResult, '_blank')
    }
  }

  const handleShare = async () => {
    if (!tryOnResult) return
    
    try {
      if (navigator.share) {
        await navigator.share({
          title: 'My Virtual Try-On',
          text: 'Check out my virtual outfit!',
          url: tryOnResult,
        })
      } else {
        await navigator.clipboard.writeText(tryOnResult)
        alert('Link copied to clipboard!')
      }
    } catch (err) {
      console.error('Share failed:', err)
      try {
        await navigator.clipboard.writeText(tryOnResult)
        alert('Link copied to clipboard!')
      } catch {
        window.open(tryOnResult, '_blank')
      }
    }
  }

  const scrollCarousel = (categoryId, direction) => {
    const ref = carouselRefs.current[categoryId]
    if (!ref) return
    const scrollAmount = direction === 'left' ? -150 : 150
    ref.scrollBy({ left: scrollAmount, behavior: 'smooth' })
  }

  const clearSelection = () => {
    setSelectedGarments({})
  }

  if (!avatarUrl) {
    return (
      <div className="min-h-screen flex flex-col bg-[var(--color-cream)] safe-top safe-bottom">
        <div className="flex-1 flex flex-col items-center justify-center page-padding page-container">
          <div className="w-24 h-24 rounded-full bg-[var(--color-terracotta)]/10 flex items-center justify-center mb-6">
            <Sparkles className="w-12 h-12 text-[var(--color-terracotta)]" />
          </div>
          <h2 className="text-lg font-semibold text-[var(--color-charcoal)] mb-2">
            Create Your Avatar First
          </h2>
          <p className="text-sm text-[var(--color-warm-gray)] text-center mb-6 max-w-xs">
            You need an avatar to try on clothes virtually
          </p>
          <button
            onClick={() => navigate('/create-avatar')}
            className="px-6 py-3 bg-[var(--color-terracotta)] text-white rounded-xl font-medium text-sm"
          >
            Create Avatar
          </button>
        </div>
        <BottomNav />
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col bg-[var(--color-cream)] safe-top safe-bottom">
      {isLoading && <LoadingOverlay message={loadingMessage} />}

      <div className="flex-1 flex flex-col page-container">
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
          <div className="w-10" />
          
          <h1 className="text-lg font-bold text-[var(--color-charcoal)]">
            Dressing Room
          </h1>
          
          {selectedCount > 0 ? (
            <button
              onClick={clearSelection}
              className="px-3 py-1.5 text-sm text-[var(--color-terracotta)] font-medium bg-[var(--color-terracotta)]/10 rounded-full"
            >
              Clear
            </button>
          ) : (
            <div className="w-10" />
          )}
        </header>

        {/* Error Toast */}
        {error && (
          <div 
            className="page-padding mb-3 flex-shrink-0"
            onClick={clearError}
          >
            <div className="bg-[var(--color-terracotta)] text-white px-4 py-3 rounded-xl animate-fade-in">
              <p className="text-sm">{error}</p>
            </div>
          </div>
        )}

        {/* Avatar Display with Selection Summary */}
        <div className="mx-4 mt-6 mb-6 flex-shrink-0">
          <div className="flex gap-4 items-start bg-white rounded-3xl p-5 shadow-sm">
            {/* Avatar */}
            <div className="relative w-28 aspect-[3/4] rounded-xl overflow-hidden bg-gradient-to-br from-gray-50 to-gray-100 flex-shrink-0">
              <img
                src={avatarUrl}
                alt="Your avatar"
                className="w-full h-full object-cover"
              />
            </div>
            
            {/* Selection Summary */}
            <div className="flex-1 min-w-0">
              <h3 className="text-base font-semibold text-[var(--color-charcoal)] mb-1">
                Your Outfit
              </h3>
              
              {selectedCount === 0 ? (
                <p className="text-sm text-[var(--color-warm-gray)]">
                  Select items below to build your look
                </p>
              ) : (
                <div className="space-y-2">
                  {selectedGarmentsArray.map(garment => (
                    <div 
                      key={garment.id}
                      className="flex items-center gap-2 bg-[var(--color-cream)] rounded-lg p-2"
                    >
                      <img 
                        src={garment.front_url || garment.url} 
                        alt={garment.category}
                        className="w-10 h-10 object-contain rounded bg-white"
                      />
                      <span className="text-sm text-[var(--color-charcoal)] capitalize flex-1">
                        {garment.category}
                      </span>
                      <button
                        onClick={() => handleSelectGarment(garment)}
                        className="w-6 h-6 rounded-full bg-[var(--color-charcoal)]/10 flex items-center justify-center hover:bg-[var(--color-charcoal)]/20"
                      >
                        <X className="w-3 h-3 text-[var(--color-charcoal)]" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Garment Categories - Scrollable */}
        <div className="mx-4 flex-1 overflow-y-auto bg-white rounded-3xl shadow-sm mb-4">
          <div className="p-6 nav-bottom-spacing">
            {CATEGORIES.map(category => {
              const categoryGarments = garmentsByCategory[category.id]
              if (categoryGarments.length === 0) return null
              
              return (
                <div key={category.id} className="mb-6">
                  {/* Category Header */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <span className="text-xl">{category.icon}</span>
                      <span className="text-base font-semibold text-[var(--color-charcoal)]">
                        {category.label}
                      </span>
                      <span className="text-sm text-[var(--color-warm-gray)] bg-[var(--color-warm-gray)]/10 min-w-[28px] h-7 flex items-center justify-center rounded-full">
                        {categoryGarments.length}
                      </span>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => scrollCarousel(category.id, 'left')}
                        className="w-8 h-8 rounded-full bg-[var(--color-charcoal)]/5 flex items-center justify-center hover:bg-[var(--color-charcoal)]/10 transition-colors"
                      >
                        <ChevronLeft className="w-4 h-4 text-[var(--color-charcoal)]" />
                      </button>
                      <button
                        onClick={() => scrollCarousel(category.id, 'right')}
                        className="w-8 h-8 rounded-full bg-[var(--color-charcoal)]/5 flex items-center justify-center hover:bg-[var(--color-charcoal)]/10 transition-colors"
                      >
                        <ChevronRight className="w-4 h-4 text-[var(--color-charcoal)]" />
                      </button>
                    </div>
                  </div>
                  
                  {/* Category Carousel */}
                  <div 
                    ref={el => carouselRefs.current[category.id] = el}
                    className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide snap-x -mx-4 px-4 sm:-mx-6 sm:px-6 md:-mx-8 md:px-8"
                  >
                    {categoryGarments.map(garment => {
                      const selected = isGarmentSelected(garment)
                      return (
                        <button
                          key={garment.id}
                          onClick={() => handleSelectGarment(garment)}
                          className={`relative flex-shrink-0 w-20 h-20 rounded-xl overflow-hidden transition-all snap-start bg-[var(--color-cream)] ${
                            selected
                              ? 'ring-2 ring-[var(--color-terracotta)] ring-offset-2 scale-105'
                              : 'hover:scale-102 hover:shadow-md'
                          }`}
                        >
                          <img
                            src={garment.front_url || garment.url}
                            alt={garment.category}
                            className="w-full h-full object-contain p-1.5"
                          />
                          {selected && (
                            <div className="absolute top-1 right-1 w-5 h-5 rounded-full bg-[var(--color-terracotta)] flex items-center justify-center shadow-sm">
                              <Check className="w-3 h-3 text-white" />
                            </div>
                          )}
                        </button>
                      )
                    })}
                  </div>
                </div>
              )
            })}
            
            {/* Empty State */}
            {garments.length === 0 && (
              <div className="text-center py-12">
                <div className="w-16 h-16 rounded-full bg-[var(--color-warm-gray)]/10 flex items-center justify-center mx-auto mb-4">
                  <Sparkles className="w-8 h-8 text-[var(--color-warm-gray)]" />
                </div>
                <p className="text-base text-[var(--color-warm-gray)] mb-4">
                  No clothes in your wardrobe yet
                </p>
                <button
                  onClick={() => navigate('/capture')}
                  className="px-5 py-2.5 bg-[var(--color-terracotta)] text-white rounded-xl text-sm font-medium"
                >
                  Add Clothes
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Floating Try On Button */}
      <div className="fixed bottom-24 left-0 right-0 page-padding pointer-events-none z-30">
        <div className="page-container pointer-events-auto">
          <button
            onClick={handleTryOn}
            disabled={selectedCount === 0 || isLoading}
            className="w-full flex items-center justify-center gap-2 py-4 bg-[var(--color-terracotta)] text-white rounded-2xl font-semibold text-base transition-all active:scale-98 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl"
          >
            <Sparkles className="w-5 h-5" />
            {selectedCount === 0 
              ? 'Select items to try on' 
              : `Try On ${selectedCount} Item${selectedCount > 1 ? 's' : ''}`
            }
          </button>
        </div>
      </div>

      {/* Result Modal */}
      {showResult && tryOnResult && (
        <div className="fixed inset-0 z-50 bg-black/95 flex flex-col safe-top safe-bottom animate-fade-in">
          <div className="flex-1 flex flex-col page-container w-full">
            <header className="flex items-center justify-between page-padding py-4 flex-shrink-0">
              <button
                onClick={handleCloseResult}
                className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center hover:bg-white/20"
              >
                <X className="w-5 h-5 text-white" />
              </button>
              
              <h2 className="text-lg font-bold text-white">Your Look</h2>
              
              <div className="w-10" />
            </header>

            <div className="flex-1 flex items-center justify-center page-padding overflow-auto">
              <div className="w-full max-w-sm rounded-2xl overflow-hidden shadow-2xl bg-white">
                <img
                  src={tryOnResult}
                  alt="Try-on result"
                  className="w-full h-auto object-contain"
                />
              </div>
            </div>

            <div className="page-padding pb-6 flex-shrink-0">
              <div className="grid grid-cols-3 gap-3">
                <button
                  onClick={handleSaveLook}
                  disabled={isSaving || saveSuccess}
                  className={`flex flex-col items-center justify-center gap-1.5 py-3 rounded-xl font-medium text-sm transition-all ${
                    saveSuccess
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-white/10 text-white hover:bg-white/20'
                  }`}
                >
                  {saveSuccess ? (
                    <Check className="w-5 h-5" />
                  ) : (
                    <Save className="w-5 h-5" />
                  )}
                  <span>{saveSuccess ? 'Saved!' : 'Save'}</span>
                </button>
                <button
                  onClick={handleDownload}
                  className="flex flex-col items-center justify-center gap-1.5 py-3 bg-white/10 text-white rounded-xl font-medium text-sm hover:bg-white/20"
                >
                  <Download className="w-5 h-5" />
                  <span>Download</span>
                </button>
                <button
                  onClick={handleShare}
                  className="flex flex-col items-center justify-center gap-1.5 py-3 bg-white/10 text-white rounded-xl font-medium text-sm hover:bg-white/20"
                >
                  <Share2 className="w-5 h-5" />
                  <span>Share</span>
                </button>
              </div>
              
              <button
                onClick={handleCloseResult}
                className="w-full mt-4 py-4 bg-[var(--color-terracotta)] text-white rounded-2xl font-semibold text-base"
              >
                Try Another Look
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Bottom Navigation - only show when not in result modal */}
      {!showResult && <BottomNav />}
    </div>
  )
}
