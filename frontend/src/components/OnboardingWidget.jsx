import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { 
  User, Shirt, Sparkles, ChevronUp, ChevronDown, 
  Check, ArrowRight, PartyPopper
} from 'lucide-react'
import { useOnboarding } from '../context/OnboardingContext'

const iconMap = {
  User,
  Shirt,
  Sparkles,
}

// SVG progress ring component
function ProgressRing({ progress, size = 44, strokeWidth = 3 }) {
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (progress * circumference)

  return (
    <svg width={size} height={size} className="onboarding-progress-ring">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="var(--glass-border)"
        strokeWidth={strokeWidth}
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="var(--accent)"
        strokeWidth={strokeWidth}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        className="onboarding-progress-ring-fill"
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
    </svg>
  )
}

export default function OnboardingWidget() {
  const navigate = useNavigate()
  const location = useLocation()
  const {
    isOnboardingComplete,
    completedCount,
    totalMilestones,
    overallProgress,
    milestones,
    widgetMinimized,
    toggleWidgetMinimized,
    showCompleteCelebration,
    markCelebration,
    shouldCelebrate,
    GARMENT_GOAL,
  } = useOnboarding()

  const [justCompleted, setJustCompleted] = useState(null)
  const [isHidden, setIsHidden] = useState(false)

  // Check for milestone celebrations
  useEffect(() => {
    const milestone = milestones.find(m => shouldCelebrate(m.id))
    if (milestone) {
      const startTimer = setTimeout(() => {
        setJustCompleted(milestone.id)
        markCelebration(milestone.id)
      }, 0)

      return () => clearTimeout(startTimer)
    }
  }, [milestones, shouldCelebrate, markCelebration])

  useEffect(() => {
    if (justCompleted) {
      const timer = setTimeout(() => {
        setJustCompleted(null)
      }, 3000)

      return () => clearTimeout(timer)
    }
  }, [justCompleted])

  // Hide completely after completion celebration ends
  useEffect(() => {
    if (isOnboardingComplete && !showCompleteCelebration) {
      const timer = setTimeout(() => setIsHidden(true), 500)
      return () => clearTimeout(timer)
    }
  }, [isOnboardingComplete, showCompleteCelebration])

  if (isHidden) return null

  const widgetClassName = `onboarding-widget-container ${
    location.pathname === '/dressing-room' ? 'onboarding-widget-with-action' : ''
  }`

  const goToMilestone = (route) => {
    if (!widgetMinimized) {
      toggleWidgetMinimized()
    }
    navigate(route)
  }

  // Completion celebration state
  if (showCompleteCelebration) {
    return (
      <div className={`${widgetClassName} animate-scale-in`}>
        <div 
          className="onboarding-widget-expanded"
          style={{
            background: 'var(--bg-primary)',
            border: '1px solid var(--accent)',
            borderRadius: '16px',
            boxShadow: 'var(--shadow-lg)',
            padding: '24px',
            textAlign: 'center',
          }}
        >
          <div className="mb-3 animate-float">
            <PartyPopper className="w-10 h-10 mx-auto" style={{ color: 'var(--accent)' }} />
          </div>
          <h3 
            className="text-lg font-bold mb-1"
            style={{ color: 'var(--text-primary)' }}
          >
            All Set!
          </h3>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            Your wardrobe is ready. Enjoy your personalized magazine!
          </p>
        </div>
      </div>
    )
  }

  // Collapsed state — just the progress ring
  if (widgetMinimized) {
    return (
      <div className={widgetClassName}>
        <button
          onClick={toggleWidgetMinimized}
          className="onboarding-widget-collapsed"
          style={{
            background: 'var(--bg-primary)',
            border: '1px solid var(--glass-border)',
            borderRadius: '50%',
            width: '52px',
            height: '52px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            boxShadow: 'var(--shadow-md)',
            position: 'relative',
          }}
          aria-label="Open onboarding progress"
        >
          <ProgressRing progress={overallProgress} size={44} strokeWidth={3} />
          <span 
            className="absolute text-xs font-bold"
            style={{ color: 'var(--text-primary)' }}
          >
            {completedCount}/{totalMilestones}
          </span>
        </button>
      </div>
    )
  }

  // Expanded state
  return (
    <div className={`${widgetClassName} animate-scale-in`}>
      <div 
        className="onboarding-widget-expanded"
        style={{
          background: 'var(--bg-primary)',
          border: '1px solid var(--glass-border)',
          borderRadius: '16px',
          boxShadow: 'var(--shadow-lg)',
          overflow: 'hidden',
          width: '300px',
        }}
      >
        {/* Header */}
        <div 
          className="flex items-center justify-between px-4 py-3"
          style={{ borderBottom: '1px solid var(--glass-border)' }}
        >
          <div className="flex items-center gap-3">
            <ProgressRing progress={overallProgress} size={32} strokeWidth={2.5} />
            <div>
              <h4 
                className="text-sm font-bold"
                style={{ color: 'var(--text-primary)' }}
              >
                Set up your Wardrub
              </h4>
              <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                {completedCount} of {totalMilestones} complete
              </p>
            </div>
          </div>
          <button
            onClick={toggleWidgetMinimized}
            className="w-7 h-7 rounded-full flex items-center justify-center transition-colors"
            style={{ background: 'var(--bg-secondary)' }}
            aria-label="Minimize onboarding widget"
          >
            <ChevronDown className="w-3.5 h-3.5" style={{ color: 'var(--text-secondary)' }} />
          </button>
        </div>

        {/* Milestones */}
        <div className="px-3 py-2">
          {milestones.map((milestone) => {
            const Icon = iconMap[milestone.icon]
            const isCelebrating = justCompleted === milestone.id
            
            return (
              <div 
                key={milestone.id}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
                  isCelebrating ? 'onboarding-celebrate' : ''
                }`}
                style={{
                  background: isCelebrating ? 'rgba(16, 185, 129, 0.08)' : 'transparent',
                }}
              >
                {/* Status Icon */}
                <div 
                  className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 transition-all"
                  style={{
                    background: milestone.done 
                      ? 'var(--accent)' 
                      : 'var(--bg-secondary)',
                    border: milestone.done 
                      ? 'none' 
                      : '1px solid var(--glass-border)',
                  }}
                >
                  {milestone.done ? (
                    <Check className="w-3.5 h-3.5 text-white" />
                  ) : (
                    <Icon className="w-3.5 h-3.5" style={{ color: 'var(--text-tertiary)' }} />
                  )}
                </div>

                {/* Label & Progress */}
                <div className="flex-1 min-w-0">
                  <p 
                    className="text-xs font-medium truncate"
                    style={{ 
                      color: milestone.done ? 'var(--text-tertiary)' : 'var(--text-primary)',
                      textDecoration: milestone.done ? 'line-through' : 'none',
                    }}
                  >
                    {milestone.label}
                  </p>
                  
                  {/* Progress bar for clothes */}
                  {milestone.id === 'clothes' && !milestone.done && (
                    <div className="flex items-center gap-2 mt-1">
                      <div 
                        className="flex-1 h-1.5 rounded-full overflow-hidden"
                        style={{ background: 'var(--bg-secondary)' }}
                      >
                        <div 
                          className="h-full rounded-full transition-all duration-500"
                          style={{ 
                            background: 'var(--accent)',
                            width: `${(milestone.progress / GARMENT_GOAL) * 100}%`,
                          }}
                        />
                      </div>
                      <span 
                        className="text-xs font-medium tabular-nums flex-shrink-0"
                        style={{ color: 'var(--text-tertiary)' }}
                      >
                        {milestone.progress}/{GARMENT_GOAL}
                      </span>
                    </div>
                  )}
                </div>

                {/* CTA Arrow */}
                {!milestone.done && (
                  <button
                    onClick={() => goToMilestone(milestone.route)}
                    className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 transition-colors"
                    style={{ background: 'var(--accent-glow)' }}
                    aria-label={`Go to ${milestone.label}`}
                  >
                    <ArrowRight className="w-3 h-3" style={{ color: 'var(--accent)' }} />
                  </button>
                )}
              </div>
            )
          })}
        </div>

        {/* Bottom progress bar */}
        <div className="px-4 pb-3">
          <div 
            className="w-full h-1 rounded-full overflow-hidden"
            style={{ background: 'var(--bg-secondary)' }}
          >
            <div 
              className="h-full rounded-full transition-all duration-700 ease-out"
              style={{ 
                background: 'var(--accent)',
                width: `${overallProgress * 100}%`,
              }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
