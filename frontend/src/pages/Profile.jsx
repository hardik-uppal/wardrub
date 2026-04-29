import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  ChevronLeft, User, LogOut, AlertCircle, Sparkles, Camera, MapPin
} from 'lucide-react'
import { useWardrobe } from '../context/WardrobeContext'
import { useAuth } from '../context/AuthContext'
import LoadingOverlay from '../components/LoadingOverlay'
import BottomNav from '../components/BottomNav'

const API_URL = import.meta.env.VITE_API_URL || ''

// Color name to hex mapping
const colorNameToHex = {
  'coral': '#FF7F50', 'peach': '#FFCBA4', 'salmon': '#FA8072', 'rose': '#FF007F',
  'blush': '#DE5D83', 'burgundy': '#800020', 'maroon': '#800000', 'cherry': '#DE3163',
  'orange': '#FFA500', 'tangerine': '#FF9966', 'apricot': '#FBCEB1', 'amber': '#FFBF00',
  'gold': '#FFD700', 'golden yellow': '#FFDF00', 'mustard': '#FFDB58', 'lemon': '#FFF44F',
  'yellow': '#FFFF00', 'cream': '#FFFDD0', 'ivory': '#FFFFF0', 'champagne': '#F7E7CE',
  'olive': '#808000', 'sage': '#BCB88A', 'mint': '#98FF98', 'seafoam': '#93E9BE',
  'teal': '#008080', 'emerald': '#50C878', 'forest': '#228B22', 'lime': '#32CD32',
  'green': '#008000', 'warm green': '#76B041', 'jade': '#00A86B',
  'navy': '#000080', 'cobalt': '#0047AB', 'royal blue': '#4169E1', 'sky blue': '#87CEEB',
  'powder blue': '#B0E0E6', 'turquoise': '#40E0D0', 'aqua': '#00FFFF', 'blue': '#0000FF',
  'lavender': '#E6E6FA', 'lilac': '#C8A2C8', 'violet': '#EE82EE', 'purple': '#800080',
  'plum': '#DDA0DD', 'mauve': '#E0B0FF', 'orchid': '#DA70D6',
  'brown': '#A52A2A', 'chocolate': '#D2691E', 'caramel': '#FFD59A', 'tan': '#D2B48C',
  'beige': '#F5F5DC', 'taupe': '#483C32', 'khaki': '#C3B091', 'camel': '#C19A6B',
  'black': '#000000', 'charcoal': '#36454F', 'gray': '#808080', 'grey': '#808080',
  'silver': '#C0C0C0', 'dark gray': '#A9A9A9', 'light gray': '#D3D3D3',
  'white': '#FFFFFF', 'off-white': '#FAF9F6',
  'muted colors': '#A9A9A9', 'muted': '#A9A9A9',
}

const getColorHex = (colorName) => {
  const normalized = colorName.toLowerCase().trim()
  return colorNameToHex[normalized] || '#CCCCCC'
}

const bodyTypeDescriptions = {
  hourglass: 'Balanced shoulders and hips with defined waist',
  pear: 'Hips wider than shoulders, defined waist',
  apple: 'Shoulders wider than hips, less defined waist',
  rectangle: 'Shoulders, waist, and hips similar width',
  inverted_triangle: 'Shoulders notably wider than hips',
}

// Minimal SVG line sketches for clothing
const TopSketch = () => (
  <svg viewBox="0 0 48 48" className="w-12 h-12" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M14 12 L24 8 L34 12 L36 20 L32 20 L32 40 L16 40 L16 20 L12 20 Z" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M20 8 L20 16 L28 16 L28 8" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)

const BottomSketch = () => (
  <svg viewBox="0 0 48 48" className="w-12 h-12" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M14 8 L34 8 L36 12 L32 44 L26 44 L24 24 L22 44 L16 44 L12 12 Z" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)

// Body type silhouettes as minimal line art
const BodyTypeSilhouette = ({ type }) => {
  const paths = {
    hourglass: "M20 8 Q24 8 28 8 Q32 16 28 24 Q24 28 24 28 Q24 28 20 24 Q16 16 20 8 M20 24 Q16 32 18 44 L30 44 Q32 32 28 24",
    pear: "M22 8 Q24 8 26 8 Q28 14 26 20 Q24 22 24 22 Q24 22 22 20 Q20 14 22 8 M22 20 Q16 30 16 44 L32 44 Q32 30 26 20",
    apple: "M18 8 Q24 8 30 8 Q34 16 30 24 Q24 26 24 26 Q24 26 18 24 Q14 16 18 8 M18 24 Q20 32 22 44 L26 44 Q28 32 30 24",
    rectangle: "M20 8 Q24 8 28 8 Q30 14 28 24 Q26 30 26 44 L22 44 Q22 30 20 24 Q18 14 20 8",
    inverted_triangle: "M16 8 Q24 8 32 8 Q34 16 30 24 Q26 28 26 44 L22 44 Q22 28 18 24 Q14 16 16 8",
  }
  
  return (
    <svg viewBox="0 0 48 52" className="w-16 h-20 mx-auto" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d={paths[type] || paths.rectangle} strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

const popularCities = [
  { city: 'London', lat: 51.5074, lon: -0.1278 },
  { city: 'New York', lat: 40.7128, lon: -74.0060 },
  { city: 'Paris', lat: 48.8566, lon: 2.3522 },
  { city: 'Tokyo', lat: 35.6762, lon: 139.6503 },
  { city: 'Sydney', lat: -33.8688, lon: 151.2093 },
]

export default function Profile() {
  const navigate = useNavigate()
  const { avatarUrl } = useWardrobe()
  const { getIdToken, signOut } = useAuth()
  
  const [profile, setProfile] = useState(null)
  const [colorRecs, setColorRecs] = useState(null)
  const [fitRecs, setFitRecs] = useState(null)
  const [error, setError] = useState(null)
  const [location, setLocation] = useState({ city: '', lat: null, lon: null })
  const [isUpdatingLocation, setIsUpdatingLocation] = useState(false)
  const [showLocationPicker, setShowLocationPicker] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState([])

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
    fetchProfile()
  }, [])

  const fetchProfile = async () => {
    try {
      const response = await authFetch(`${API_URL}/api/profile`)
      const data = await response.json()
      
      if (data.profile) {
        setProfile(data.profile)
        if (data.profile.location) {
          setLocation(data.profile.location)
        }
        
        if (data.profile.skin_tone) {
          try {
            const colorRes = await authFetch(`${API_URL}/api/profile/color-recommendations`)
            if (colorRes.ok) {
              const colorData = await colorRes.json()
              setColorRecs(colorData.recommendations)
            }
          } catch (e) {
            console.log('Color recommendations not available')
          }
        }
        
        if (data.profile.body_type) {
          try {
            const fitRes = await authFetch(`${API_URL}/api/profile/fit-recommendations`)
            if (fitRes.ok) {
              const fitData = await fitRes.json()
              setFitRecs(fitData.recommendations)
            }
          } catch (e) {
            console.log('Fit recommendations not available')
          }
        }
      }
    } catch (err) {
      console.error('Failed to fetch profile:', err)
      setError('Failed to load profile')
    }
  }

  const handleLocationSelect = async (selectedLocation) => {
    setIsUpdatingLocation(true)
    setShowLocationPicker(false)
    
    try {
      const response = await authFetch(`${API_URL}/api/profile/location`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(selectedLocation)
      })
      
      if (response.ok) {
        setLocation(selectedLocation)
        await fetchProfile()
      } else {
        setError('Failed to update location')
      }
    } catch (err) {
      console.error('Failed to update location:', err)
      setError('Failed to update location')
    } finally {
      setIsUpdatingLocation(false)
    }
  }

  const handleUseCurrentLocation = () => {
    if (navigator.geolocation) {
      setIsUpdatingLocation(true)
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const newLocation = {
            lat: position.coords.latitude,
            lon: position.coords.longitude,
            city: 'Current Location'
          }
          await handleLocationSelect(newLocation)
        },
        (err) => {
          console.error('Geolocation error:', err)
          setError('Could not get your location')
          setIsUpdatingLocation(false)
        }
      )
    } else {
      setError('Geolocation not supported')
    }
  }

  const handleFileChange = (e) => {
    if (e.target.files) {
      setSelectedFiles(Array.from(e.target.files))
    }
  }

  const handleAnalyzeProfile = async () => {
    if (selectedFiles.length === 0) return
    
    setIsAnalyzing(true)
    setError(null)
    
    try {
      const formData = new FormData()
      selectedFiles.forEach(file => formData.append('files', file))
      
      const response = await authFetch(`${API_URL}/api/profile/analyze`, {
        method: 'POST',
        body: formData
      })
      
      if (response.ok) {
        const data = await response.json()
        setProfile(data.profile)
        setColorRecs(data.color_recommendations)
        setFitRecs(data.fit_recommendations)
        setSelectedFiles([])
      } else {
        const errData = await response.json()
        setError(errData.detail || 'Failed to analyze profile')
      }
    } catch (err) {
      console.error('Profile analysis failed:', err)
      setError('Failed to analyze profile')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const skinTone = profile?.skin_tone
  const bodyType = profile?.body_type
  const analysisQuality = profile?.analysis_quality

  return (
    <div className="min-h-screen bg-[var(--color-cream)] safe-top safe-bottom">
      {isAnalyzing && <LoadingOverlay message="Analyzing your photos..." />}
      
      {/* Error Toast */}
      {error && (
        <div 
          className="fixed top-4 left-4 right-4 z-50 bg-red-500 text-white px-4 py-3 rounded-xl shadow-lg max-w-md mx-auto"
          onClick={() => setError(null)}
        >
          <p className="text-sm">{error}</p>
        </div>
      )}
      
      {/* Header */}
      <div className="page-container">
        <header className="mx-4 mt-4 flex items-center justify-between bg-white rounded-3xl shadow-sm p-6">
          <button 
            onClick={() => navigate('/')}
            className="w-10 h-10 rounded-full bg-[var(--color-cream)] flex items-center justify-center"
          >
            <ChevronLeft className="w-5 h-5 text-[var(--color-charcoal)]" />
          </button>
          
          <h1 className="text-lg font-bold text-[var(--color-charcoal)]">My Profile</h1>
          
          <button
            onClick={async () => {
              await signOut()
              navigate('/login')
            }}
            className="w-10 h-10 rounded-full bg-[var(--color-terracotta)]/10 flex items-center justify-center hover:bg-[var(--color-terracotta)]/20 transition-colors"
            title="Sign out"
          >
            <LogOut className="w-4 h-4 text-[var(--color-terracotta)]" />
          </button>
        </header>
      </div>

      <div className="nav-bottom-spacing space-y-5 page-container mt-5">
        {/* Profile Card - Avatar + Info */}
        <div className="mx-4 bg-white rounded-3xl p-6 shadow-sm text-center">
          {/* Avatar - Centered with Edit Overlay */}
          <div className="flex justify-center mb-4">
            <button 
              onClick={() => navigate('/create-avatar')}
              className="relative group"
            >
              <div className="w-20 h-20 rounded-full overflow-hidden border-2 border-[var(--color-terracotta)] transition-all group-hover:border-[var(--color-terracotta)]/70">
              {avatarUrl ? (
                <img src={avatarUrl} alt="Avatar" className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full bg-[var(--color-blush)]/30 flex items-center justify-center">
                  <User className="w-8 h-8 text-[var(--color-terracotta)]" />
                </div>
              )}
            </div>
              {/* Edit overlay - appears on hover/tap */}
              <div className="absolute inset-0 rounded-full bg-[var(--color-charcoal)]/60 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                <Camera className="w-6 h-6 text-white" />
              </div>
              {/* Small camera badge */}
              <div className="absolute -bottom-1 -right-1 w-7 h-7 rounded-full bg-[var(--color-terracotta)] flex items-center justify-center shadow-md border-2 border-white">
                <Camera className="w-3.5 h-3.5 text-white" />
              </div>
            </button>
          </div>
          <p className="text-xs text-[var(--color-warm-gray)] mb-3">Tap to update avatar</p>
          
          {/* Profile Info */}
          {skinTone ? (
            <div className="mb-5">
              <p className="text-lg font-bold text-[var(--color-charcoal)] capitalize">
                {skinTone.season} Season
              </p>
              <p className="text-sm text-[var(--color-warm-gray)]">
                {skinTone.undertone} • {skinTone.depth}
                {bodyType && ` • ${bodyType.replace('_', ' ')}`}
              </p>
            </div>
          ) : (
            <p className="text-sm text-[var(--color-warm-gray)] mb-5">
              Analyze your style to get personalized recommendations
            </p>
          )}

          {/* Location Display */}
          {location.city && (
            <p className="text-sm text-[var(--color-warm-gray)] mb-5">
              {location.city}
            </p>
          )}
          
          {/* Two Side-by-Side Action Buttons */}
          <div className="grid grid-cols-2 gap-3">
            <label className="cursor-pointer">
              <div className="py-3 px-4 bg-[var(--color-sage)] text-white rounded-xl font-medium text-sm flex items-center justify-center gap-2">
                <Sparkles className="w-4 h-4" />
                <span>{selectedFiles.length > 0 ? `${selectedFiles.length} selected` : 'Analyze Style'}</span>
              </div>
              <input
                type="file"
                accept="image/*"
                multiple
                onChange={handleFileChange}
                className="hidden"
              />
            </label>
            
            <button
              onClick={() => setShowLocationPicker(!showLocationPicker)}
              disabled={isUpdatingLocation}
              className="py-3 px-4 bg-[var(--color-charcoal)] text-white rounded-xl font-medium text-sm flex items-center justify-center gap-2"
            >
              <MapPin className="w-4 h-4" />
              <span>{isUpdatingLocation ? 'Updating...' : 'Update Location'}</span>
            </button>
          </div>
          
          {/* Analyze Button - Only when files selected */}
          {selectedFiles.length > 0 && (
            <button
              onClick={handleAnalyzeProfile}
              disabled={isAnalyzing}
              className="w-full mt-3 py-3 bg-green-500 text-white rounded-xl font-medium text-sm flex items-center justify-center gap-2"
            >
              <Sparkles className="w-4 h-4" />
              <span>Analyze My Style</span>
            </button>
          )}

          {/* Location Picker */}
          {showLocationPicker && (
            <div className="mt-4 p-4 bg-[var(--color-cream)] rounded-xl space-y-3 text-left">
              <div className="flex flex-wrap gap-2 justify-center">
                {popularCities.map((city) => (
                  <button
                    key={city.city}
                    onClick={() => handleLocationSelect(city)}
                    className={`px-4 py-2 text-sm rounded-xl transition-colors ${
                      location.city === city.city
                        ? 'bg-[var(--color-terracotta)] text-white'
                        : 'bg-white text-[var(--color-charcoal)]'
                    }`}
                  >
                    {city.city}
                  </button>
                ))}
              </div>
              <button
                onClick={handleUseCurrentLocation}
                className="w-full py-2.5 text-sm text-[var(--color-terracotta)] font-medium border border-[var(--color-terracotta)]/30 rounded-xl"
              >
                Use My Current Location
              </button>
            </div>
          )}
          
          {/* Quality feedback */}
          {analysisQuality?.needs_more_images && (
            <div className="mt-4 p-3 bg-amber-50 rounded-xl flex items-center justify-center gap-2">
              <AlertCircle className="w-4 h-4 text-amber-600" />
              <p className="text-xs text-amber-800">
                {analysisQuality.recommendation || 'Add more photos for better results'}
              </p>
            </div>
          )}
        </div>

        {/* Best Colors - Only show if analyzed */}
        {colorRecs?.best && colorRecs.best.length > 0 && (
          <div className="mx-4 bg-white rounded-3xl p-6 shadow-sm text-center">
            <h2 className="font-bold text-[var(--color-charcoal)] text-base mb-4">Best Colors</h2>
            <div className="flex gap-3 justify-center flex-wrap">
              {colorRecs.best.slice(0, 6).map((color, i) => (
                <div key={i} className="flex flex-col items-center gap-1.5">
                  <div
                    className="w-11 h-11 rounded-full shadow-sm border border-gray-100"
                    style={{ backgroundColor: getColorHex(color) }}
                  />
                  <span className="text-xs text-[var(--color-warm-gray)] capitalize">{color}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Colors to Avoid - Only show if analyzed */}
        {colorRecs?.avoid && colorRecs.avoid.length > 0 && (
          <div className="mx-4 bg-white rounded-3xl p-6 shadow-sm text-center">
            <h2 className="font-bold text-[var(--color-charcoal)] text-base mb-4">Colors to Avoid</h2>
            <div className="flex gap-3 justify-center flex-wrap">
              {colorRecs.avoid.slice(0, 6).map((color, i) => (
                <div key={i} className="flex flex-col items-center gap-1.5">
                  <div
                    className="w-11 h-11 rounded-full shadow-sm border border-gray-100 relative overflow-hidden"
                    style={{ backgroundColor: getColorHex(color) }}
                  >
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="w-full h-0.5 bg-red-500/70 rotate-45" />
                    </div>
                  </div>
                  <span className="text-xs text-[var(--color-warm-gray)] capitalize">{color}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Body Type & Fit - Only show if analyzed */}
        {bodyType && (
          <div className="mx-4 bg-white rounded-3xl p-6 shadow-sm text-center">
            <h2 className="font-bold text-[var(--color-charcoal)] text-base mb-2 capitalize">
              {bodyType.replace('_', ' ')} Body Type
            </h2>
            
            {/* Body Silhouette - Minimal Line Art */}
            <div className="text-[var(--color-warm-gray)] mb-3 flex justify-center">
              <BodyTypeSilhouette type={bodyType} />
            </div>
            
            <p className="text-sm text-[var(--color-warm-gray)] mb-5">
              {bodyTypeDescriptions[bodyType]}
            </p>
            
            {fitRecs && (
              <div className="grid grid-cols-2 gap-4">
                {/* Tops */}
                {fitRecs.tops && fitRecs.tops.length > 0 && (
                  <div className="p-4 bg-[var(--color-cream)] rounded-2xl">
                    <div className="text-[var(--color-terracotta)] mb-2 flex justify-center">
                      <TopSketch />
                    </div>
                    <p className="text-sm font-semibold text-[var(--color-charcoal)] mb-2">Tops</p>
                    <div className="space-y-1.5">
                      {fitRecs.tops.slice(0, 3).map((item, i) => (
                        <p key={i} className="text-xs text-[var(--color-warm-gray)]">{item}</p>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Bottoms */}
                {fitRecs.bottoms && fitRecs.bottoms.length > 0 && (
                  <div className="p-4 bg-[var(--color-cream)] rounded-2xl">
                    <div className="text-[var(--color-terracotta)] mb-2 flex justify-center">
                      <BottomSketch />
                    </div>
                    <p className="text-sm font-semibold text-[var(--color-charcoal)] mb-2">Bottoms</p>
                    <div className="space-y-1.5">
                      {fitRecs.bottoms.slice(0, 3).map((item, i) => (
                        <p key={i} className="text-xs text-[var(--color-warm-gray)]">{item}</p>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
            
            {fitRecs?.notes && (
              <p className="mt-4 text-sm text-[var(--color-terracotta)] italic">
                {fitRecs.notes}
              </p>
            )}
          </div>
        )}
      </div>
      
      <BottomNav />
    </div>
  )
}
