/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
import { useAuth } from './AuthContext'
import { buildMultiTryOnGarments } from '../utils/tryOn'
import { trackActivationEvent } from '../utils/analytics'
import { validateStylePhotos } from '../utils/styleAnalysis'
import { createReadCache } from '../utils/readCache'

const API_URL = import.meta.env.VITE_API_URL || ''

// Cache TTL in milliseconds (5 minutes)
const CACHE_TTL = 5 * 60 * 1000

const WardrobeContext = createContext(null)

export function WardrobeProvider({ children }) {
  const { user } = useAuth()
  // Remount all private data/cache on identity changes, including direct account switches.
  return <WardrobeSession key={user?.uid || 'signed-out'}>{children}</WardrobeSession>
}

function WardrobeSession({ children }) {
  const { getIdToken, user } = useAuth()
  
  const [avatarUrl, setAvatarUrl] = useState(null)
  const [garments, setGarments] = useState([])
  const [looks, setLooks] = useState([])
  const [nextLookOffset, setNextLookOffset] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [loadingMessage, setLoadingMessage] = useState('')
  const [error, setError] = useState(null)
  const [userProfile, setUserProfile] = useState(null)
  const profileRevision = useRef(0)
  
  const readCache = useRef(createReadCache(CACHE_TTL))
  const garmentSelection = useRef(0)
  const invalidateCache = (key) => readCache.current.invalidate(key)

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

  const readJson = useCallback(async (url) => {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 30000)
    try {
      const response = await authFetch(url, { signal: controller.signal })
      if (!response.ok) throw new Error('Could not load data. Please retry.')
      return await response.json()
    } finally {
      clearTimeout(timeout)
    }
  }, [authFetch])

  const fetchAvatar = useCallback(async (force = false) => {
    if (!user) return
    try {
      const result = await readCache.current.read('avatar', () => readJson(`${API_URL}/api/avatar`), force)
      if (result.isCurrent()) setAvatarUrl(result.value.avatar_url || null)
    } catch (err) {
      console.error('Failed to fetch avatar:', err)
    }
  }, [readJson, user])

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
      readCache.current = createReadCache(CACHE_TTL)
    }
  }, [user, fetchAvatar])

  const fetchGarments = useCallback(async (category = null, force = false) => {
    if (!user) return
    const selection = ++garmentSelection.current
    try {
      const url = category
        ? `${API_URL}/api/wardrobe?category=${encodeURIComponent(category)}`
        : `${API_URL}/api/wardrobe`
      const result = await readCache.current.read(`garments:${category || 'all'}`, async () => {
        const data = await readJson(url)
        if (!Array.isArray(data.garments)) throw new Error('Invalid wardrobe response')
        return data
      }, force)
      if (result.isCurrent() && selection === garmentSelection.current) setGarments(result.value.garments)
    } catch (err) {
      console.error('Failed to fetch garments:', err)
      if (selection === garmentSelection.current) setError('Failed to load wardrobe')
    }
  }, [readJson, user])

  const fetchLooks = useCallback(async (force = false) => {
    if (!user) return
    try {
      const result = await readCache.current.read('looks', async () => {
        const data = await readJson(`${API_URL}/api/try-on/history`)
        if (!Array.isArray(data.results)) throw new Error('Invalid history response')
        return data
      }, force)
      if (result.isCurrent()) { setLooks(result.value.results); setNextLookOffset(result.value.next_offset ?? null) }
    } catch (err) {
      console.error('Failed to fetch looks:', err)
    }
  }, [readJson, user])

  const loadMoreLooks = async () => {
    if (nextLookOffset === null) return
    const data = await readJson(`${API_URL}/api/try-on/history?offset=${nextLookOffset}`)
    setLooks(previous => [...previous, ...data.results.filter(look => !previous.some(p => p.id === look.id))])
    setNextLookOffset(data.next_offset ?? null)
  }

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
      void trackActivationEvent(
        'first_garment_added',
        getIdToken,
        { category: data.category || category, garment_count: 1 },
      )

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
        invalidateCache('garments')
        setGarments(prev => [...prev, ...data.garments.map(g => ({
          id: g.id,
          url: g.front_url,
          front_url: g.front_url,
          back_url: g.back_url,
          category: g.category,
          description: g.description
        }))])
        void trackActivationEvent(
          'first_garment_added',
          getIdToken,
          {
            category: data.garments[0].category,
            garment_count: data.garments.length,
          },
        )
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

  const createAvatar = async (files, mode = 'upload', activate = true) => {
    setIsLoading(true)
    setLoadingMessage(mode === 'selfie' ? 'Applying your face...' : 'Processing your photo...')
    setError(null)

    try {
      const formData = new FormData()
      files.forEach(file => formData.append('files', file))
      formData.append('mode', mode)
      formData.append('activate', String(activate))

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
      if (activate) setAvatarUrl(data.avatar_url)
      invalidateCache('avatar') // Invalidate cache after creating new avatar
      void trackActivationEvent('avatar_created', getIdToken, { mode })

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
        invalidateCache('looks')
        setLooks(prev => [{
          id: data.id || Date.now().toString(),
          url: data.result_url,
        }, ...prev])
        void trackActivationEvent('first_try_on_completed', getIdToken, {
          category,
          garment_count: 1,
        })
        void trackActivationEvent('first_look_saved', getIdToken, {
          garment_count: 1,
        })
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
      const requestGarments = buildMultiTryOnGarments(garments)

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
          garments: requestGarments,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Multi try-on failed')
      }

      const data = await response.json()
      
      // Add to looks
      if (data.result_url) {
        invalidateCache('looks')
        setLooks(prev => [{
          id: data.id || Date.now().toString(),
          url: data.result_url,
          garment_count: data.garment_count,
        }, ...prev])
        void trackActivationEvent('first_try_on_completed', getIdToken, {
          garment_count: garments.length,
        })
        void trackActivationEvent('first_look_saved', getIdToken, {
          garment_count: garments.length,
        })
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

  const updateLook = async (lookId, updates) => {
    try {
      const response = await authFetch(`${API_URL}/api/look/${lookId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to update look')
      }

      const data = await response.json()
      invalidateCache('looks')
      setLooks(prev => prev.map(look => (
        look.id === lookId ? { ...look, ...data } : look
      )))
      return data
    } catch (err) {
      setError(err.message)
      throw err
    }
  }

  const clearError = () => setError(null)

  // ============================================
  // Profile and Recommendation APIs
  // ============================================
  
  const applyProfile = useCallback((profile) => {
    profileRevision.current += 1
    setUserProfile(profile)
    readCache.current.invalidate('profile')
  }, [])

  const fetchProfile = useCallback(async (force = true) => {
    if (!user) return
    if (force) readCache.current.invalidate('profile')
    const revision = profileRevision.current
    try {
      // Explicit Profile reloads supersede reads started before direct location edits.
      const result = await readCache.current.read('profile', () => readJson(`${API_URL}/api/profile`), force)
      if (!result.isCurrent() || revision !== profileRevision.current) return null
      setUserProfile(result.value.profile || null)
      return result.value
    } catch (err) {
      console.error('Failed to fetch profile:', err)
      return { error: 'Failed to load your profile. Please reload to retry.' }
    }
  }, [readJson, user])

  useEffect(() => {
    if (user) fetchProfile(false)
  }, [user, fetchProfile])

  const analyzeProfile = async (files, stage = 'auto') => {
    const validationError = validateStylePhotos(files)
    if (validationError) throw new Error(validationError)
    setIsLoading(true)
    setLoadingMessage('Analyzing your profile...')
    setError(null)

    try {
      const formData = new FormData()
      files.forEach(file => formData.append('files', file))
      formData.append('stage', stage)

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
        applyProfile(data.profile)
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

      profileRevision.current += 1
      invalidateCache('profile')
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
      
      invalidateCache('garments')
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
      void trackActivationEvent(
        'first_garment_added',
        getIdToken,
        { category: data.category || category, garment_count: 1 },
      )

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
      invalidateCache('avatar')
      setAvatarUrl(data.avatar_url)
      
      if (data.profile) {
        applyProfile(data.profile)
      }
      void trackActivationEvent('avatar_created', getIdToken, { mode })

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
      await Promise.all([
        fetchAvatar(true),
        fetchGarments(null, true),
        fetchLooks(true),
        fetchProfile(true),
      ])
      
      return data
    } catch (err) {
      console.error('Migration failed:', err)
      throw err
    }
  }
  
  const checkLegacyData = useCallback(async () => {
    const response = await authFetch(`${API_URL}/api/check-legacy-data`)
    if (!response.ok) throw new Error('Could not check previous-session data. Please retry.')
    const data = await response.json()
    if (typeof data.has_legacy_data !== 'boolean') throw new Error('Could not read previous-session data.')
    return data.has_legacy_data
  }, [authFetch])

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
    nextLookOffset,
    loadMoreLooks,
    processGarment,
    processUploadedClothes,
    processGarmentFull,
    createAvatar,
    fetchAvatar,
    createAvatarFull,
    tryOn,
    tryOnMultiple,
    deleteGarment,
    deleteAvatar,
    deleteLook,
    updateLook,
    clearError,
    fetchProfile,
    analyzeProfile,
    applyProfile,
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
