import { useState, useEffect, useRef, useMemo } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Sparkles, X, Download, Share2, ChevronLeft, ChevronRight, Check } from 'lucide-react'
import { useWardrobe } from '../context/WardrobeContext'
import LoadingOverlay from '../components/LoadingOverlay'
import BottomNav from '../components/BottomNav'
import { getTryOnResultUrl } from '../utils/tryOn'
import ResilientImage from '../components/ResilientImage'

// Category configuration
const CATEGORIES = [
  { id: 'top', label: 'Tops' },
  { id: 'bottom', label: 'Bottoms' },
  { id: 'dress', label: 'Dresses' },
  { id: 'outerwear', label: 'Outerwear' },
]

export default function DressingRoom() {
  const navigate = useNavigate()
  const location = useLocation()
  const { 
    avatarUrl, 
    garments, 
    fetchGarments, 
    tryOnMultiple,
    isLoading, 
    loadingMessage,
    error,
    clearError 
  } = useWardrobe()
  
  // Multi-selection state: { top: garment, bottom: garment, dress: garment, outerwear: garment }
  const [selectedGarments, setSelectedGarments] = useState({})
  const [tryOnResult, setTryOnResult] = useState(null)
  const [showResult, setShowResult] = useState(false)
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
        const timer = setTimeout(() => {
          setSelectedGarments(newSelection)
          hasAppliedPreselection.current = true
        }, 0)
        return () => clearTimeout(timer)
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
      const category = garment.category
      const currentlySelected = prev[category]
      
      if (currentlySelected?.id === garment.id) {
        // Deselect
        const next = { ...prev }
        delete next[category]
        return next
      }
      
      // Dress and top/bottom are mutually exclusive
      if (category === 'dress') {
        const next = { ...prev, dress: garment }
        delete next.top
        delete next.bottom
        return next
      }
      
      if (category === 'top' || category === 'bottom') {
        const next = { ...prev, [category]: garment }
        delete next.dress
        return next
      }
      
      return { ...prev, [category]: garment }
    })
  }

  const isGarmentSelected = (garment) => {
    return selectedGarments[garment.category]?.id === garment.id
  }

  const handleTryOn = async () => {
    if (selectedCount === 0) return
    
    try {
      const result = await tryOnMultiple(selectedGarmentsArray)
      const resultUrl = getTryOnResultUrl(result)
      if (resultUrl) {
        setTryOnResult(resultUrl)
        setShowResult(true)
      }
    } catch (err) {
      console.error('Try-on failed:', err)
    }
  }

  const handleCloseResult = () => {
    setShowResult(false)
    setTryOnResult(null)
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
      <div className="min-h-screen flex flex-col safe-top safe-bottom" style={{ background: 'var(--bg-primary)' }}>
        <div className="flex-1 flex flex-col items-center justify-center page-padding page-container">
          <div
            className="w-24 h-24 rounded-2xl flex items-center justify-center mb-6"
            style={{ background: 'var(--accent-glow)' }}
          >
            <Sparkles className="w-12 h-12" style={{ color: 'var(--accent-light)' }} />
          </div>
          <h2 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
            Create Your Avatar First
          </h2>
          <p className="text-sm text-center mb-6 max-w-xs" style={{ color: 'var(--text-secondary)' }}>
            You need an avatar to try on clothes virtually
          </p>
          <button onClick={() => navigate('/create-avatar')} className="btn-primary">
            Create Avatar
          </button>
        </div>
        <BottomNav />
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col safe-top safe-bottom" style={{ background: 'var(--bg-primary)' }}>
      {isLoading && <LoadingOverlay message={loadingMessage} />}

      <div className="flex-1 flex flex-col page-container">
        {/* Header */}
        <header className="mx-4 mt-4 glass-card-static flex items-center justify-between p-5 flex-shrink-0">
          <div className="w-10" />
          <h1 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
            Dressing Room
          </h1>
          {selectedCount > 0 ? (
            <button
              onClick={clearSelection}
              className="px-3 py-1.5 text-sm font-medium rounded-full"
              style={{ color: 'var(--accent)', background: 'var(--accent-glow)' }}
            >
              Clear
            </button>
          ) : (
            <div className="w-10" />
          )}
        </header>

        {/* Error Toast */}
        {error && (
          <button
            type="button"
            className="mx-4 mt-3 flex-shrink-0 text-left"
            onClick={clearError}
            aria-label="Dismiss error"
          >
            <div className="px-4 py-3 rounded-xl animate-fade-in" style={{ background: 'var(--error)', color: 'white' }}>
              <p className="text-sm">{error}</p>
            </div>
          </button>
        )}

        {/* Responsive Grid Layout */}
        <div className="flex-1 grid grid-cols-1 md:grid-cols-12 gap-5 mx-4 mt-5 mb-4 min-h-0">
          {/* Left Column: Avatar & Outfit Selection */}
          <div className="md:col-span-4 lg:col-span-3 flex flex-col gap-4 flex-shrink-0">
            <div className="glass-card-elevated p-5 flex flex-row md:flex-col gap-4 items-start md:items-stretch">
              {/* Avatar */}
              <div
                className="relative w-28 md:w-full aspect-[3/4] rounded-xl overflow-hidden flex-shrink-0"
                style={{ background: 'var(--glass-bg)', border: '1px solid var(--glass-border)' }}
              >
                <ResilientImage
                  src={avatarUrl}
                  alt="Your avatar"
                  className="w-full h-full object-cover object-top"
                />
              </div>
              
              {/* Selection Summary */}
              <div className="flex-1 min-w-0 flex flex-col">
                <h3 className="text-base font-semibold mb-2 md:text-center" style={{ color: 'var(--text-primary)' }}>
                  Your Outfit
                </h3>
                
                {selectedCount === 0 ? (
                  <div className="space-y-2 md:text-center">
                    <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                      Select items below to build your look.
                    </p>
                    <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                      Choose a dress or a top and bottom. Outerwear works with either.
                    </p>
                  </div>
                ) : (
                  <div>
                    <div className="space-y-2 md:max-h-[220px] lg:max-h-[300px] overflow-y-auto pr-1">
                      {selectedGarmentsArray.map(garment => (
                        <div
                          key={garment.id}
                          className="flex items-center gap-2 rounded-lg p-2"
                          style={{ background: 'var(--glass-bg)', border: '1px solid var(--glass-border)' }}
                        >
                          <ResilientImage
                            src={garment.thumbnail_url || garment.front_url || garment.url}
                            alt={garment.category}
                            className="w-10 h-10 object-contain rounded"
                            style={{ background: 'var(--glass-bg-elevated)' }}
                          />
                          <span className="text-sm capitalize flex-1" style={{ color: 'var(--text-primary)' }}>
                            {garment.category}
                          </span>
                          <button
                            onClick={() => handleSelectGarment(garment)}
                            className="w-8 h-8 rounded-full flex items-center justify-center transition-colors"
                            style={{ background: 'var(--glass-bg-hover)' }}
                            aria-label={`Remove ${garment.category}`}
                          >
                            <X className="w-3.5 h-3.5" style={{ color: 'var(--text-secondary)' }} />
                          </button>
                        </div>
                      ))}
                    </div>
                    <p className="text-xs mt-3 md:text-center" style={{ color: 'var(--text-secondary)' }}>
                      Generation usually takes 20–40 seconds.
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Desktop Try-on Button */}
            <div className="hidden md:block">
              <button
                onClick={handleTryOn}
                disabled={selectedCount === 0 || isLoading}
                className="btn-primary btn-lg w-full"
              >
                <Sparkles className="w-5 h-5" />
                {selectedCount === 0
                  ? 'Choose an item to continue'
                  : `Try On ${selectedCount} Item${selectedCount > 1 ? 's' : ''}`
                }
              </button>
            </div>
          </div>

          {/* Right Column: Garment Categories */}
          <div className="md:col-span-8 lg:col-span-9 flex-1 overflow-y-auto glass-card-elevated min-h-[400px] md:min-h-0">
            <div className="p-5 pb-44 md:pb-5">
              {CATEGORIES.map(category => {
                const categoryGarments = garmentsByCategory[category.id]
                if (categoryGarments.length === 0) return null
                
                return (
                  <div key={category.id} className="mb-6 last:mb-0">
                    {/* Category Header */}
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <span
                          className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
                          style={{ background: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}
                          aria-hidden="true"
                        >
                          {category.label.slice(0, 1)}
                        </span>
                        <h3 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
                          {category.label}
                        </h3>
                        <span
                          className="text-sm min-w-[28px] h-7 flex items-center justify-center rounded-full"
                          style={{ color: 'var(--text-secondary)', background: 'var(--glass-bg)' }}
                        >
                          {categoryGarments.length}
                        </span>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => scrollCarousel(category.id, 'left')}
                          className="w-8 h-8 rounded-full flex items-center justify-center transition-colors"
                          style={{ background: 'var(--glass-bg)' }}
                          aria-label={`Scroll ${category.label} left`}
                        >
                          <ChevronLeft className="w-4 h-4" style={{ color: 'var(--text-secondary)' }} />
                        </button>
                        <button
                          onClick={() => scrollCarousel(category.id, 'right')}
                          className="w-8 h-8 rounded-full flex items-center justify-center transition-colors"
                          style={{ background: 'var(--glass-bg)' }}
                          aria-label={`Scroll ${category.label} right`}
                        >
                          <ChevronRight className="w-4 h-4" style={{ color: 'var(--text-secondary)' }} />
                        </button>
                      </div>
                    </div>
                    
                    {/* Category Carousel */}
                    <div 
                      ref={el => carouselRefs.current[category.id] = el}
                      className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide snap-x"
                    >
                      {categoryGarments.map(garment => {
                        const selected = isGarmentSelected(garment)
                        return (
                          <button
                            key={garment.id}
                            onClick={() => handleSelectGarment(garment)}
                            className="relative flex-shrink-0 w-22 h-22 md:w-28 md:h-28 rounded-xl overflow-hidden transition-all snap-start"
                            style={{
                              width: '88px',
                              height: '88px',
                              background: selected ? 'var(--accent-glow)' : 'var(--glass-bg)',
                              border: selected ? '2px solid var(--accent)' : '1px solid var(--glass-border)',
                              boxShadow: selected ? '0 0 16px var(--accent-glow)' : 'none',
                              transform: selected ? 'scale(1.05)' : 'scale(1)',
                            }}
                          >
                            <ResilientImage
                              src={garment.thumbnail_url || garment.front_url || garment.url}
                              alt={garment.category}
                              className="w-full h-full object-contain p-1.5"
                            />
                            {selected && (
                              <div
                                className="absolute top-1 right-1 w-5 h-5 rounded-full flex items-center justify-center"
                                style={{ background: 'var(--accent)' }}
                              >
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
                  <div
                    className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4"
                    style={{ background: 'var(--glass-bg)' }}
                  >
                    <Sparkles className="w-8 h-8" style={{ color: 'var(--text-tertiary)' }} />
                  </div>
                  <p className="text-base mb-4" style={{ color: 'var(--text-secondary)' }}>
                    No clothes in your wardrobe yet
                  </p>
                  <button onClick={() => navigate('/capture')} className="btn-primary">
                    Add Clothes
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Floating Try On Button (mobile only) */}
      {selectedCount > 0 && (
        <div className="fixed bottom-24 md:hidden left-0 right-0 px-4 pointer-events-none z-30">
          <div className="max-w-lg mx-auto pointer-events-auto">
            <button
              onClick={handleTryOn}
              disabled={isLoading}
              className="btn-primary btn-lg w-full shadow-lg"
            >
              <Sparkles className="w-5 h-5" />
              {`Try On ${selectedCount} Item${selectedCount > 1 ? 's' : ''}`}
            </button>
          </div>
        </div>
      )}

      {/* Result Modal */}
      {showResult && tryOnResult && (
        <div className="fixed inset-0 z-50 flex flex-col safe-top safe-bottom animate-fade-in" style={{ background: 'rgba(0,0,0,0.95)' }}>
          <div className="flex-1 flex flex-col page-container w-full">
            <header className="flex items-center justify-between page-padding py-4 flex-shrink-0">
              <button
                onClick={handleCloseResult}
                className="w-10 h-10 rounded-full flex items-center justify-center"
                style={{ background: 'var(--glass-bg)' }}
              >
                <X className="w-5 h-5" style={{ color: 'var(--text-primary)' }} />
              </button>
              <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Your Look</h2>
              <div className="w-10" />
            </header>

            <div className="flex-1 flex items-center justify-center page-padding overflow-auto">
              <div className="w-full max-w-sm rounded-2xl overflow-hidden" style={{ boxShadow: '0 0 40px rgba(224, 120, 80, 0.2)' }}>
                <ResilientImage
                  src={tryOnResult}
                  alt="Try-on result"
                  className="w-full h-auto object-contain"
                  fallbackClassName="w-full min-h-64"
                />
              </div>
            </div>

            <div className="page-padding pb-6 flex-shrink-0">
              <p className="text-center text-sm mb-3 text-white/80">
                Saved automatically to Looks
              </p>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={handleDownload}
                  className="flex flex-col items-center justify-center gap-1.5 py-3 rounded-xl font-medium text-sm"
                  style={{ background: 'var(--glass-bg)', color: 'var(--text-primary)', border: '1px solid var(--glass-border)' }}
                >
                  <Download className="w-5 h-5" />
                  <span>Download</span>
                </button>
                <button
                  onClick={handleShare}
                  className="flex flex-col items-center justify-center gap-1.5 py-3 rounded-xl font-medium text-sm"
                  style={{ background: 'var(--glass-bg)', color: 'var(--text-primary)', border: '1px solid var(--glass-border)' }}
                >
                  <Share2 className="w-5 h-5" />
                  <span>Share</span>
                </button>
              </div>
              
              <button onClick={handleCloseResult} className="btn-primary btn-lg w-full mt-4">
                Try Another Look
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Bottom Navigation */}
      {!showResult && <BottomNav />}
    </div>
  )
}
