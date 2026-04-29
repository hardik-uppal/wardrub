import { Loader2 } from 'lucide-react'

const loadingMessages = [
  'Analyzing your garment...',
  'Removing background...',
  'Creating your avatar...',
  'Generating full body...',
  'Stitching your look...',
  'Fitting the garment...',
  'Adding finishing touches...',
  'Almost ready...',
]

export default function LoadingOverlay({ message = 'Processing...' }) {
  return (
    <div className="fixed inset-0 z-50 bg-[var(--color-charcoal)]/95 backdrop-blur-sm flex flex-col items-center justify-center safe-top safe-bottom">
      {/* Animated loader */}
      <div className="relative mb-8">
        {/* Outer ring */}
        <div className="w-24 h-24 rounded-full border-4 border-[var(--color-terracotta)]/20" />
        
        {/* Spinning ring */}
        <div className="absolute inset-0 w-24 h-24 rounded-full border-4 border-transparent border-t-[var(--color-terracotta)] animate-spin" />
        
        {/* Center icon */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-12 h-12 rounded-full bg-[var(--color-terracotta)]/20 flex items-center justify-center">
            <Loader2 className="w-6 h-6 text-[var(--color-terracotta)] animate-spin" style={{ animationDirection: 'reverse' }} />
          </div>
        </div>
      </div>

      {/* Message */}
      <p className="text-lg font-medium text-white mb-2 animate-pulse-soft">
        {message}
      </p>
      
      {/* Sub-message */}
      <p className="text-sm text-white/60 max-w-[250px] text-center">
        This may take 10-30 seconds. Please don't close the app.
      </p>

      {/* Progress dots */}
      <div className="flex gap-2 mt-6">
        {[0, 1, 2].map(i => (
          <div
            key={i}
            className="w-2 h-2 rounded-full bg-[var(--color-terracotta)] animate-pulse-soft"
            style={{ animationDelay: `${i * 0.3}s` }}
          />
        ))}
      </div>
    </div>
  )
}





