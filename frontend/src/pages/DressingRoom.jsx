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
      const garmentIds = selectedGarmentsArray.map(g => g.id)
      const resultUrl = await tryOnMultiple(garmentIds)
      if (resultUrl) {
        setTryOnResult(resultUrl)
        setShowResult(true)
        setSaveSuccess(false)
      }
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
      const garmentIds = selectedGarmentsArray.map(g => g.id)
      await saveLook(tryOnResult, garmentIds)
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
          <div className="mx-4 mt-3 flex-shrink-0" onClick={clearError}>
            <div className="px-4 py-3 rounded-xl animate-fade-in" style={{ background: 'var(--error)', color: 'white' }}>
              <p className="text-sm">{error}</p>
            </div>
          </div>
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
                <img
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
                  <p className="text-sm md:text-center" style={{ color: 'var(--text-tertiary)' }}>
                    Select items below to build your look
                  </p>
                ) : (
                  <div className="space-y-2 md:max-h-[220px] lg:max-h-[300px] overflow-y-auto pr-1">
                    {selectedGarmentsArray.map(garment => (
                      <div 
                        key={garment.id}
                        className="flex items-center gap-2 rounded-lg p-2"
                        style={{ background: 'var(--glass-bg)', border: '1px solid var(--glass-border)' }}
                      >
                        <img 
                          src={garment.front_url || garment.url} 
                          alt={garment.category}
                          className="w-10 h-10 object-contain rounded"
                          style={{ background: 'var(--glass-bg-elevated)' }}
                        />
                        <span className="text-sm capitalize flex-1" style={{ color: 'var(--text-primary)' }}>
                          {garment.category}
                        </span>
                        <button
                          onClick={() => handleSelectGarment(garment)}
                          className="w-6 h-6 rounded-full flex items-center justify-center transition-colors"
                          style={{ background: 'var(--glass-bg-hover)' }}
                        >
                          <X className="w-3 h-3" style={{ color: 'var(--text-secondary)' }} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Desktop Try-on Button */}
            <button
              onClick={handleTryOn}
              disabled={selectedCount === 0 || isLoading}
              className="hidden md:flex btn-primary btn-lg w-full"
            >
              <Sparkles className="w-5 h-5" />
              {selectedCount === 0 
                ? 'Select items to try on' 
                : `Try On ${selectedCount} Item${selectedCount > 1 ? 's' : ''}`
              }
            </button>
          </div>

          {/* Right Column: Garment Categories */}
          <div className="md:col-span-8 lg:col-span-9 flex-1 overflow-y-auto glass-card-elevated min-h-[400px] md:min-h-0">
            <div className="p-5 nav-bottom-spacing md:pb-5">
              {CATEGORIES.map(category => {
                const categoryGarments = garmentsByCategory[category.id]
                if (categoryGarments.length === 0) return null
                
                return (
                  <div key={category.id} className="mb-6 last:mb-0">
                    {/* Category Header */}
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <span className="text-xl">{category.icon}</span>
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
                        >
                          <ChevronLeft className="w-4 h-4" style={{ color: 'var(--text-secondary)' }} />
                        </button>
                        <button
                          onClick={() => scrollCarousel(category.id, 'right')}
                          className="w-8 h-8 rounded-full flex items-center justify-center transition-colors"
                          style={{ background: 'var(--glass-bg)' }}
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
                            <img
                              src={garment.front_url || garment.url}
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
      <div className="fixed bottom-24 md:hidden left-0 right-0 page-padding pointer-events-none z-30">
        <div className="page-container pointer-events-auto">
          <button
            onClick={handleTryOn}
            disabled={selectedCount === 0 || isLoading}
            className="btn-primary btn-lg w-full"
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
                  className="flex flex-col items-center justify-center gap-1.5 py-3 rounded-xl font-medium text-sm transition-all"
                  style={{
                    background: saveSuccess ? 'rgba(74, 222, 128, 0.15)' : 'var(--glass-bg)',
                    color: saveSuccess ? '#4ade80' : 'var(--text-primary)',
                    border: '1px solid var(--glass-border)',
                  }}
                >
                  {saveSuccess ? <Check className="w-5 h-5" /> : <Save className="w-5 h-5" />}
                  <span>{saveSuccess ? 'Saved!' : 'Save'}</span>
                </button>
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
