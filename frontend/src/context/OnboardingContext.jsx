/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react'
import { useWardrobe } from './WardrobeContext'

const OnboardingContext = createContext(null)

// Non-sensitive UI preference keys for localStorage
const STORAGE_KEYS = {
  WELCOME_SEEN: 'wardrub_welcome_seen',
  DISMISSED_TOOLTIPS: 'wardrub_dismissed_tooltips',
  WIDGET_MINIMIZED: 'wardrub_widget_minimized',
  CELEBRATION_SEEN: 'wardrub_celebration_seen',
}

const GARMENT_GOAL = 10

// Steps in order
const STEPS = {
  WELCOME: 'welcome',
  AVATAR: 'avatar',
  CLOTHES: 'clothes',
  STYLE: 'style',
  COMPLETE: 'complete',
}

export function OnboardingProvider({ children }) {
  const { avatarUrl, garments, userProfile } = useWardrobe()
  
  // localStorage-backed UI preferences (non-sensitive display state only)
  const [welcomeSeen, setWelcomeSeen] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEYS.WELCOME_SEEN) === 'true'
    } catch {
      return false
    }
  })
  
  const [dismissedTooltips, setDismissedTooltips] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.DISMISSED_TOOLTIPS)
      return stored ? JSON.parse(stored) : []
    } catch {
      return []
    }
  })
  
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

  // Determine current step (first incomplete milestone)
  const currentStep = useMemo(() => {
    if (!welcomeSeen) return STEPS.WELCOME
    if (!avatarDone) return STEPS.AVATAR
    if (!garmentsDone) return STEPS.CLOTHES
    if (!profileDone) return STEPS.STYLE
    return STEPS.COMPLETE
  }, [welcomeSeen, avatarDone, garmentsDone, profileDone])

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
  const markWelcomeSeen = useCallback(() => {
    setWelcomeSeen(true)
    try {
      localStorage.setItem(STORAGE_KEYS.WELCOME_SEEN, 'true')
    } catch {
      // localStorage not available, state still updates in memory
    }
  }, [])

  const dismissTooltip = useCallback((tooltipId) => {
    setDismissedTooltips(prev => {
      const updated = [...prev, tooltipId]
      try {
        localStorage.setItem(STORAGE_KEYS.DISMISSED_TOOLTIPS, JSON.stringify(updated))
      } catch {
        // localStorage not available
      }
      return updated
    })
  }, [])

  const isTooltipDismissed = useCallback((tooltipId) => {
    return dismissedTooltips.includes(tooltipId)
  }, [dismissedTooltips])

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
      setShowCompleteCelebration(true)
      const timer = setTimeout(() => {
        setShowCompleteCelebration(false)
        markCelebration('complete')
      }, 5000)
      return () => clearTimeout(timer)
    }
  }, [isOnboardingComplete, celebrationSeen.complete, markCelebration])

  const value = useMemo(() => ({
    // State
    welcomeSeen,
    avatarDone,
    garmentsDone,
    garmentsCount,
    garmentsProgress,
    profileDone,
    isOnboardingComplete,
    completedCount,
    totalMilestones,
    overallProgress,
    currentStep,
    milestones,
    widgetMinimized,
    showCompleteCelebration,
    GARMENT_GOAL,
    
    // Actions
    markWelcomeSeen,
    dismissTooltip,
    isTooltipDismissed,
    toggleWidgetMinimized,
    markCelebration,
    shouldCelebrate,
  }), [
    welcomeSeen, avatarDone, garmentsDone, garmentsCount, garmentsProgress,
    profileDone, isOnboardingComplete, completedCount, overallProgress,
    currentStep, milestones, widgetMinimized, showCompleteCelebration,
    markWelcomeSeen, dismissTooltip, isTooltipDismissed, toggleWidgetMinimized,
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

export { STEPS }
