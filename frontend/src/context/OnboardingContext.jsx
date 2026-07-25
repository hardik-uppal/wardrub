/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react'
import { useWardrobe } from './WardrobeContext'

const OnboardingContext = createContext(null)

// Non-sensitive UI preference keys for localStorage
const STORAGE_KEYS = {
  WIDGET_MINIMIZED: 'wardrub_widget_minimized',
  CELEBRATION_SEEN: 'wardrub_celebration_seen',
}

const GARMENT_GOAL = 10

export function OnboardingProvider({ children }) {
  const { avatarUrl, garments, userProfile } = useWardrobe()
  
  const [widgetMinimized, setWidgetMinimized] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEYS.WIDGET_MINIMIZED) === 'true'
    } catch {
      return false
    }
  })

  const [celebrationSeen, setCelebrationSeen] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.CELEBRATION_SEEN)
      return stored ? JSON.parse(stored) : {}
    } catch {
      return {}
    }
  })

  // Derived milestone states
  const avatarDone = !!avatarUrl
  const garmentsCount = garments ? garments.filter(g => !g.id.startsWith('mock-')).length : 0
  const garmentsDone = garmentsCount >= GARMENT_GOAL
  const garmentsProgress = Math.min(garmentsCount, GARMENT_GOAL)
  const profileDone = !!(userProfile?.skin_tone || userProfile?.body_type)
  
  const isOnboardingComplete = avatarDone && garmentsDone && profileDone

  // Completed milestones count (out of 3)
  const completedCount = useMemo(() => {
    let count = 0
    if (avatarDone) count++
    if (garmentsDone) count++
    if (profileDone) count++
    return count
  }, [avatarDone, garmentsDone, profileDone])

  const totalMilestones = 3
  const overallProgress = completedCount / totalMilestones

  // Milestones data for the widget
  const milestones = useMemo(() => [
    {
      id: 'avatar',
      label: 'Create your avatar',
      description: 'Upload a photo so we can dress you virtually',
      done: avatarDone,
      route: '/create-avatar',
      icon: 'User',
    },
    {
      id: 'clothes',
      label: 'Add 10 clothes',
      description: 'Build your wardrobe for personalized outfits',
      done: garmentsDone,
      progress: garmentsProgress,
      goal: GARMENT_GOAL,
      route: '/capture',
      icon: 'Shirt',
    },
    {
      id: 'style',
      label: 'Analyze your style',
      description: 'Discover your best colors and body type',
      done: profileDone,
      route: '/profile',
      icon: 'Sparkles',
    },
  ], [avatarDone, garmentsDone, garmentsProgress, profileDone])

  // Actions
  const toggleWidgetMinimized = useCallback(() => {
    setWidgetMinimized(prev => {
      const next = !prev
      try {
        localStorage.setItem(STORAGE_KEYS.WIDGET_MINIMIZED, String(next))
      } catch {
        // localStorage not available
      }
      return next
    })
  }, [])

  const markCelebration = useCallback((milestoneId) => {
    setCelebrationSeen(prev => {
      const updated = { ...prev, [milestoneId]: true }
      try {
        localStorage.setItem(STORAGE_KEYS.CELEBRATION_SEEN, JSON.stringify(updated))
      } catch {
        // localStorage not available
      }
      return updated
    })
  }, [])

  const shouldCelebrate = useCallback((milestoneId) => {
    // Check if milestone is done but celebration not yet seen
    const milestone = milestones.find(m => m.id === milestoneId)
    return milestone?.done && !celebrationSeen[milestoneId]
  }, [milestones, celebrationSeen])

  // Auto-hide widget when complete (after a delay for celebration)
  const [showCompleteCelebration, setShowCompleteCelebration] = useState(false)
  
  useEffect(() => {
    if (isOnboardingComplete && !celebrationSeen.complete) {
      const startTimer = setTimeout(() => {
        setShowCompleteCelebration(true)
      }, 0)
      return () => clearTimeout(startTimer)
    }
  }, [isOnboardingComplete, celebrationSeen.complete])

  useEffect(() => {
    if (!showCompleteCelebration) return

    const timer = setTimeout(() => {
      setShowCompleteCelebration(false)
      markCelebration('complete')
    }, 5000)
    return () => clearTimeout(timer)
  }, [showCompleteCelebration, markCelebration])

  const value = useMemo(() => ({
    // State
    avatarDone,
    garmentsDone,
    garmentsCount,
    garmentsProgress,
    profileDone,
    isOnboardingComplete,
    completedCount,
    totalMilestones,
    overallProgress,
    milestones,
    widgetMinimized,
    showCompleteCelebration,
    GARMENT_GOAL,
    
    // Actions
    toggleWidgetMinimized,
    markCelebration,
    shouldCelebrate,
  }), [
    avatarDone, garmentsDone, garmentsCount, garmentsProgress,
    profileDone, isOnboardingComplete, completedCount, overallProgress,
    milestones, widgetMinimized, showCompleteCelebration,
    toggleWidgetMinimized,
    markCelebration, shouldCelebrate,
  ])

  return (
    <OnboardingContext.Provider value={value}>
      {children}
    </OnboardingContext.Provider>
  )
}

export function useOnboarding() {
  const context = useContext(OnboardingContext)
  if (!context) {
    throw new Error('useOnboarding must be used within an OnboardingProvider')
  }
  return context
}
