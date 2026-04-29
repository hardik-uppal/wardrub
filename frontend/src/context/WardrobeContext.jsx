import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
import { useAuth } from './AuthContext'

const API_URL = import.meta.env.VITE_API_URL || ''

// Cache TTL in milliseconds (5 minutes)
const CACHE_TTL = 5 * 60 * 1000

const WardrobeContext = createContext(null)

export function WardrobeProvider({ children }) {
  const { getIdToken, user } = useAuth()
  
  const [avatarUrl, setAvatarUrl] = useState(null)
  const [garments, setGarments] = useState([])
  const [looks, setLooks] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [loadingMessage, setLoadingMessage] = useState('')
  const [error, setError] = useState(null)
  const [userProfile, setUserProfile] = useState(null)
  
  // Cache timestamps to prevent duplicate fetches
  const cacheTimestamps = useRef({
    avatar: 0,
    garments: 0,
    looks: 0,
    profile: 0
  })
  
  // Check if cache is still valid
  const isCacheValid = (key) => {
    return Date.now() - cacheTimestamps.current[key] < CACHE_TTL
  }
  
  // Invalidate specific cache
  const invalidateCache = (key) => {
    cacheTimestamps.current[key] = 0
  }

  // Helper to make authenticated fetch requests
  const authFetch = useCallback(async (url, options = {}) => {
    const token = await getIdToken()
    
    if (!token) {
      throw new Error('Not authenticated')
    }

    const headers = {
      ...options.headers,
      'Authorization': `Bearer ${token}`,
    }

    const response = await fetch(url, { ...options, headers })

    // Handle 401 - token might be expired
    if (response.status === 401) {
      throw new Error('Authentication expired. Please sign in again.')
    }

    return response
  }, [getIdToken])

  // Fetch avatar when user changes
  useEffect(() => {
    if (user) {
      fetchAvatar()
    } else {
      // Clear data on logout
      setAvatarUrl(null)
      setGarments([])
      setLooks([])
      setUserProfile(null)
      // Reset all cache timestamps
      cacheTimestamps.current = {
        avatar: 0,
        garments: 0,
        looks: 0,
        profile: 0
      }
    }
  }, [user])

  const fetchAvatar = useCallback(async (force = false) => {
    // Skip if cache is valid and not forced
    if (!force && isCacheValid('avatar') && avatarUrl) {
      return
    }
    
    try {
      const response = await authFetch(`${API_URL}/api/avatar`)
      const data = await response.json()
      if (data.avatar_url) {
        setAvatarUrl(data.avatar_url)
        cacheTimestamps.current.avatar = Date.now()
      }
    } catch (err) {
      console.error('Failed to fetch avatar:', err)
    }
  }, [authFetch, avatarUrl])

  const fetchGarments = useCallback(async (category = null, force = false) => {
    // Skip if cache is valid and not forced (only for "all" category)
    if (!force && !category && isCacheValid('garments') && garments.length > 0) {
      return
    }
    
    try {
      const url = category 
        ? `${API_URL}/api/wardrobe?category=${category}`
        : `${API_URL}/api/wardrobe`
      const response = await authFetch(url)
      const data = await response.json()
      setGarments(data.garments || [])
      if (!category) {
        cacheTimestamps.current.garments = Date.now()
      }
    } catch (err) {
      console.error('Failed to fetch garments:', err)
      setError('Failed to load wardrobe')
    }
  }, [authFetch, garments.length])

  const fetchLooks = useCallback(async (force = false) => {
    // Skip if cache is valid and not forced
    if (!force && isCacheValid('looks') && looks.length > 0) {
      return
    }
    
    try {
      const response = await authFetch(`${API_URL}/api/try-on/history`)
      const data = await response.json()
      setLooks(data.results || [])
      cacheTimestamps.current.looks = Date.now()
    } catch (err) {
      console.error('Failed to fetch looks:', err)
    }
  }, [authFetch, looks.length])

  const processGarment = async (frontFile, backFile, category, ghostMannequin = true) => {
    setIsLoading(true)
    setLoadingMessage('Analyzing your garment...')
    setError(null)

    try {
      const formData = new FormData()
      formData.append('front', frontFile)
      if (backFile) {
        formData.append('back', backFile)
      }
      formData.append('category', category)
      formData.append('ghost_mannequin', ghostMannequin)

      // Progress messages
      setTimeout(() => setLoadingMessage('Removing background...'), 2000)
      if (ghostMannequin) {
        setTimeout(() => setLoadingMessage('Creating ghost mannequin effect...'), 4000)
        setTimeout(() => setLoadingMessage('AI is shaping your garment...'), 8000)
        setTimeout(() => setLoadingMessage('Almost ready...'), 15000)
      } else {
        setTimeout(() => setLoadingMessage('Processing...'), 4000)
      }

      const response = await authFetch(`${API_URL}/api/process-garment`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to process garment')
      }

      const data = await response.json()
      
      // Add to local state with front/back URLs
      setGarments(prev => [...prev, {
        id: data.id,
        url: data.front_url,  // Primary URL
        front_url: data.front_url,
        back_url: data.back_url,
        category: data.category
      }])
      invalidateCache('garments') // Invalidate cache after adding new garment

      return data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setIsLoading(false)
      setLoadingMessage('')
    }
  }

  // Process uploaded image - AI detects and creates garments from clothes in image
  const processUploadedClothes = async (file) => {
    setIsLoading(true)
    setLoadingMessage('Analyzing image...')
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      setTimeout(() => setLoadingMessage('Detecting clothes...'), 2000)
      setTimeout(() => setLoadingMessage('Creating mannequins...'), 5000)
      setTimeout(() => setLoadingMessage('Almost done...'), 10000)

      const response = await authFetch(`${API_URL}/api/process-uploaded-clothes`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to process uploaded clothes')
      }

      const data = await response.json()
      
      // Add all detected garments to local state
      if (data.garments && data.garments.length > 0) {
        setGarments(prev => [...prev, ...data.garments.map(g => ({
          id: g.id,
          url: g.front_url,
          front_url: g.front_url,
          back_url: g.back_url,
          category: g.category,
          description: g.description
        }))])
      }

      return data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setIsLoading(false)
      setLoadingMessage('')
    }
  }

  const createAvatar = async (files, mode = 'upload') => {
    setIsLoading(true)
    setLoadingMessage(mode === 'selfie' ? 'Applying your face...' : 'Processing your photo...')
    setError(null)

    try {
      const formData = new FormData()
      files.forEach(file => formData.append('files', file))
      formData.append('mode', mode) // 'upload' or 'selfie'

      if (mode === 'selfie') {
        setTimeout(() => setLoadingMessage('Creating face swap...'), 3000)
        setTimeout(() => setLoadingMessage('Blending with avatar...'), 8000)
      } else {
        setTimeout(() => setLoadingMessage('Processing full body...'), 3000)
        setTimeout(() => setLoadingMessage('Enhancing image...'), 8000)
      }

      const response = await authFetch(`${API_URL}/api/create-avatar`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to create avatar')
      }

      const data = await response.json()
      setAvatarUrl(data.avatar_url)
      invalidateCache('avatar') // Invalidate cache after creating new avatar

      return data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setIsLoading(false)
      setLoadingMessage('')
    }
  }

  const tryOn = async (garmentUrl, category) => {
    if (!avatarUrl) {
      setError('Please create an avatar first')
      throw new Error('No avatar available')
    }

    setIsLoading(true)
    setLoadingMessage('Stitching your look...')
    setError(null)

    try {
      setTimeout(() => setLoadingMessage('Fitting the garment...'), 5000)
      setTimeout(() => setLoadingMessage('Almost ready...'), 12000)

      const response = await authFetch(`${API_URL}/api/try-on`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          avatar_url: avatarUrl,
          garment_url: garmentUrl,
          category: category,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Try-on failed')
      }

      const data = await response.json()
      
      // Add to looks
      if (data.result_url) {
        setLooks(prev => [{
          id: data.id || Date.now().toString(),
          url: data.result_url,
        }, ...prev])
      }
      
      return data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setIsLoading(false)
      setLoadingMessage('')
    }
  }

  const tryOnMultiple = async (garments) => {
    if (!avatarUrl) {
      setError('Please create an avatar first')
      throw new Error('No avatar available')
    }

    if (!garments || garments.length === 0) {
      setError('Please select at least one garment')
      throw new Error('No garments selected')
    }

    setIsLoading(true)
    setLoadingMessage(`Creating your look with ${garments.length} items...`)
    setError(null)

    try {
      setTimeout(() => setLoadingMessage('Fitting the garments...'), 5000)
      setTimeout(() => setLoadingMessage('Styling your outfit...'), 10000)
      setTimeout(() => setLoadingMessage('Almost ready...'), 15000)

      const response = await authFetch(`${API_URL}/api/try-on-multiple`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          avatar_url: avatarUrl,
          garments: garments.map(g => ({
            url: g.url,
            category: g.category,
          })),
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Multi try-on failed')
      }

      const data = await response.json()
      
      // Add to looks
      if (data.result_url) {
        setLooks(prev => [{
          id: data.id || Date.now().toString(),
          url: data.result_url,
          garment_count: data.garment_count,
        }, ...prev])
      }
      
      return data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setIsLoading(false)
      setLoadingMessage('')
    }
  }

  const deleteGarment = async (garmentId) => {
    try {
      const response = await authFetch(`${API_URL}/api/garment/${garmentId}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        throw new Error('Failed to delete garment')
      }

      setGarments(prev => prev.filter(g => g.id !== garmentId))
      invalidateCache('garments')
    } catch (err) {
      setError(err.message)
      throw err
    }
  }
  
  const deleteAvatar = async () => {
    try {
      const response = await authFetch(`${API_URL}/api/avatar`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        throw new Error('Failed to delete avatar')
      }

      setAvatarUrl(null)
      invalidateCache('avatar')
    } catch (err) {
      setError(err.message)
      throw err
    }
  }

  const deleteLook = async (lookId) => {
    try {
      const response = await authFetch(`${API_URL}/api/look/${lookId}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        throw new Error('Failed to delete look')
      }

      setLooks(prev => prev.filter(l => l.id !== lookId))
      invalidateCache('looks')
    } catch (err) {
      setError(err.message)
      throw err
    }
  }

  const clearError = () => setError(null)

  // ============================================
  // Profile and Recommendation APIs
  // ============================================
  
  const fetchProfile = async (force = false) => {
    // Skip if cache is valid and not forced
    if (!force && isCacheValid('profile') && userProfile) {
      return { profile: userProfile }
    }
    
    try {
      const response = await authFetch(`${API_URL}/api/profile`)
      const data = await response.json()
      if (data.profile) {
        setUserProfile(data.profile)
        cacheTimestamps.current.profile = Date.now()
      }
      return data
    } catch (err) {
      console.error('Failed to fetch profile:', err)
      return null
    }
  }

  const analyzeProfile = async (files) => {
    setIsLoading(true)
    setLoadingMessage('Analyzing your profile...')
    setError(null)

    try {
      const formData = new FormData()
      files.forEach(file => formData.append('files', file))

      setTimeout(() => setLoadingMessage('Detecting skin tone...'), 2000)
      setTimeout(() => setLoadingMessage('Analyzing body type...'), 5000)

      const response = await authFetch(`${API_URL}/api/profile/analyze`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to analyze profile')
      }

      const data = await response.json()
      if (data.profile) {
        setUserProfile(data.profile)
      }
      return data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setIsLoading(false)
      setLoadingMessage('')
    }
  }

  const updateLocation = async (lat, lon, city = '') => {
    try {
      const response = await authFetch(`${API_URL}/api/profile/location`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lat, lon, city }),
      })

      if (!response.ok) {
        throw new Error('Failed to update location')
      }

      setUserProfile(prev => prev ? {
        ...prev,
        location: { lat, lon, city }
      } : null)

      return await response.json()
    } catch (err) {
      setError(err.message)
      throw err
    }
  }

  const getDailyOutfit = async (occasion = null) => {
    try {
      const params = new URLSearchParams({ use_weather: 'true' })
      if (occasion) {
        params.append('occasion', occasion)
      }

      const response = await authFetch(`${API_URL}/api/daily-outfit?${params}`)
      return await response.json()
    } catch (err) {
      console.error('Failed to get daily outfit:', err)
      return null
    }
  }

  // Process garment with full analysis (multi-image, color, visibility)
  const processGarmentFull = async (files, category) => {
    setIsLoading(true)
    setLoadingMessage('Processing garment...')
    setError(null)

    try {
      const formData = new FormData()
      files.forEach(file => formData.append('files', file))
      formData.append('category', category)

      setTimeout(() => setLoadingMessage('Analyzing quality...'), 1000)
      setTimeout(() => setLoadingMessage('Extracting colors...'), 3000)
      setTimeout(() => setLoadingMessage('Creating mannequin...'), 6000)

      const response = await authFetch(`${API_URL}/api/process-garment-full`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to process garment')
      }

      const data = await response.json()
      
      setGarments(prev => [...prev, {
        id: data.id,
        url: data.front_url,
        front_url: data.front_url,
        back_url: data.back_url,
        category: data.category,
        colors: data.colors,
        visibility: data.visibility,
        recommendation_scores: data.recommendation_scores
      }])

      return data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setIsLoading(false)
      setLoadingMessage('')
    }
  }

  // Create avatar with full profile analysis
  const createAvatarFull = async (files, mode = 'upload', analyzeProfileFlag = true) => {
    setIsLoading(true)
    setLoadingMessage('Processing photos...')
    setError(null)

    try {
      const formData = new FormData()
      files.forEach(file => formData.append('files', file))
      formData.append('mode', mode)
      formData.append('analyze_profile', analyzeProfileFlag)

      setTimeout(() => setLoadingMessage('Analyzing skin tone...'), 2000)
      setTimeout(() => setLoadingMessage('Detecting body type...'), 5000)
      setTimeout(() => setLoadingMessage('Creating avatar...'), 8000)

      const response = await authFetch(`${API_URL}/api/create-avatar-full`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to create avatar')
      }

      const data = await response.json()
      setAvatarUrl(data.avatar_url)
      
      if (data.profile) {
        setUserProfile(data.profile)
      }

      return data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setIsLoading(false)
      setLoadingMessage('')
    }
  }

  // ============================================
  // Data Migration
  // ============================================
  
  const migrateLegacyData = async () => {
    try {
      const response = await authFetch(`${API_URL}/api/migrate-legacy-data`, {
        method: 'POST',
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Migration failed')
      }
      
      const data = await response.json()
      
      // Refresh data after migration
      await fetchAvatar()
      await fetchGarments()
      await fetchLooks()
      await fetchProfile()
      
      return data
    } catch (err) {
      console.error('Migration failed:', err)
      throw err
    }
  }
  
  const checkLegacyData = async () => {
    try {
      const response = await authFetch(`${API_URL}/api/check-legacy-data`)
      const data = await response.json()
      return data.has_legacy_data
    } catch (err) {
      console.error('Failed to check legacy data:', err)
      return false
    }
  }

  const value = {
    avatarUrl,
    garments,
    looks,
    isLoading,
    loadingMessage,
    error,
    userProfile,
    fetchGarments,
    fetchLooks,
    processGarment,
    processUploadedClothes,
    processGarmentFull,
    createAvatar,
    createAvatarFull,
    tryOn,
    tryOnMultiple,
    deleteGarment,
    deleteAvatar,
    deleteLook,
    clearError,
    fetchProfile,
    analyzeProfile,
    updateLocation,
    getDailyOutfit,
    migrateLegacyData,
    checkLegacyData,
  }

  return (
    <WardrobeContext.Provider value={value}>
      {children}
    </WardrobeContext.Provider>
  )
}

export function useWardrobe() {
  const context = useContext(WardrobeContext)
  if (!context) {
    throw new Error('useWardrobe must be used within a WardrobeProvider')
  }
  return context
}
