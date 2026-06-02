import { X } from 'lucide-react'
import { useOnboarding } from '../context/OnboardingContext'

/**
 * Contextual tooltip that appears at specific points in the UI.
 * Dismissed tooltips are tracked in localStorage so they don't reappear.
 *
 * @param {string} id - Unique tooltip ID for tracking dismissal
 * @param {string} message - The message to display
 * @param {string} [cta] - Optional CTA button text
 * @param {function} [onCtaClick] - CTA click handler
 * @param {'top'|'bottom'|'left'|'right'} [position='top'] - Arrow position
 * @param {string} [className] - Additional CSS classes
 */
export default function OnboardingTooltip({ 
  id, 
  message, 
  cta, 
  onCtaClick, 
  position = 'top',
  className = '' 
}) {
  const { isTooltipDismissed, dismissTooltip, isOnboardingComplete } = useOnboarding()

  // Don't show if already dismissed or onboarding is complete
  if (isTooltipDismissed(id) || isOnboardingComplete) return null

  return (
    <div 
      className={`onboarding-tooltip onboarding-tooltip-${position} animate-fade-in ${className}`}
      role="tooltip"
    >
      {/* Arrow */}
      <div className={`onboarding-tooltip-arrow onboarding-tooltip-arrow-${position}`} />
      
      {/* Content */}
      <div className="flex items-start gap-2">
        <p 
          className="text-xs leading-relaxed flex-1"
          style={{ color: 'var(--text-primary)' }}
        >
          {message}
        </p>
        <button
          onClick={() => dismissTooltip(id)}
          className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 transition-colors"
          style={{ background: 'var(--bg-secondary)' }}
          aria-label="Dismiss tip"
        >
          <X className="w-3 h-3" style={{ color: 'var(--text-tertiary)' }} />
        </button>
      </div>

      {/* Optional CTA */}
      {cta && onCtaClick && (
        <button
          onClick={() => {
            onCtaClick()
            dismissTooltip(id)
          }}
          className="mt-2 text-xs font-semibold transition-colors"
          style={{ color: 'var(--accent)' }}
        >
          {cta} →
        </button>
      )}
    </div>
  )
}
