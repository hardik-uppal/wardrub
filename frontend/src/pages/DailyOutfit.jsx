import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Sun, Cloud, CloudRain, Snowflake, Thermometer,
  Sparkles, RefreshCw, Shirt, User, Wind, CloudFog, CloudLightning,
  Palette, Calendar, ChevronLeft, ChevronRight, Wand2
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
  const { avatarUrl, garments, isLoading: contextLoading, fetchGarments } = useWardrobe()
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

  useEffect(() => {
    fetchDailyLooks()
    fetchGarments()
    fetchDayForecast()
  }, [])

  const fetchDayForecast = async () => {
    try {
      const response = await authFetch(`${API_URL}/api/weather/forecast`)
      const data = await response.json()
      if (data.status === 'success' && data.forecast) {
        setDayForecast(data.forecast)
      }
    } catch (err) {
      console.error('Failed to fetch day forecast:', err)
    }
  }

  const fetchDailyLooks = async () => {
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
  }

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
    // Replace patterns like "ColorSeason.SPRING" with "Spring"
    return text.replace(/(\w+)\.(\w+)/g, (match, prefix, value) => {
      return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase()
    })
  }

  // Remove duplicate style text from reasoning (if style_notes appears in reasoning)
  const cleanReasoning = (reasoning, styleNotes) => {
    if (!reasoning || !styleNotes) return reasoning
    // Remove the style notes portion from reasoning to avoid duplication
    return reasoning
      .replace(`. ${styleNotes}`, '')
      .replace(styleNotes, '')
      .replace(/\.\s*$/, '') // Remove trailing period
      .trim() || 'Great outfit for today'
  }

  const today = new Date()
  const dateStr = today.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#FDF6E3] via-[#FFF8E7] to-[#F5E6D3] safe-top safe-bottom flex flex-col">
      {/* Only show full overlay for regeneration (which takes longer) */}
      {isRegenerating && (
        <LoadingOverlay message="Creating new looks..." />
      )}
      
      {/* Header Card */}
      <div className="page-container">
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
            Today's Looks
          </h1>
          <div className="flex items-center justify-center gap-1.5 mt-1">
            <Calendar className="w-3.5 h-3.5 text-[var(--color-warm-gray)]" />
            <p className="text-sm text-[var(--color-warm-gray)]">{dateStr}</p>
          </div>
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
      </div>

      {/* Main Content - Scrollable */}
      <div className="flex-1 overflow-y-auto page-container space-y-6 mt-6" style={{ paddingBottom: '180px' }}>
        {/* Weather Card */}
        {(weather || dayForecast) && (
          <div className="mx-4 px-6 py-4 bg-white rounded-3xl shadow-sm">
            {/* Day Weather Forecast - Single row layout */}
            {dayForecast && dayForecast.length > 0 ? (
              <div className="flex items-center justify-center gap-6">
                {dayForecast.map((forecast, index) => {
                  const IconComponent = getWeatherIcon(forecast.icon)
                  const bgColors = [
                    'from-amber-100 to-yellow-200',
                    'from-orange-100 to-amber-200', 
                    'from-rose-100 to-orange-200',
                    'from-indigo-100 to-slate-200'
                  ]
                  const iconColors = ['text-amber-600', 'text-orange-600', 'text-rose-500', 'text-indigo-500']
                  
                  return (
                    <div key={forecast.time_label} className="flex items-center gap-2">
                      {/* Icon */}
                      <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${bgColors[index]} flex items-center justify-center relative flex-shrink-0`}>
                        <IconComponent className={`w-6 h-6 ${iconColors[index]}`} />
                        {forecast.is_windy && (
                          <div className="absolute -top-1 -right-1 w-4 h-4 bg-white rounded-full flex items-center justify-center shadow-sm">
                            <Wind className="w-2.5 h-2.5 text-gray-600" />
                          </div>
                        )}
                      </div>
                      {/* Text beside icon */}
                      <div className="flex flex-col">
                        <span className="text-sm font-bold text-[var(--color-charcoal)]">
                          {forecast.temp}°
                        </span>
                        <span className="text-[10px] text-[var(--color-warm-gray)] font-medium">
                          {forecast.time_label}
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : weather && (
              /* Fallback to current weather only */
              <div className="flex items-center justify-center gap-6">
                {['Morn', 'Noon', 'Eve', 'Night'].map((label, index) => {
                  const bgColors = ['from-amber-100 to-yellow-200', 'from-orange-100 to-amber-200', 'from-rose-100 to-orange-200', 'from-indigo-100 to-slate-200']
                  const iconColors = ['text-amber-600', 'text-orange-600', 'text-rose-500', 'text-indigo-500']
                  const icons = [Sun, WeatherIcon, Cloud, Cloud]
                  const Icon = icons[index]
                  return (
                    <div key={label} className="flex items-center gap-2">
                      <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${bgColors[index]} flex items-center justify-center flex-shrink-0`}>
                        <Icon className={`w-6 h-6 ${iconColors[index]}`} />
                      </div>
                      <div className="flex flex-col">
                        <span className="text-sm font-bold text-[var(--color-charcoal)]">
                          {weather.temp ? `${Math.round(weather.temp)}°` : '--°'}
                        </span>
                        <span className="text-[10px] text-[var(--color-warm-gray)] font-medium">{label}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {/* Initial Loading - Subtle skeleton */}
        {isLoading && !dailyLooks && (
          <div className="mx-4 bg-white rounded-3xl overflow-hidden shadow-sm animate-pulse">
            <div className="aspect-[3/4] bg-gray-200" />
            <div className="p-5 space-y-4">
              <div className="h-20 bg-gray-100 rounded-xl" />
              <div className="h-12 bg-gray-100 rounded-xl" />
            </div>
          </div>
        )}

        {/* Error States */}
        {error === 'no_looks' && !isLoading && (
          <div className="mx-4 bg-white rounded-3xl shadow-sm p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-amber-100 flex items-center justify-center">
              <Sparkles className="w-8 h-8 text-amber-600" />
            </div>
            <h3 className="text-lg font-bold text-[var(--color-charcoal)] mb-2">
              No looks generated yet
            </h3>
            <p className="text-sm text-[var(--color-warm-gray)] mb-4">
              Daily looks are generated automatically at 6 AM, or you can create them now.
            </p>
            {!avatarUrl ? (
              <button
                onClick={() => navigate('/create-avatar')}
                className="px-6 py-3 bg-[var(--color-terracotta)] text-white rounded-xl font-medium text-sm"
              >
                Create Your Profile First
              </button>
            ) : garments.length < 2 ? (
              <button
                onClick={() => navigate('/capture')}
                className="px-6 py-3 bg-[var(--color-terracotta)] text-white rounded-xl font-medium text-sm"
              >
                Add More Clothes
              </button>
            ) : (
              <button
                onClick={handleRegenerate}
                className="px-6 py-3 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-xl font-medium text-sm flex items-center gap-2 mx-auto"
              >
                <Sparkles className="w-4 h-4" />
                Generate Today's Looks
              </button>
            )}
          </div>
        )}

        {error === 'failed' && !isLoading && (
          <div className="mx-4 bg-white rounded-3xl shadow-sm p-8 text-center">
            <p className="text-[var(--color-charcoal)] font-medium mb-4">
              Failed to load recommendations
            </p>
            <button
              onClick={fetchDailyLooks}
              className="px-6 py-2 bg-[var(--color-charcoal)] text-white rounded-full text-sm font-medium"
            >
              Try Again
            </button>
          </div>
        )}

        {/* Daily Looks Content */}
        {dailyLooks && dailyLooks.looks && dailyLooks.looks.length > 0 && (
          <div className="mx-4">
            {/* Selected Look Card */}
            {selectedLook && (
              <div className="bg-white rounded-3xl overflow-hidden shadow-sm">
                {/* Try-on Image with Navigation */}
                <div className="aspect-[3/4] bg-gradient-to-br from-gray-50 to-gray-100 relative">
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
                        className="absolute left-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-white/90 shadow-md flex items-center justify-center hover:bg-white transition-colors"
                      >
                        <ChevronLeft className="w-5 h-5 text-[var(--color-charcoal)]" />
                      </button>
                      <button
                        onClick={() => setSelectedLookIndex(prev => prev === dailyLooks.looks.length - 1 ? 0 : prev + 1)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-white/90 shadow-md flex items-center justify-center hover:bg-white transition-colors"
                      >
                        <ChevronRight className="w-5 h-5 text-[var(--color-charcoal)]" />
                      </button>
                    </>
                  )}
                  
                  {/* Score Badge */}
                  <div className="absolute top-4 right-4 h-12 px-7 bg-white/95 rounded-full shadow-sm flex items-center justify-center">
                    <span className="text-sm font-semibold text-green-600">
                      {Math.round(selectedLook.score * 100)}% Match
                    </span>
                  </div>
                  
                  {/* Look Number */}
                  <div className="absolute top-4 left-4 h-12 px-7 bg-[var(--color-charcoal)]/80 rounded-full flex items-center justify-center">
                    <span className="text-sm font-medium text-white">
                      Look {selectedLookIndex + 1} of {dailyLooks.looks.length}
                    </span>
                  </div>
                  
                  {/* Dots Indicator at bottom of image */}
                  {dailyLooks.looks.length > 1 && (
                    <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1.5 bg-black/30 px-3 py-1.5 rounded-full">
                      {dailyLooks.looks.map((_, index) => (
                        <button
                          key={index}
                          onClick={() => setSelectedLookIndex(index)}
                          className={`w-2 h-2 rounded-full transition-all ${
                            selectedLookIndex === index
                              ? 'bg-white w-4'
                              : 'bg-white/50'
                          }`}
                        />
                      ))}
                    </div>
                  )}
                </div>

                {/* Look Details - 2x2 Grid */}
                <div className="p-4">
                  <div className="grid grid-cols-2 gap-3">
                    {/* Styling Tip */}
                    <div className="p-4 bg-amber-50/70 rounded-2xl flex items-center justify-center min-h-[88px]">
                      <div className="flex items-start gap-2.5 max-w-[140px]">
                        <div className="w-9 h-9 rounded-lg bg-amber-100 flex items-center justify-center flex-shrink-0">
                          <Sparkles className="w-4 h-4 text-amber-600" />
                        </div>
                        <p className="text-[11px] text-[var(--color-charcoal)] leading-[1.4] pt-0.5" style={{ wordBreak: 'break-word' }}>
                          {cleanReasoning(selectedLook.reasoning, selectedLook.style_notes) || 'Great outfit choice!'}
                        </p>
                      </div>
                    </div>

                    {/* Color Match */}
                    <div className="p-4 bg-blue-50/70 rounded-2xl flex items-center justify-center min-h-[88px]">
                      <div className="flex items-start gap-2.5 max-w-[140px]">
                        <div className="w-9 h-9 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0">
                          <Palette className="w-4 h-4 text-blue-600" />
                        </div>
                        <p className="text-[11px] text-[var(--color-charcoal)] leading-[1.4] pt-0.5" style={{ wordBreak: 'break-word' }}>
                          {cleanEnumText(selectedLook.color_harmony_notes) || 'Colors work well together'}
                        </p>
                      </div>
                    </div>

                    {/* Style Notes */}
                    <div className="p-4 bg-green-50/70 rounded-2xl flex items-center justify-center min-h-[88px]">
                      <div className="flex items-start gap-2.5 max-w-[140px]">
                        <div className="w-9 h-9 rounded-lg bg-green-100 flex items-center justify-center flex-shrink-0">
                          <Shirt className="w-4 h-4 text-green-600" />
                        </div>
                        <p className="text-[11px] text-[var(--color-charcoal)] leading-[1.4] pt-0.5" style={{ wordBreak: 'break-word' }}>
                          {selectedLook.style_notes || 'Casual style'}
                        </p>
                      </div>
                    </div>

                    {/* Play Around with this Look */}
                    <button
                      onClick={() => navigate('/dressing-room', { 
                        state: { preselectedGarmentIds: selectedLook.garment_ids } 
                      })}
                      className="p-4 bg-[var(--color-terracotta)]/10 rounded-2xl flex items-center justify-center min-h-[88px] hover:bg-[var(--color-terracotta)]/20 transition-colors active:scale-95 transition-transform"
                    >
                      <div className="flex items-start gap-2.5 max-w-[140px]">
                        <div className="w-9 h-9 rounded-lg bg-[var(--color-terracotta)] flex items-center justify-center flex-shrink-0">
                          <Wand2 className="w-4 h-4 text-white" />
                        </div>
                        <p className="text-[11px] text-[var(--color-terracotta)] font-semibold leading-[1.4] pt-0.5">
                          Play around
                        </p>
                      </div>
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
