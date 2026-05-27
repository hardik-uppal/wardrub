import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Sparkles, RefreshCw, Shirt, User, Heart, Bookmark, Eye, CheckCircle2,
  ChevronRight, Wand2, ArrowRight, CloudRain, Sun, Snowflake, Cloud, 
  HelpCircle, ChevronLeft
} from 'lucide-react'
import { useWardrobe } from '../context/WardrobeContext'
import { useAuth } from '../context/AuthContext'
import LoadingOverlay from '../components/LoadingOverlay'
import BottomNav from '../components/BottomNav'

const API_URL = import.meta.env.VITE_API_URL || ''

// Simple weather mapping for visual headers
const weatherThemes = {
  clear: { icon: Sun, text: 'Sunny' },
  cloudy: { icon: Cloud, text: 'Cloudy' },
  rainy: { icon: CloudRain, text: 'Rainy' },
  snowy: { icon: Snowflake, text: 'Chilly' },
  default: { icon: Sun, text: 'Mild' }
}

export default function MagazineFeed() {
  const navigate = useNavigate()
  const { avatarUrl, garments, fetchGarments } = useWardrobe()
  const { getIdToken } = useAuth()

  const [feedData, setFeedData] = useState(null)
  const [isOnboarding, setIsOnboarding] = useState(false)
  const [onboardingCount, setOnboardingCount] = useState(0)
  const [isMockMode, setIsMockMode] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [loadingMessage, setLoadingMessage] = useState('Opening Today\'s Issue...')
  const [error, setError] = useState(null)
  const [generatingFeed, setGeneratingFeed] = useState(false)
  
  // Track try-on operations by look card ID
  const [tryOnLoading, setTryOnLoading] = useState({})
  const [tryOnImages, setTryOnImages] = useState({}) // key: lookId, value: tryonUrl
  const [detailLook, setDetailLook] = useState(null) // Active look modal

  // Helper to make authenticated fetch requests
  const authFetch = useCallback(async (url, options = {}) => {
    const token = await getIdToken()
    if (!token) throw new Error('Not authenticated')
    
    const headers = {
      ...options.headers,
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
    return fetch(url, { ...options, headers })
  }, [getIdToken])

  const fetchMagazineFeed = useCallback(async (force = false, useMock = false) => {
    const activeMock = useMock || isMockMode
    if (force) {
      setGeneratingFeed(true)
      setLoadingMessage('Curating today\'s edits...')
    } else {
      setIsLoading(true)
    }
    setError(null)
    
    try {
      let url = force 
        ? `${API_URL}/api/magazine-feed/generate` 
        : `${API_URL}/api/magazine-feed`
      
      const queryParams = []
      if (activeMock) {
        queryParams.push('mock=true')
      }
      if (queryParams.length > 0) {
        url += '?' + queryParams.join('&')
      }
      
      const response = await authFetch(url, { method: force ? 'POST' : 'GET' })
      const data = await response.json()
      
      if (data.status === 'onboarding') {
        setIsOnboarding(true)
        setOnboardingCount(data.count || 0)
      } else if (data.status === 'success' && data.feed) {
        setIsOnboarding(false)
        setFeedData(data.feed)
        if (activeMock) {
          setIsMockMode(true)
        }
        
        // Restore pre-rendered try-ons if they exist
        const restoredImages = {}
        const extractTryon = (look) => {
          if (look?.tryon_image_url) {
            restoredImages[look.id] = look.tryon_image_url
          }
        }
        extractTryon(data.feed.cover_look)
        extractTryon(data.feed.underused_edit)
        data.feed.daily_fits?.forEach(extractTryon)
        data.feed.one_item_three_ways?.forEach(extractTryon)
        setTryOnImages(restoredImages)
      } else {
        setError('failed')
      }
    } catch (err) {
      console.error('Failed to load magazine feed:', err)
      setError('failed')
    } finally {
      setIsLoading(false)
      setGeneratingFeed(false)
    }
  }, [authFetch, isMockMode])

  useEffect(() => {
    fetchMagazineFeed()
    fetchGarments()
  }, [fetchMagazineFeed, fetchGarments])

  // Map garment ID to full object
  const getGarment = (id) => garments.find(g => g.id === id)

  // Map category to a cleaner representation
  const cleanCategory = (cat) => {
    if (!cat) return ''
    return cat.charAt(0).toUpperCase() + cat.slice(1).toLowerCase()
  }

  // Handle like/dislike/save feedback actions
  const handleFeedback = async (lookId, action) => {
    try {
      // Optimistic update for UI feel
      if (action === 'dislike') {
        // Hide or dim card
      }
      
      await authFetch(`${API_URL}/api/magazine-feed/feedback`, {
        method: 'POST',
        body: JSON.stringify({ look_id: lookId, action })
      })
      
      // Let user know it succeeded
      // We can show a subtle micro-animation or message later
    } catch (err) {
      console.error(`Failed to register ${action} feedback:`, err)
    }
  }

  // On-demand tryon generation
  const handleRunTryOn = async (look) => {
    if (!avatarUrl) {
      navigate('/create-avatar')
      return
    }

    const lookId = look.id
    setTryOnLoading(prev => ({ ...prev, [lookId]: true }))
    
    try {
      const garmentsToTry = look.garment_ids
        .map(id => getGarment(id))
        .filter(Boolean)
        .map(g => ({
          url: g.front_url || g.url,
          category: g.category
        }))

      if (garmentsToTry.length === 0) {
        throw new Error('No valid garments found in look')
      }

      const response = await authFetch(`${API_URL}/api/try-on-multiple`, {
        method: 'POST',
        body: JSON.stringify({
          avatar_url: avatarUrl,
          garments: garmentsToTry
        })
      })

      const data = await response.json()
      if (data.status === 'success' && data.result_url) {
        setTryOnImages(prev => ({ ...prev, [lookId]: data.result_url }))
        
        // Update detailModal if open
        if (detailLook && detailLook.id === lookId) {
          setDetailLook(prev => ({ ...prev, tryon_image_url: data.result_url }))
        }
      }
    } catch (err) {
      console.error('Try-on failed:', err)
    } finally {
      setTryOnLoading(prev => ({ ...prev, [lookId]: false }))
    }
  }

  // Onboarding Page
  if (isOnboarding && !isLoading) {
    return (
      <div className="min-h-screen flex flex-col justify-between" style={{ background: 'var(--bg-primary)' }}>
        <div className="page-container p-6 flex flex-col justify-center flex-1 max-w-lg mx-auto">
          
          {/* Logo / Header */}
          <div className="text-center mb-10">
            <span 
              className="text-[42px] font-bold tracking-tight block leading-none"
              style={{ fontFamily: "'Playfair Display', Georgia, serif", color: 'var(--text-primary)' }}
            >
              The Looker
            </span>
            <span 
              className="text-[10px] tracking-[0.25em] font-semibold text-center uppercase block mt-2"
              style={{ fontFamily: "'Syne', sans-serif", color: 'var(--accent)' }}
            >
              Your Closet, Curated.
            </span>
          </div>

          {/* Premium Glass card onboarding */}
          <div className="glass-card-elevated p-8 border border-[var(--glass-border-hover)] space-y-6">
            <h2 
              className="text-xl font-bold tracking-tight text-center" 
              style={{ color: 'var(--text-primary)' }}
            >
              Assembling Your Lookbook
            </h2>
            
            <p className="text-sm leading-relaxed text-center" style={{ color: 'var(--text-secondary)' }}>
              The Looker compiles outfit recommendations, daily cover fits, and custom styling tutorials tailored to your garments. We need a few pieces to get started.
            </p>

            {/* Checklist */}
            <div className="space-y-3 pt-2">
              <div className="flex items-center gap-3 p-4 rounded-xl glass-card-static">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Create style profile</span>
              </div>
              
              <div className="flex items-center gap-3 p-4 rounded-xl glass-card-static relative overflow-hidden">
                <div 
                  className="absolute left-0 top-0 bottom-0 opacity-10 transition-all duration-500" 
                  style={{ background: 'var(--accent)', width: `${(onboardingCount / 5) * 100}%` }}
                />
                <div className="w-5 h-5 rounded-full border-2 flex items-center justify-center border-amber-500 text-xs font-bold text-amber-500">
                  {onboardingCount}
                </div>
                <div className="flex-1 flex justify-between items-center">
                  <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Upload 5 clothing garments</span>
                  <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{onboardingCount}/5 added</span>
                </div>
              </div>
            </div>

            {/* Progress bar */}
            <div className="w-full bg-[var(--glass-bg)] h-1.5 rounded-full overflow-hidden">
              <div 
                className="h-full rounded-full transition-all duration-500"
                style={{ background: 'var(--accent)', width: `${(onboardingCount / 5) * 100}%` }}
              />
            </div>

            <div className="flex flex-col gap-3 mt-4">
              <button 
                onClick={() => navigate('/capture')}
                className="btn-primary btn-lg w-full flex items-center justify-center gap-2"
              >
                <Shirt className="w-4 h-4" />
                <span>Capture Clothes</span>
              </button>
              
              <button 
                onClick={() => fetchMagazineFeed(false, true)}
                className="btn-secondary btn-lg w-full flex items-center justify-center gap-2"
              >
                <Sparkles className="w-4 h-4 text-[var(--accent)]" />
                <span>Preview with Demo Closet</span>
              </button>
            </div>
          </div>
        </div>
        <BottomNav />
      </div>
    )
  }

  // Load state
  if (isLoading && !feedData) {
    return (
      <div 
        className="min-h-screen flex flex-col justify-center items-center p-6 text-center"
        style={{ background: 'var(--bg-primary)' }}
      >
        <div className="space-y-4 animate-pulse-soft">
          <span 
            className="text-4xl font-bold tracking-tight"
            style={{ fontFamily: "'Playfair Display', Georgia, serif", color: 'var(--text-primary)' }}
          >
            The Looker
          </span>
          <div className="flex items-center justify-center gap-2 mt-2">
            <RefreshCw className="w-4 h-4 animate-spin" style={{ color: 'var(--accent)' }} />
            <p className="text-xs font-semibold uppercase tracking-widest text-[var(--text-secondary)]">{loadingMessage}</p>
          </div>
        </div>
      </div>
    )
  }

  // Error page
  if (error && !feedData) {
    return (
      <div className="min-h-screen flex flex-col justify-between" style={{ background: 'var(--bg-primary)' }}>
        <div className="page-container p-6 flex flex-col items-center justify-center flex-1 max-w-sm mx-auto text-center space-y-4">
          <div className="w-16 h-16 rounded-full flex items-center justify-center" style={{ background: 'rgba(239, 68, 68, 0.1)' }}>
            <Shirt className="w-8 h-8 text-red-400 animate-bounce" />
          </div>
          <h3 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Could not open today's issue</h3>
          <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            There was a connection issue loading the editorial feed.
          </p>
          <button onClick={() => fetchMagazineFeed()} className="btn-primary w-full">
            Retry Loading
          </button>
        </div>
        <BottomNav />
      </div>
    )
  }

  const today = new Date()
  const dateHeader = today.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' }).toUpperCase()
  const coverLook = feedData?.cover_look
  const dailyFits = feedData?.daily_fits || []
  const oneItemFits = feedData?.one_item_three_ways || []
  const underusedEdit = feedData?.underused_edit
  const weatherContextStr = coverLook?.weather_context || 'Mild'

  // Component to render garment collage
  const GarmentCollage = ({ garmentIds, className = "" }) => {
    const list = garmentIds.map(id => getGarment(id)).filter(Boolean)
    
    if (list.length === 0) {
      return (
        <div className={`flex items-center justify-center border border-[var(--glass-border)] bg-[var(--glass-bg)] rounded-2xl ${className}`}>
          <Shirt className="w-8 h-8 opacity-20 text-[var(--text-tertiary)]" />
        </div>
      )
    }

    if (list.length === 1) {
      return (
        <div className={`relative flex items-center justify-center border border-[var(--glass-border)] bg-[var(--glass-bg)] rounded-2xl p-4 overflow-hidden ${className}`}>
          <img src={list[0].front_url || list[0].url} alt="Garment" className="w-full h-full object-contain hover:scale-105 transition-transform" />
        </div>
      )
    }

    return (
      <div className={`grid grid-cols-2 gap-2 border border-[var(--glass-border)] bg-[var(--glass-bg)] rounded-2xl p-3 overflow-hidden ${className}`}>
        {list.slice(0, 4).map((g, index) => (
          <div key={g.id} className="relative aspect-square flex items-center justify-center bg-[var(--bg-primary)] border border-[var(--glass-border)] rounded-xl p-1 overflow-hidden">
            <img src={g.front_url || g.url} alt="Garment" className="w-full h-full object-contain hover:scale-105 transition-transform" />
            <span className="absolute bottom-1 left-1.5 text-[8px] uppercase tracking-wider font-semibold text-[var(--text-tertiary)] bg-[var(--bg-secondary)] px-1 rounded-sm">
              {g.category}
            </span>
          </div>
        ))}
      </div>
    )
  }

  // Component to render outfit card
  const LookCardView = ({ look, sectionName }) => {
    if (!look) return null
    const hasTryon = !!tryOnImages[look.id]
    const currentImageUrl = tryOnImages[look.id]
    const isGenerating = !!tryOnLoading[look.id]

    return (
      <div className="glass-card-static border border-[var(--glass-border)] hover:border-[var(--glass-border-hover)] transition-all overflow-hidden flex flex-col">
        
        {/* Main Imagery */}
        <div className="relative aspect-[3/4] overflow-hidden bg-black/5 flex-shrink-0 group">
          {hasTryon ? (
            <img 
              src={currentImageUrl} 
              alt={look.title} 
              className="w-full h-full object-contain cursor-pointer transition-transform duration-500 group-hover:scale-102"
              onClick={() => setDetailLook({ ...look, tryon_image_url: currentImageUrl })}
            />
          ) : (
            <div className="w-full h-full p-4 relative">
              <GarmentCollage garmentIds={look.garment_ids} className="w-full h-full" />
              
              {/* Runway overlay on hover */}
              <div 
                className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-2 cursor-pointer p-6"
                onClick={() => setDetailLook(look)}
              >
                <Eye className="w-6 h-6 text-white" />
                <span className="text-xs font-semibold text-white uppercase tracking-wider">Inspect Details</span>
              </div>
            </div>
          )}

          {/* Top Score Badge */}
          {look.score && (
            <div className="absolute top-3 right-3 px-2 py-1 rounded bg-black/40 backdrop-blur-md border border-white/10 text-[9px] font-bold text-emerald-400 tracking-wider">
              {Math.round(look.score * 100)}% MATCH
            </div>
          )}

          {/* Loader Overlay */}
          {isGenerating && (
            <div className="absolute inset-0 bg-black/75 backdrop-blur-sm flex flex-col items-center justify-center text-center p-4">
              <Wand2 className="w-8 h-8 text-[var(--accent)] animate-pulse mb-3" />
              <p className="text-xs font-bold text-white uppercase tracking-widest">Dressing Avatar...</p>
              <p className="text-[10px] text-white/50 mt-1 max-w-[150px]">Calling Fal.ai SAM & Vertex AI</p>
            </div>
          )}
        </div>

        {/* Content Info */}
        <div className="p-4 flex-1 flex flex-col justify-between gap-3">
          <div>
            <div className="flex items-center gap-1.5 text-[8px] font-semibold uppercase tracking-widest text-[var(--accent)]">
              <span>{look.occasion || 'Everyday'}</span>
            </div>
            <h3 
              className="text-base font-bold leading-tight mt-1 line-clamp-1 cursor-pointer hover:text-[var(--accent)] transition-colors"
              style={{ fontFamily: "'Playfair Display', Georgia, serif", color: 'var(--text-primary)' }}
              onClick={() => setDetailLook(look)}
            >
              {look.title}
            </h3>
            <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed line-clamp-2">
              {look.why_it_works}
            </p>
          </div>

          <div className="flex items-center gap-2 pt-2 border-t border-[var(--glass-border)]">
            {hasTryon ? (
              <button 
                onClick={() => setDetailLook({ ...look, tryon_image_url: currentImageUrl })}
                className="btn-secondary btn-sm flex-1 flex items-center justify-center gap-1"
              >
                <Eye className="w-3.5 h-3.5" />
                <span>View Try-on</span>
              </button>
            ) : (
              <button 
                onClick={() => handleRunTryOn(look)}
                disabled={isGenerating}
                className="btn-primary btn-sm flex-1 flex items-center justify-center gap-1 bg-[var(--accent)] text-white hover:bg-[var(--accent-light)] border-0"
              >
                <Wand2 className="w-3.5 h-3.5" />
                <span>Try on Avatar</span>
              </button>
            )}

            <button 
              onClick={() => handleFeedback(look.id, 'love')}
              className="w-9 h-9 rounded-md border border-[var(--glass-border)] hover:bg-[var(--glass-bg-elevated)] flex items-center justify-center text-[var(--text-secondary)] hover:text-rose-400 transition-colors"
            >
              <Heart className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen safe-top safe-bottom flex flex-col" style={{ background: 'var(--bg-primary)' }}>
      {generatingFeed && <LoadingOverlay message={loadingMessage} />}
      
      {/* Scrollable Container */}
      <div className="flex-1 overflow-y-auto page-container nav-bottom-spacing">
        
        {/* Editorial Masthead */}
        <header className="mx-4 mt-8 mb-6 border-b border-[var(--glass-border)] pb-5 text-center relative">
          <div className="flex justify-between items-center px-2 text-[9px] font-bold text-[var(--text-tertiary)] tracking-[0.2em] mb-2 uppercase">
            <div className="flex items-center gap-2">
              <span>ISSUE NO. 01</span>
              {isMockMode && (
                <span className="px-1.5 py-0.5 rounded text-[8px] font-extrabold text-amber-500 bg-amber-500/10 border border-amber-500/20 tracking-normal uppercase">
                  DEMO CLOSET
                </span>
              )}
            </div>
            <span>{dateHeader}</span>
            <div className="flex items-center gap-3">
              {isMockMode && (
                <button 
                  onClick={() => {
                    setIsMockMode(false)
                    setIsOnboarding(true)
                  }}
                  className="flex items-center gap-1 text-rose-400 hover:text-rose-300 transition-colors uppercase tracking-[0.2em]"
                >
                  EXIT
                </button>
              )}
              <button 
                onClick={() => fetchMagazineFeed(true)}
                className="flex items-center gap-1 hover:text-[var(--accent)] transition-colors uppercase tracking-[0.2em]"
              >
                <RefreshCw className="w-3 h-3" />
                <span>EDIT</span>
              </button>
            </div>
          </div>
          
          <h1 
            className="text-[48px] md:text-[64px] font-bold leading-none select-none tracking-tighter"
            style={{ fontFamily: "'Playfair Display', Georgia, serif", color: 'var(--text-primary)' }}
          >
            The Looker
          </h1>
          <span 
            className="text-[9px] tracking-[0.3em] font-semibold text-center uppercase block mt-3"
            style={{ fontFamily: "'Syne', sans-serif", color: 'var(--accent)' }}
          >
            THE MAGAZINE OF YOUR CLOSET
          </span>
        </header>

        {/* 1. Today's Cover Look */}
        {coverLook && (
          <section className="mx-4 mb-10">
            <div className="text-[10px] tracking-[0.2em] font-bold uppercase text-[var(--text-tertiary)] mb-3 flex items-center gap-2">
              <span className="w-2 h-px bg-[var(--glass-border)]" />
              <span>THE COVER LOOK</span>
            </div>

            <div className="glass-card-elevated border border-[var(--glass-border)] overflow-hidden grid grid-cols-1 md:grid-cols-12 gap-0">
              
              {/* Left Column: Image Area */}
              <div className="md:col-span-6 aspect-[3/4] relative overflow-hidden bg-black/10 flex items-center justify-center">
                {tryOnImages[coverLook.id] ? (
                  <img 
                    src={tryOnImages[coverLook.id]} 
                    alt="Cover Look Tryon" 
                    className="w-full h-full object-contain cursor-pointer hover:scale-102 transition-transform duration-500"
                    onClick={() => setDetailLook({ ...coverLook, tryon_image_url: tryOnImages[coverLook.id] })}
                  />
                ) : (
                  <div className="w-full h-full p-6 relative">
                    <GarmentCollage garmentIds={coverLook.garment_ids} className="w-full h-full border-0" />
                    
                    {/* Big Overlay tryon guide */}
                    <div 
                      className="absolute inset-0 bg-black/20 hover:bg-black/40 transition-colors flex items-center justify-center cursor-pointer group"
                      onClick={() => setDetailLook(coverLook)}
                    >
                      <div className="w-12 h-12 rounded-full bg-black/50 backdrop-blur-md border border-white/20 flex items-center justify-center group-hover:scale-110 transition-transform">
                        <Eye className="w-5 h-5 text-white" />
                      </div>
                    </div>
                  </div>
                )}

                {/* Score Tag */}
                {coverLook.score && (
                  <div className="absolute top-4 right-4 px-3 py-1.5 rounded-full bg-black/60 backdrop-blur-md border border-white/10 text-[10px] font-bold text-emerald-400 tracking-wider">
                    {Math.round(coverLook.score * 100)}% Harmony
                  </div>
                )}
                
                {/* Image generation loading */}
                {tryOnLoading[coverLook.id] && (
                  <div className="absolute inset-0 bg-black/75 backdrop-blur-sm flex flex-col items-center justify-center text-center p-4">
                    <Wand2 className="w-8 h-8 text-[var(--accent)] animate-pulse mb-3" />
                    <p className="text-sm font-bold text-white uppercase tracking-widest">Compiling Runway Fit...</p>
                    <p className="text-xs text-white/50 mt-1 max-w-[180px]">Generating Segmentations on Fal.ai & styling avatar</p>
                  </div>
                )}
              </div>

              {/* Right Column: Editorial Copy */}
              <div className="md:col-span-6 p-6 md:p-8 flex flex-col justify-between gap-6 border-t md:border-t-0 md:border-l border-[var(--glass-border)]">
                <div className="space-y-4">
                  <div className="inline-block px-2.5 py-1 rounded bg-[var(--accent-glow)] text-[9px] font-bold tracking-widest text-[var(--accent-light)] uppercase">
                    {coverLook.occasion || 'Featured Look'}
                  </div>

                  <div className="space-y-1">
                    <h2 
                      className="text-2xl md:text-3xl font-bold leading-tight"
                      style={{ fontFamily: "'Playfair Display', Georgia, serif", color: 'var(--text-primary)' }}
                    >
                      {coverLook.title}
                    </h2>
                    {coverLook.subtitle && (
                      <p className="text-xs font-semibold uppercase tracking-widest text-[var(--text-tertiary)]">
                        {coverLook.subtitle}
                      </p>
                    )}
                  </div>

                  {/* Editorial Pull Quote */}
                  <blockquote className="border-l-2 border-[var(--accent)] pl-4 italic text-sm text-[var(--text-secondary)] leading-relaxed">
                    "{coverLook.why_it_works}"
                  </blockquote>

                  {/* Styling Tips */}
                  {coverLook.styling_tips?.length > 0 && (
                    <div className="space-y-2 pt-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-primary)] block">Styling Directives</span>
                      <ul className="space-y-1 text-xs text-[var(--text-secondary)] list-disc pl-4 leading-relaxed">
                        {coverLook.styling_tips.map((tip, i) => (
                          <li key={i}>{tip}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Alternative suggestions (Swaps) */}
                  {coverLook.swaps?.length > 0 && (
                    <div className="pt-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-primary)] block mb-1">Swap Options</span>
                      {coverLook.swaps.map((s, index) => (
                        <div key={index} className="text-xs text-[var(--text-secondary)] leading-relaxed flex items-start gap-2 bg-[var(--glass-bg)] p-3 rounded-lg border border-[var(--glass-border)]">
                          <Shirt className="w-4 h-4 text-[var(--accent)] flex-shrink-0 mt-0.5" />
                          <p>
                            Replace <strong>{cleanCategory(getGarment(s.replace_item_id)?.category)}</strong> with your <strong>{getGarment(s.with_item_id)?.colors?.color_family} {cleanCategory(getGarment(s.with_item_id)?.category)}</strong>: {s.reason}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Cover Actions */}
                <div className="flex items-center gap-3 pt-6 border-t border-[var(--glass-border)]">
                  {tryOnImages[coverLook.id] ? (
                    <button 
                      onClick={() => setDetailLook({ ...coverLook, tryon_image_url: tryOnImages[coverLook.id] })}
                      className="btn-secondary btn-lg flex-1 flex items-center justify-center gap-2"
                    >
                      <Eye className="w-4 h-4" />
                      <span>Inspect Fit</span>
                    </button>
                  ) : (
                    <button 
                      onClick={() => handleRunTryOn(coverLook)}
                      disabled={tryOnLoading[coverLook.id]}
                      className="btn-primary btn-lg flex-1 flex items-center justify-center gap-2"
                    >
                      <Wand2 className="w-4 h-4" />
                      <span>Try on Avatar</span>
                    </button>
                  )}

                  <button 
                    onClick={() => handleFeedback(coverLook.id, 'love')}
                    className="w-12 h-12 rounded-xl border border-[var(--glass-border)] hover:bg-[var(--glass-bg-elevated)] flex items-center justify-center text-[var(--text-secondary)] hover:text-rose-400 transition-colors"
                  >
                    <Heart className="w-5 h-5" />
                  </button>
                  
                  <button 
                    onClick={() => handleFeedback(coverLook.id, 'save')}
                    className="w-12 h-12 rounded-xl border border-[var(--glass-border)] hover:bg-[var(--glass-bg-elevated)] flex items-center justify-center text-[var(--text-secondary)] hover:text-amber-400 transition-colors"
                  >
                    <Bookmark className="w-5 h-5" />
                  </button>
                </div>
              </div>

            </div>
          </section>
        )}

        {/* 2. Three Fits From Your Closet */}
        {dailyFits.length > 0 && (
          <section className="mx-4 mb-10">
            <div className="text-[10px] tracking-[0.2em] font-bold uppercase text-[var(--text-tertiary)] mb-4 flex items-center gap-2">
              <span className="w-2 h-px bg-[var(--glass-border)]" />
              <span>THE DAILY EDIT</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
              {dailyFits.map(look => (
                <LookCardView key={look.id} look={look} sectionName="daily" />
              ))}
            </div>
          </section>
        )}

        {/* 3. One Item, Three Ways */}
        {oneItemFits.length > 0 && (
          <section className="mx-4 mb-10">
            <div className="text-[10px] tracking-[0.2em] font-bold uppercase text-[var(--text-tertiary)] mb-4 flex items-center gap-2">
              <span className="w-2 h-px bg-[var(--glass-border)]" />
              <span>ONE STAPLE, THREE WAYS</span>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
              
              {/* Feature Garment Panel */}
              <div className="lg:col-span-3 glass-card-static border border-[var(--glass-border)] p-6 flex flex-col justify-center items-center text-center relative overflow-hidden bg-black/5">
                <span className="text-[8px] font-bold tracking-[0.2em] uppercase text-[var(--accent)] mb-3">STAPLE FOCUS</span>
                {oneItemFits[0]?.hero_item_id && getGarment(oneItemFits[0].hero_item_id) ? (
                  <div className="w-36 h-36 flex items-center justify-center rounded-2xl bg-[var(--bg-primary)] border border-[var(--glass-border)] p-3 relative overflow-hidden group">
                    <img 
                      src={getGarment(oneItemFits[0].hero_item_id).front_url || getGarment(oneItemFits[0].hero_item_id).url} 
                      alt="Featured garment" 
                      className="w-full h-full object-contain group-hover:scale-105 transition-transform"
                    />
                  </div>
                ) : (
                  <Shirt className="w-12 h-12 opacity-35" />
                )}
                <h4 
                  className="text-base font-bold mt-4"
                  style={{ fontFamily: "'Playfair Display', Georgia, serif", color: 'var(--text-primary)' }}
                >
                  {oneItemFits[0]?.hero_item_id && getGarment(oneItemFits[0].hero_item_id)?.description?.short || 'Classic Staple'}
                </h4>
                <p className="text-xs text-[var(--text-tertiary)] mt-1.5 leading-relaxed max-w-[160px]">
                  Styling one foundational closet staple for three distinct occasions.
                </p>
              </div>

              {/* The Three styled fits */}
              <div className="lg:col-span-9 grid grid-cols-1 sm:grid-cols-3 gap-6">
                {oneItemFits.map(look => (
                  <LookCardView key={look.id} look={look} sectionName="one_item_three_ways" />
                ))}
              </div>

            </div>
          </section>
        )}

        {/* 4. The Underused Edit */}
        {underusedEdit && (
          <section className="mx-4 mb-8">
            <div className="text-[10px] tracking-[0.2em] font-bold uppercase text-[var(--text-tertiary)] mb-4 flex items-center gap-2">
              <span className="w-2 h-px bg-[var(--glass-border)]" />
              <span>THE UNDERUSED EDIT</span>
            </div>

            <div className="glass-card-static border border-[var(--glass-border)] hover:border-amber-500/30 transition-colors overflow-hidden grid grid-cols-1 md:grid-cols-12 gap-0 relative">
              <div className="absolute top-4 left-4 z-10 px-3 py-1 text-[8px] font-bold uppercase tracking-widest text-amber-500 bg-amber-500/10 border border-amber-500/20 rounded-md">
                CLOSET RESURRECTION
              </div>

              {/* Right/Left Image Area */}
              <div className="md:col-span-5 aspect-[3/4] relative overflow-hidden bg-black/10 flex items-center justify-center">
                {tryOnImages[underusedEdit.id] ? (
                  <img 
                    src={tryOnImages[underusedEdit.id]} 
                    alt="Underused look tryon" 
                    className="w-full h-full object-contain cursor-pointer"
                    onClick={() => setDetailLook({ ...underusedEdit, tryon_image_url: tryOnImages[underusedEdit.id] })}
                  />
                ) : (
                  <div className="w-full h-full p-6 relative">
                    <GarmentCollage garmentIds={underusedEdit.garment_ids} className="w-full h-full border-0" />
                    
                    <div 
                      className="absolute inset-0 bg-black/10 hover:bg-black/35 transition-colors flex items-center justify-center cursor-pointer group"
                      onClick={() => setDetailLook(underusedEdit)}
                    >
                      <div className="w-10 h-10 rounded-full bg-black/50 backdrop-blur-md border border-white/20 flex items-center justify-center group-hover:scale-110 transition-transform">
                        <Eye className="w-4 h-4 text-white" />
                      </div>
                    </div>
                  </div>
                )}

                {tryOnLoading[underusedEdit.id] && (
                  <div className="absolute inset-0 bg-black/75 backdrop-blur-sm flex flex-col items-center justify-center text-center p-4">
                    <Wand2 className="w-8 h-8 text-[var(--accent)] animate-pulse mb-3" />
                    <p className="text-xs font-bold text-white uppercase tracking-widest">Resurrecting outfit...</p>
                  </div>
                )}
              </div>

              {/* Text Description */}
              <div className="md:col-span-7 p-6 md:p-8 flex flex-col justify-between gap-5">
                <div className="space-y-4">
                  <div className="space-y-1">
                    <h3 
                      className="text-xl md:text-2xl font-bold leading-tight"
                      style={{ fontFamily: "'Playfair Display', Georgia, serif", color: 'var(--text-primary)' }}
                    >
                      {underusedEdit.title}
                    </h3>
                    <p className="text-xs font-semibold text-[var(--text-tertiary)] uppercase tracking-wider">
                      Focusing your under-worn {underusedEdit.hero_item_id && getGarment(underusedEdit.hero_item_id) ? cleanCategory(getGarment(underusedEdit.hero_item_id).category) : 'garment'}
                    </p>
                  </div>

                  <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                    {underusedEdit.why_it_works}
                  </p>

                  <div className="flex items-start gap-3 p-3 rounded-lg border border-amber-500/10 bg-amber-500/5">
                    <Shirt className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                    <div className="text-xs text-[var(--text-secondary)] leading-relaxed">
                      <strong>Focus garment:</strong> {underusedEdit.hero_item_id && getGarment(underusedEdit.hero_item_id)?.description?.short || 'Foundation piece'}. Let's bring this back into rotation.
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 pt-4 border-t border-[var(--glass-border)]">
                  {tryOnImages[underusedEdit.id] ? (
                    <button 
                      onClick={() => setDetailLook({ ...underusedEdit, tryon_image_url: tryOnImages[underusedEdit.id] })}
                      className="btn-secondary btn-md flex-1 flex items-center justify-center gap-1.5"
                    >
                      <Eye className="w-4 h-4" />
                      <span>Inspect Look</span>
                    </button>
                  ) : (
                    <button 
                      onClick={() => handleRunTryOn(underusedEdit)}
                      disabled={tryOnLoading[underusedEdit.id]}
                      className="btn-primary btn-md flex-1 flex items-center justify-center gap-1.5 bg-amber-600 hover:bg-amber-700 text-white border-0"
                    >
                      <Wand2 className="w-4 h-4" />
                      <span>Try on Avatar</span>
                    </button>
                  )}
                  
                  <button 
                    onClick={() => handleFeedback(underusedEdit.id, 'love')}
                    className="w-10 h-10 rounded-lg border border-[var(--glass-border)] hover:bg-[var(--glass-bg-elevated)] flex items-center justify-center text-[var(--text-secondary)] hover:text-rose-400 transition-colors"
                  >
                    <Heart className="w-4.5 h-4.5" />
                  </button>
                </div>
              </div>

            </div>
          </section>
        )}

      </div>

      {/* 5. Detail Modal View */}
      {detailLook && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md"
          onClick={() => setDetailLook(null)}
        >
          <div 
            className="w-full max-w-2xl max-h-[85vh] overflow-y-auto glass-card-elevated border border-[var(--glass-border-hover)] rounded-2xl flex flex-col md:flex-row gap-0"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Left Image */}
            <div className="md:w-1/2 aspect-[3/4] md:aspect-auto relative bg-black/10 flex items-center justify-center">
              {detailLook.tryon_image_url ? (
                <img 
                  src={detailLook.tryon_image_url} 
                  alt={detailLook.title} 
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="w-full h-full p-6 relative flex items-center justify-center">
                  <GarmentCollage garmentIds={detailLook.garment_ids} className="w-full h-full border-0" />
                </div>
              )}
              
              {tryOnLoading[detailLook.id] && (
                <div className="absolute inset-0 bg-black/75 backdrop-blur-sm flex flex-col items-center justify-center text-center p-4">
                  <Wand2 className="w-6 h-6 text-[var(--accent)] animate-pulse mb-2" />
                  <p className="text-xs font-bold text-white uppercase tracking-widest">Dressing avatar...</p>
                </div>
              )}
            </div>

            {/* Modal Right Info */}
            <div className="md:w-1/2 p-6 flex flex-col justify-between gap-5 bg-[var(--bg-secondary)] border-t md:border-t-0 md:border-l border-[var(--glass-border)]">
              <div className="space-y-4">
                <div className="flex justify-between items-start gap-2">
                  <span className="inline-block px-2 py-0.5 rounded bg-[var(--accent-glow)] text-[8px] font-bold tracking-wider text-[var(--accent-light)] uppercase">
                    {detailLook.occasion || 'Fit Details'}
                  </span>
                  <button 
                    onClick={() => setDetailLook(null)}
                    className="text-xs text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors"
                  >
                    Close
                  </button>
                </div>

                <div className="space-y-0.5">
                  <h3 
                    className="text-xl font-bold leading-tight"
                    style={{ fontFamily: "'Playfair Display', Georgia, serif", color: 'var(--text-primary)' }}
                  >
                    {detailLook.title}
                  </h3>
                  {detailLook.subtitle && (
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
                      {detailLook.subtitle}
                    </p>
                  )}
                </div>

                <p className="text-xs text-[var(--text-secondary)] leading-relaxed bg-[var(--bg-primary)] p-3 rounded-lg border border-[var(--glass-border)]">
                  {detailLook.why_it_works}
                </p>

                {/* Outfit list details */}
                <div className="space-y-2">
                  <span className="text-[9px] font-bold uppercase tracking-wider text-[var(--text-primary)]">GARMENTS IN FIT</span>
                  <div className="space-y-1.5">
                    {detailLook.garment_ids.map(id => {
                      const g = getGarment(id)
                      return (
                        <div key={id} className="flex items-center gap-2 p-1.5 bg-[var(--glass-bg)] border border-[var(--glass-border)] rounded-lg">
                          <div className="w-8 h-8 rounded bg-[var(--bg-primary)] flex items-center justify-center p-0.5 border border-[var(--glass-border)] overflow-hidden">
                            {g ? (
                              <img src={g.front_url || g.url} alt="Garment" className="w-full h-full object-contain" />
                            ) : (
                              <Shirt className="w-4 h-4 opacity-30" />
                            )}
                          </div>
                          <div className="text-left">
                            <p className="text-[10px] font-bold leading-none" style={{ color: 'var(--text-primary)' }}>
                              {g?.description?.short || 'Clothing Item'}
                            </p>
                            <p className="text-[8px] text-[var(--text-tertiary)] mt-0.5 uppercase tracking-wider font-semibold">
                              {g?.colors?.color_family || 'Color'} • {cleanCategory(g?.category)}
                            </p>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Styling tips list */}
                {detailLook.styling_tips?.length > 0 && (
                  <div className="space-y-1">
                    <span className="text-[9px] font-bold uppercase tracking-wider text-[var(--text-primary)]">DIRECTIVES</span>
                    <ul className="list-disc pl-4 text-[10px] text-[var(--text-secondary)] leading-relaxed space-y-0.5">
                      {detailLook.styling_tips.map((tip, i) => (
                        <li key={i}>{tip}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Bottom Actions */}
              <div className="flex items-center gap-2 pt-4 border-t border-[var(--glass-border)]">
                {!detailLook.tryon_image_url && (
                  <button 
                    onClick={() => handleRunTryOn(detailLook)}
                    disabled={tryOnLoading[detailLook.id]}
                    className="btn-primary btn-sm flex-1 flex items-center justify-center gap-1.5"
                  >
                    <Wand2 className="w-4.5 h-4.5" />
                    <span>Run Try-on</span>
                  </button>
                )}
                
                <button 
                  onClick={() => {
                    handleFeedback(detailLook.id, 'love')
                    setDetailLook(null)
                  }}
                  className="btn-secondary btn-sm flex-1 flex items-center justify-center gap-1 hover:text-rose-400"
                >
                  <Heart className="w-3.5 h-3.5" />
                  <span>Love</span>
                </button>
                
                <button 
                  onClick={() => {
                    handleFeedback(detailLook.id, 'save')
                    setDetailLook(null)
                  }}
                  className="btn-secondary btn-sm flex-1 flex items-center justify-center gap-1 hover:text-amber-400"
                >
                  <Bookmark className="w-3.5 h-3.5" />
                  <span>Save</span>
                </button>
              </div>
            </div>

          </div>
        </div>
      )}

      {/* Bottom Navigation */}
      <BottomNav />
    </div>
  )
}
