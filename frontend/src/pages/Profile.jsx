import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  ChevronLeft, User, LogOut, AlertCircle, Sparkles, Camera, MapPin
} from 'lucide-react'
import { useWardrobe } from '../context/WardrobeContext'
import { useAuth } from '../context/AuthContext'
import { useOnboarding } from '../context/OnboardingContext'
import LoadingOverlay from '../components/LoadingOverlay'
import OnboardingTooltip from '../components/OnboardingTooltip'
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
  const { avatarUrl, checkLegacyData, migrateLegacyData } = useWardrobe()
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
  const [hasLegacyData, setHasLegacyData] = useState(false)
  const [isMigrating, setIsMigrating] = useState(false)
  const [migrationSuccess, setMigrationSuccess] = useState(false)

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

  const fetchProfile = useCallback(async () => {
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
          } catch {
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
          } catch {
            console.log('Fit recommendations not available')
          }
        }
      }
    } catch (err) {
      console.error('Failed to fetch profile:', err)
      setError('Failed to load profile')
    }
  }, [authFetch])

  useEffect(() => {
    fetchProfile()
    
    // Check for legacy data
    if (checkLegacyData) {
      checkLegacyData().then(hasLegacy => {
        setHasLegacyData(hasLegacy)
      }).catch(err => {
        console.error('Failed to check legacy data:', err)
      })
    }
  }, [fetchProfile, checkLegacyData])

  const handleMigrateData = async () => {
    if (!migrateLegacyData) return
    setIsMigrating(true)
    setError(null)
    try {
      await migrateLegacyData()
      setMigrationSuccess(true)
      setHasLegacyData(false)
      await fetchProfile()
    } catch (err) {
      console.error('Migration failed:', err)
      setError(err.message || 'Failed to migrate old data')
    } finally {
      setIsMigrating(false)
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
    <div className="min-h-screen safe-top safe-bottom" style={{ background: 'var(--bg-primary)' }}>
      {isAnalyzing && <LoadingOverlay message="Analyzing your photos..." />}
      {isMigrating && <LoadingOverlay message="Migrating your previous data..." />}
      
      {/* Error Toast */}
      {error && (
        <div 
          className="fixed top-4 left-4 right-4 z-50 px-4 py-3 rounded-xl shadow-lg max-w-md mx-auto cursor-pointer"
          style={{ background: 'var(--error)', color: 'white' }}
          onClick={() => setError(null)}
        >
          <p className="text-sm">{error}</p>
        </div>
      )}
      
      {/* Header */}
      <div className="page-container">
        <header className="mx-4 mt-4 glass-card-static flex items-center justify-between p-5">
          <button 
            onClick={() => navigate('/')}
            className="w-10 h-10 rounded-full flex items-center justify-center"
            style={{ background: 'var(--glass-bg)' }}
          >
            <ChevronLeft className="w-5 h-5" style={{ color: 'var(--text-primary)' }} />
          </button>
          
          <h1 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>My Profile</h1>
          
          <button
            onClick={async () => {
              await signOut()
              navigate('/login')
            }}
            className="w-10 h-10 rounded-full flex items-center justify-center transition-colors"
            style={{ background: 'rgba(248, 113, 113, 0.1)' }}
            title="Sign out"
          >
            <LogOut className="w-4 h-4" style={{ color: 'var(--error)' }} />
          </button>
        </header>
      </div>

      {/* Legacy Data Migration Banner */}
      {hasLegacyData && (
        <div className="page-container mt-4 px-4">
          <div className="glass-card-elevated p-5 flex flex-col md:flex-row items-center justify-between gap-4 border border-amber-500/20" style={{ background: 'rgba(245, 158, 11, 0.05)', borderRadius: '16px' }}>
            <div className="flex items-center gap-3">
              <Sparkles className="w-6 h-6 text-amber-400 shrink-0 animate-pulse" />
              <div className="text-left">
                <h3 className="font-bold text-sm" style={{ color: 'var(--text-primary)' }}>Previous Session Data Found</h3>
                <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                  We found wardrobe items and analysis from a previous session. Would you like to import them to your account?
                </p>
              </div>
            </div>
            <button
              onClick={handleMigrateData}
              disabled={isMigrating}
              className="btn-primary py-2.5 px-5 whitespace-nowrap shrink-0"
              style={{ background: 'var(--accent)' }}
            >
              Import Data
            </button>
          </div>
        </div>
      )}

      {migrationSuccess && (
        <div className="page-container mt-4 px-4">
          <div className="glass-card-elevated p-4 flex items-center gap-3 border border-green-500/20" style={{ background: 'rgba(16, 185, 129, 0.05)', borderRadius: '16px' }}>
            <Sparkles className="w-5 h-5 text-green-400 shrink-0" />
            <div className="text-left flex-1">
              <p className="text-xs font-semibold" style={{ color: '#34d399' }}>
                Successfully imported previous wardrobe items and profile settings!
              </p>
            </div>
            <button className="text-xs" style={{ color: 'var(--text-secondary)' }} onClick={() => setMigrationSuccess(false)}>Dismiss</button>
          </div>
        </div>
      )}

      <div className="nav-bottom-spacing page-container mt-5 max-w-5xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
          
          {/* Left Column - Avatar + Info + Location Picker */}
          <div className="md:col-span-5 lg:col-span-4 flex flex-col gap-5">
            <div className="mx-4 md:mx-0 glass-card-elevated p-6 text-center">
              {/* Avatar */}
              <div className="flex justify-center mb-4">
                <button 
                  onClick={() => navigate('/create-avatar')}
                  className="relative group"
                >
                  <div
                    className="w-24 h-24 rounded-full overflow-hidden transition-all"
                    style={{
                      border: '1px solid var(--accent)',
                    }}
                  >
                    {avatarUrl ? (
                      <img 
                        src={avatarUrl} 
                        alt="Avatar" 
                        className="w-full h-full object-cover" 
                        style={{ objectPosition: 'top center' }}
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center" style={{ background: 'var(--glass-bg)' }}>
                        <User className="w-10 h-10" style={{ color: 'var(--accent)' }} />
                      </div>
                    )}
                  </div>
                  {/* Edit overlay */}
                  <div className="absolute inset-0 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity" style={{ background: 'rgba(0,0,0,0.6)' }}>
                    <Camera className="w-6 h-6" style={{ color: 'var(--text-primary)' }} />
                  </div>
                  {/* Camera badge */}
                  <div
                    className="absolute -bottom-1 -right-1 w-7 h-7 rounded-full flex items-center justify-center"
                    style={{ background: 'var(--accent)', boxShadow: '0 0 8px var(--accent-glow)' }}
                  >
                    <Camera className="w-3.5 h-3.5 text-white" />
                  </div>
                </button>
              </div>
              <p className="text-xs mb-3" style={{ color: 'var(--text-tertiary)' }}>Tap to update avatar</p>
              
              {/* Profile Info */}
              {skinTone ? (
                <div className="mb-5">
                  <h2 className="text-lg font-bold capitalize" style={{ color: 'var(--text-primary)' }}>
                    {skinTone.season} Season
                  </h2>
                  <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                    {skinTone.undertone} • {skinTone.depth}
                    {bodyType && ` • ${bodyType.replace('_', ' ')}`}
                  </p>
                </div>
              ) : (
                <p className="text-sm mb-5" style={{ color: 'var(--text-secondary)' }}>
                  Analyze your style to get personalized recommendations
                </p>
              )}

              {/* Location Display */}
              {location.city && (
                <p className="text-sm mb-5" style={{ color: 'var(--text-secondary)' }}>
                  📍 {location.city}
                </p>
              )}
              
              {/* Action Buttons — stacked to avoid truncation */}
              <div className="flex flex-col gap-3">
                <label className="cursor-pointer">
                  <div className="btn-primary w-full">
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
                  className="btn-ghost w-full"
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
                  className="w-full mt-3 py-3 rounded-xl font-medium text-sm flex items-center justify-center gap-2"
                  style={{ background: 'rgba(74, 222, 128, 0.2)', color: '#4ade80', border: '1px solid rgba(74, 222, 128, 0.3)' }}
                >
                  <Sparkles className="w-4 h-4" />
                  <span>Analyze My Style</span>
                </button>
              )}

              {/* Location Picker */}
              {showLocationPicker && (
                <div className="mt-4 p-4 rounded-xl space-y-3 text-left" style={{ background: 'var(--glass-bg)', border: '1px solid var(--glass-border)' }}>
                  <div className="flex flex-wrap gap-2 justify-center">
                    {popularCities.map((city) => (
                      <button
                        key={city.city}
                        onClick={() => handleLocationSelect(city)}
                        className="px-4 py-2 text-sm rounded-xl transition-colors"
                        style={{
                          background: location.city === city.city ? 'var(--accent)' : 'var(--glass-bg-hover)',
                          color: location.city === city.city ? 'white' : 'var(--text-secondary)',
                          border: '1px solid var(--glass-border)',
                        }}
                      >
                        {city.city}
                      </button>
                    ))}
                  </div>
                  <button
                    onClick={handleUseCurrentLocation}
                    className="w-full py-2.5 text-sm font-medium rounded-xl"
                    style={{ color: 'var(--accent)', border: '1px solid var(--accent)', background: 'transparent' }}
                  >
                    Use My Current Location
                  </button>
                </div>
              )}
              
              {/* Quality feedback */}
              {analysisQuality?.needs_more_images && (
                <div className="mt-4 p-3 rounded-xl flex items-center justify-center gap-2" style={{ background: 'rgba(251, 191, 36, 0.1)', border: '1px solid rgba(251, 191, 36, 0.2)' }}>
                  <AlertCircle className="w-4 h-4" style={{ color: '#fbbf24' }} />
                  <p className="text-xs" style={{ color: '#fbbf24' }}>
                    {analysisQuality.recommendation || 'Add more photos for better results'}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Right Column - Styling Recommendations */}
          <div className="md:col-span-7 lg:col-span-8 flex flex-col gap-5">
            
            {/* Onboarding tooltip for style analysis */}
            {!colorRecs && !bodyType && (
              <div className="mx-4 md:mx-0 mb-4">
                <OnboardingTooltip
                  id="profile-analyze-style"
                  message="Upload a few photos of yourself to discover your best colors, season type, and body shape — so we can recommend outfits that truly suit you."
                  cta="Upload photos above"
                  onCtaClick={() => {}}
                  position="bottom"
                />
              </div>
            )}

            {/* CTA State if profile is not analyzed */}
            {!colorRecs && !bodyType && (
              <div className="mx-4 md:mx-0 glass-card-elevated p-8 text-center flex flex-col items-center justify-center min-h-[300px]">
                <div
                  className="w-20 h-20 rounded-2xl flex items-center justify-center mb-5"
                  style={{ background: 'var(--accent-glow)' }}
                >
                  <Sparkles className="w-10 h-10" style={{ color: 'var(--accent-light)' }} />
                </div>
                <h3 className="text-lg font-bold mb-2" style={{ color: 'var(--text-primary)' }}>Style Analysis</h3>
                <p className="text-sm max-w-sm" style={{ color: 'var(--text-secondary)' }}>
                  Upload photos of yourself to analyze your season colors, undertones, and body silhouette for personalized fit advice.
                </p>
              </div>
            )}

            {/* Best Colors */}
            {colorRecs?.best && colorRecs.best.length > 0 && (
              <div className="mx-4 md:mx-0 glass-card-elevated p-6">
                <h2 className="font-bold text-base mb-5 text-center" style={{ color: 'var(--text-primary)' }}>Best Colors</h2>
                <div className="flex gap-4 justify-center flex-wrap">
                  {colorRecs.best.slice(0, 6).map((color, i) => (
                    <div key={i} className="flex flex-col items-center gap-2">
                      <div
                        className="color-swatch"
                        style={{ backgroundColor: getColorHex(color) }}
                      />
                      <span className="text-xs capitalize" style={{ color: 'var(--text-secondary)' }}>{color}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Colors to Avoid */}
            {colorRecs?.avoid && colorRecs.avoid.length > 0 && (
              <div className="mx-4 md:mx-0 glass-card-elevated p-6">
                <h2 className="font-bold text-base mb-5 text-center" style={{ color: 'var(--text-primary)' }}>Colors to Avoid</h2>
                <div className="flex gap-4 justify-center flex-wrap">
                  {colorRecs.avoid.slice(0, 6).map((color, i) => (
                    <div key={i} className="flex flex-col items-center gap-2">
                      <div
                        className="color-swatch relative overflow-hidden"
                        style={{ backgroundColor: getColorHex(color) }}
                      >
                        <div className="absolute inset-0 flex items-center justify-center">
                          <div className="w-full h-0.5 rotate-45" style={{ background: 'rgba(248, 113, 113, 0.7)' }} />
                        </div>
                      </div>
                      <span className="text-xs capitalize" style={{ color: 'var(--text-secondary)' }}>{color}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Body Type & Fit */}
            {bodyType && (
              <div className="mx-4 md:mx-0 glass-card-elevated p-6 text-center">
                <h2 className="font-bold text-base mb-2 capitalize" style={{ color: 'var(--text-primary)' }}>
                  {bodyType.replace('_', ' ')} Body Type
                </h2>
                
                <div className="mb-3 flex justify-center" style={{ color: 'var(--text-tertiary)' }}>
                  <BodyTypeSilhouette type={bodyType} />
                </div>
                
                <p className="text-sm mb-5" style={{ color: 'var(--text-secondary)' }}>
                  {bodyTypeDescriptions[bodyType]}
                </p>
                
                {fitRecs && (
                  <div className="grid grid-cols-2 gap-4 md:gap-5">
                    {/* Tops */}
                    {fitRecs.tops && fitRecs.tops.length > 0 && (
                      <div className="p-4 rounded-2xl" style={{ background: 'var(--glass-bg)', border: '1px solid var(--glass-border)' }}>
                        <div className="mb-2 flex justify-center" style={{ color: 'var(--accent)' }}>
                          <TopSketch />
                        </div>
                        <h4 className="text-sm font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>Tops</h4>
                        <div className="space-y-1.5">
                          {fitRecs.tops.slice(0, 3).map((item, i) => (
                            <p key={i} className="text-xs" style={{ color: 'var(--text-secondary)' }}>{item}</p>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Bottoms */}
                    {fitRecs.bottoms && fitRecs.bottoms.length > 0 && (
                      <div className="p-4 rounded-2xl" style={{ background: 'var(--glass-bg)', border: '1px solid var(--glass-border)' }}>
                        <div className="mb-2 flex justify-center" style={{ color: 'var(--accent)' }}>
                          <BottomSketch />
                        </div>
                        <h4 className="text-sm font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>Bottoms</h4>
                        <div className="space-y-1.5">
                          {fitRecs.bottoms.slice(0, 3).map((item, i) => (
                            <p key={i} className="text-xs" style={{ color: 'var(--text-secondary)' }}>{item}</p>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
                
                {fitRecs?.notes && (
                  <p className="mt-4 text-sm italic" style={{ color: 'var(--accent-light)' }}>
                    {fitRecs.notes}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
      
      <BottomNav />
    </div>
  )
}
