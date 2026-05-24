import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Sun, Cloud, CloudRain, Snowflake, Thermometer,
  Sparkles, RefreshCw, Shirt, User, Wind, CloudFog, CloudLightning,
  Palette, Calendar, ChevronLeft, ChevronRight, Wand2, ArrowRight
} from 'lucide-react'
import { useWardrobe } from '../context/WardrobeContext'
import { useAuth } from '../context/AuthContext'
import LoadingOverlay from '../components/LoadingOverlay'
import BottomNav from '../components/BottomNav'

const API_URL = import.meta.env.VITE_API_URL || ''

// Weather icon mapping based on backend icon names
const weatherIconMap = {
  'sun': Sun,
  'cloud': Cloud,
  'cloud-rain': CloudRain,
  'snowflake': Snowflake,
  'thermometer': Thermometer,
  'wind': Wind,
  'cloud-fog': CloudFog,
  'cloud-lightning': CloudLightning,
}

// Legacy weather icon mapping for current weather
const weatherIcons = {
  clear: Sun,
  cloudy: Cloud,
  rainy: CloudRain,
  snowy: Snowflake,
  hot: Thermometer,
  cold: Snowflake,
}

// Get icon component from backend icon name
const getWeatherIcon = (iconName) => {
  return weatherIconMap[iconName] || Cloud
}

export default function DailyOutfit() {
  const navigate = useNavigate()
  const { avatarUrl, garments, fetchGarments } = useWardrobe()
  const { getIdToken } = useAuth()
  
  const [dailyLooks, setDailyLooks] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedLookIndex, setSelectedLookIndex] = useState(0)
  const [isRegenerating, setIsRegenerating] = useState(false)
  const [dayForecast, setDayForecast] = useState(null)

  // Helper to make authenticated fetch requests
  const authFetch = useCallback(async (url, options = {}) => {
    const token = await getIdToken()
    if (!token) throw new Error('Not authenticated')
    
    const headers = {
      ...options.headers,
      'Authorization': `Bearer ${token}`,
    }
    return fetch(url, { ...options, headers })
  }, [getIdToken])

  const fetchDayForecast = useCallback(async () => {
    try {
      const response = await authFetch(`${API_URL}/api/weather/forecast`)
      const data = await response.json()
      if (data.status === 'success' && data.forecast) {
        setDayForecast(data.forecast)
      }
    } catch (err) {
      console.error('Failed to fetch day forecast:', err)
    }
  }, [authFetch])

  const fetchDailyLooks = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      const response = await authFetch(`${API_URL}/api/daily-looks/latest`)
      const data = await response.json()
      
      if (data.status === 'success' && data.looks) {
        setDailyLooks(data.looks)
      } else if (data.status === 'not_generated') {
        setError('no_looks')
      } else {
        setError('failed')
      }
    } catch (err) {
      console.error('Failed to fetch daily looks:', err)
      setError('failed')
    } finally {
      setIsLoading(false)
    }
  }, [authFetch])

  useEffect(() => {
    fetchDailyLooks()
    fetchGarments()
    fetchDayForecast()
  }, [fetchDailyLooks, fetchGarments, fetchDayForecast])

  const handleRegenerate = async () => {
    setIsRegenerating(true)
    try {
      await authFetch(`${API_URL}/api/daily-looks/generate?force=true`, { method: 'POST' })
      // Wait a bit for generation to complete (it runs in background)
      setTimeout(() => {
        fetchDailyLooks()
        setIsRegenerating(false)
      }, 5000)
    } catch (err) {
      console.error('Failed to regenerate:', err)
      setIsRegenerating(false)
    }
  }

  // Parse weather from context string like "10.23°C, Light rain in Current Location"
  const parseWeatherContext = (context) => {
    if (!context) return null
    const tempMatch = context.match(/([\d.]+)°C/)
    const temp = tempMatch ? parseFloat(tempMatch[1]) : null
    const descMatch = context.match(/°C,\s*([^in]+)/)
    const description = descMatch ? descMatch[1].trim() : ''
    const locationMatch = context.match(/in\s+(.+)$/)
    const location = locationMatch ? locationMatch[1].trim() : ''
    
    // Determine weather condition
    let condition = 'clear'
    const descLower = description.toLowerCase()
    if (descLower.includes('rain') || descLower.includes('drizzle')) condition = 'rainy'
    else if (descLower.includes('snow')) condition = 'snowy'
    else if (descLower.includes('cloud') || descLower.includes('overcast')) condition = 'cloudy'
    else if (temp && temp > 28) condition = 'hot'
    else if (temp && temp < 5) condition = 'cold'
    
    return { temp, description, location, condition }
  }

  const selectedLook = dailyLooks?.looks?.[selectedLookIndex]
  const weather = selectedLook ? parseWeatherContext(selectedLook.weather_context) : null
  const WeatherIcon = weather ? weatherIcons[weather.condition] || Sun : Sun

  // Clean up text that may contain enum strings like "ColorSeason.SPRING"
  const cleanEnumText = (text) => {
    if (!text) return text
    return text.replace(/(\w+)\.(\w+)/g, (match, prefix, value) => {
      return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase()
    })
  }

  // Remove duplicate style text from reasoning
  const cleanReasoning = (reasoning, styleNotes) => {
    if (!reasoning || !styleNotes) return reasoning
    return reasoning
      .replace(`. ${styleNotes}`, '')
      .replace(styleNotes, '')
      .replace(/\.\s*$/, '')
      .trim() || 'Great outfit for today'
  }

  const today = new Date()
  const dateStr = today.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })

  return (
    <div className="min-h-screen safe-top safe-bottom flex flex-col" style={{ background: 'var(--bg-primary)' }}>
      {isRegenerating && <LoadingOverlay message="Creating new looks..." />}
      
      {/* Hero Header */}
      <div className="page-container">
        <header className="mx-4 mt-4 glass-card-static p-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                Today's Looks
              </h1>
              <div className="flex items-center gap-1.5 mt-1">
                <Calendar className="w-3.5 h-3.5" style={{ color: 'var(--text-tertiary)' }} />
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{dateStr}</p>
              </div>
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
          </div>
        </header>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto page-container space-y-5 mt-5 nav-bottom-spacing">
        {/* Weather Forecast */}
        {(weather || dayForecast) && (
          <div className="mx-4 glass-card-static p-5">
            {dayForecast && dayForecast.length > 0 ? (
              <div className="flex items-center justify-center gap-4 sm:gap-6 flex-wrap">
                {dayForecast.map((forecast, index) => {
                  const IconComponent = getWeatherIcon(forecast.icon)
                  const accentColors = [
                    'rgba(251, 191, 36, 0.15)',
                    'rgba(249, 115, 22, 0.15)', 
                    'rgba(244, 63, 94, 0.15)',
                    'rgba(99, 102, 241, 0.15)'
                  ]
                  const iconColors = [
                    '#fbbf24',
                    '#f97316', 
                    '#f43f5e',
                    '#6366f1'
                  ]
                  
                  return (
                    <div key={forecast.time_label} className="flex items-center gap-3 glass-card-static px-4 py-3">
                      <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 relative"
                        style={{ background: accentColors[index] }}
                      >
                        <IconComponent className="w-5 h-5" style={{ color: iconColors[index] }} />
                        {forecast.is_windy && (
                          <div
                            className="absolute -top-1 -right-1 w-4 h-4 rounded-full flex items-center justify-center"
                            style={{ background: 'var(--bg-surface)', border: '1px solid var(--glass-border)' }}
                          >
                            <Wind className="w-2.5 h-2.5" style={{ color: 'var(--text-secondary)' }} />
                          </div>
                        )}
                      </div>
                      <div className="flex flex-col">
                        <span className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>
                          {forecast.temp}°
                        </span>
                        <span className="text-[10px] font-medium" style={{ color: 'var(--text-tertiary)' }}>
                          {forecast.time_label}
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : weather && (
              <div className="flex items-center justify-center gap-4 sm:gap-6 flex-wrap">
                {['Morn', 'Noon', 'Eve', 'Night'].map((label, index) => {
                  const accentColors = ['rgba(251, 191, 36, 0.15)', 'rgba(249, 115, 22, 0.15)', 'rgba(244, 63, 94, 0.15)', 'rgba(99, 102, 241, 0.15)']
                  const iconColors = ['#fbbf24', '#f97316', '#f43f5e', '#6366f1']
                  const icons = [Sun, WeatherIcon, Cloud, Cloud]
                  const Icon = icons[index]
                  return (
                    <div key={label} className="flex items-center gap-3 glass-card-static px-4 py-3">
                      <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                        style={{ background: accentColors[index] }}
                      >
                        <Icon className="w-5 h-5" style={{ color: iconColors[index] }} />
                      </div>
                      <div className="flex flex-col">
                        <span className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>
                          {weather.temp ? `${Math.round(weather.temp)}°` : '--°'}
                        </span>
                        <span className="text-[10px] font-medium" style={{ color: 'var(--text-tertiary)' }}>{label}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {/* Initial Loading */}
        {isLoading && !dailyLooks && (
          <div className="mx-4 glass-card-static overflow-hidden">
            <div className="aspect-[3/4] animate-shimmer" />
            <div className="p-5 space-y-4">
              <div className="h-20 rounded-xl animate-shimmer" />
              <div className="h-12 rounded-xl animate-shimmer" />
            </div>
          </div>
        )}

        {/* No Looks — Premium Empty State */}
        {error === 'no_looks' && !isLoading && (
          <div className="mx-4 space-y-5">
            {/* Main CTA Card */}
            <div className="glass-card-elevated p-8 text-center">
              <div
                className="w-20 h-20 mx-auto mb-5 rounded-2xl flex items-center justify-center"
                style={{ background: 'var(--accent-glow)' }}
              >
                <Sparkles className="w-10 h-10" style={{ color: 'var(--accent-light)' }} />
              </div>
              <h3 className="text-xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
                No looks generated yet
              </h3>
              <p className="text-sm mb-6 max-w-sm mx-auto" style={{ color: 'var(--text-secondary)' }}>
                Daily looks are generated automatically at 6 AM, or you can create them now.
              </p>
              {!avatarUrl ? (
                <button onClick={() => navigate('/create-avatar')} className="btn-primary btn-lg w-full max-w-xs mx-auto">
                  Create Your Profile First
                </button>
              ) : garments.length < 2 ? (
                <button onClick={() => navigate('/capture')} className="btn-primary btn-lg w-full max-w-xs mx-auto">
                  Add More Clothes
                </button>
              ) : (
                <button onClick={handleRegenerate} className="btn-primary btn-lg w-full max-w-xs mx-auto">
                  <Sparkles className="w-4 h-4" />
                  Generate Today's Looks
                </button>
              )}
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <button
                onClick={() => navigate('/wardrobe')}
                className="glass-card-static p-5 flex items-center gap-4 text-left transition-all hover:border-[var(--glass-border-hover)]"
              >
                <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: 'rgba(74, 222, 128, 0.12)' }}>
                  <Shirt className="w-6 h-6" style={{ color: '#4ade80' }} />
                </div>
                <div>
                  <h4 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>My Wardrobe</h4>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>Browse {garments.length} items</p>
                </div>
                <ArrowRight className="w-4 h-4 ml-auto" style={{ color: 'var(--text-tertiary)' }} />
              </button>
              <button
                onClick={() => navigate('/dressing-room')}
                className="glass-card-static p-5 flex items-center gap-4 text-left transition-all hover:border-[var(--glass-border-hover)]"
              >
                <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: 'rgba(168, 85, 247, 0.12)' }}>
                  <Sparkles className="w-6 h-6" style={{ color: '#a855f7' }} />
                </div>
                <div>
                  <h4 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Try On Manually</h4>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>Build your own outfit</p>
                </div>
                <ArrowRight className="w-4 h-4 ml-auto" style={{ color: 'var(--text-tertiary)' }} />
              </button>
            </div>
          </div>
        )}

        {error === 'failed' && !isLoading && (
          <div className="mx-4 glass-card-elevated p-8 text-center">
            <p className="font-medium mb-4" style={{ color: 'var(--text-primary)' }}>
              Failed to load recommendations
            </p>
            <button onClick={fetchDailyLooks} className="btn-ghost">
              Try Again
            </button>
          </div>
        )}

        {/* Daily Looks Content */}
        {dailyLooks && dailyLooks.looks && dailyLooks.looks.length > 0 && (
          <div className="mx-4">
            {selectedLook && (
              <div className="grid grid-cols-1 md:grid-cols-12 gap-5 items-start">
                
                {/* Left Column: Try-on Image */}
                <div className="md:col-span-5 glass-card-static overflow-hidden relative w-full aspect-[3/4]">
                  <img
                    src={selectedLook.tryon_image_url}
                    alt="Today's outfit"
                    className="w-full h-full object-contain"
                  />
                  
                  {/* Navigation Arrows */}
                  {dailyLooks.looks.length > 1 && (
                    <>
                      <button
                        onClick={() => setSelectedLookIndex(prev => prev === 0 ? dailyLooks.looks.length - 1 : prev - 1)}
                        className="absolute left-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full flex items-center justify-center transition-colors"
                        style={{ background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(8px)' }}
                      >
                        <ChevronLeft className="w-5 h-5" style={{ color: 'var(--text-primary)' }} />
                      </button>
                      <button
                        onClick={() => setSelectedLookIndex(prev => prev === dailyLooks.looks.length - 1 ? 0 : prev + 1)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full flex items-center justify-center transition-colors"
                        style={{ background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(8px)' }}
                      >
                        <ChevronRight className="w-5 h-5" style={{ color: 'var(--text-primary)' }} />
                      </button>
                    </>
                  )}
                  
                  {/* Score Badge */}
                  <div
                    className="absolute top-4 right-4 px-4 py-2 rounded-full"
                    style={{ background: 'rgba(74, 222, 128, 0.2)', border: '1px solid rgba(74, 222, 128, 0.3)', backdropFilter: 'blur(8px)' }}
                  >
                    <span className="text-sm font-semibold" style={{ color: '#4ade80' }}>
                      {Math.round(selectedLook.score * 100)}% Match
                    </span>
                  </div>
                  
                  {/* Look Number */}
                  <div
                    className="absolute top-4 left-4 px-4 py-2 rounded-full"
                    style={{ background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(8px)' }}
                  >
                    <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                      Look {selectedLookIndex + 1} of {dailyLooks.looks.length}
                    </span>
                  </div>
                  
                  {/* Dots */}
                  {dailyLooks.looks.length > 1 && (
                    <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1.5 px-3 py-1.5 rounded-full" style={{ background: 'rgba(0,0,0,0.4)' }}>
                      {dailyLooks.looks.map((_, index) => (
                        <button
                          key={index}
                          onClick={() => setSelectedLookIndex(index)}
                          className="h-2 rounded-full transition-all"
                          style={{
                            width: selectedLookIndex === index ? '16px' : '8px',
                            background: selectedLookIndex === index ? 'var(--accent)' : 'rgba(255,255,255,0.4)',
                          }}
                        />
                      ))}
                    </div>
                  )}
                </div>

                {/* Right Column: Look Details */}
                <div className="md:col-span-7 flex flex-col gap-4">
                  <div className="glass-card-elevated p-6 flex flex-col gap-5">
                    <div>
                      <h2 className="text-lg font-bold mb-1" style={{ color: 'var(--text-primary)' }}>Look Details</h2>
                      <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Curated styling insights for today</p>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {/* Styling Tip */}
                      <div className="p-4 rounded-2xl flex items-start gap-3" style={{ background: 'rgba(251, 191, 36, 0.08)', border: '1px solid rgba(251, 191, 36, 0.15)' }}>
                        <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: 'rgba(251, 191, 36, 0.15)' }}>
                          <Sparkles className="w-5 h-5" style={{ color: '#fbbf24' }} />
                        </div>
                        <div>
                          <h4 className="text-xs font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>Styling Tip</h4>
                          <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                            {cleanReasoning(selectedLook.reasoning, selectedLook.style_notes) || 'Great outfit choice!'}
                          </p>
                        </div>
                      </div>

                      {/* Color Match */}
                      <div className="p-4 rounded-2xl flex items-start gap-3" style={{ background: 'rgba(99, 102, 241, 0.08)', border: '1px solid rgba(99, 102, 241, 0.15)' }}>
                        <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: 'rgba(99, 102, 241, 0.15)' }}>
                          <Palette className="w-5 h-5" style={{ color: '#6366f1' }} />
                        </div>
                        <div>
                          <h4 className="text-xs font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>Color Harmony</h4>
                          <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                            {cleanEnumText(selectedLook.color_harmony_notes) || 'Colors work well together'}
                          </p>
                        </div>
                      </div>

                      {/* Style Notes */}
                      <div className="p-4 rounded-2xl flex items-start gap-3 sm:col-span-2" style={{ background: 'rgba(74, 222, 128, 0.08)', border: '1px solid rgba(74, 222, 128, 0.15)' }}>
                        <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: 'rgba(74, 222, 128, 0.15)' }}>
                          <Shirt className="w-5 h-5" style={{ color: '#4ade80' }} />
                        </div>
                        <div>
                          <h4 className="text-xs font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>Style Notes</h4>
                          <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                            {selectedLook.style_notes || 'Casual style'}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* CTA Button */}
                    <button
                      onClick={() => navigate('/dressing-room', { 
                        state: { preselectedGarmentIds: selectedLook.garment_ids } 
                      })}
                      className="btn-primary btn-lg w-full"
                    >
                      <Wand2 className="w-5 h-5" />
                      <span>Customize in Dressing Room</span>
                    </button>
                  </div>
                </div>

              </div>
            )}
          </div>
        )}
      </div>

      {/* Bottom Navigation */}
      <BottomNav />
    </div>
  )
}
