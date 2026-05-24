import { Loader2 } from 'lucide-react'

/*
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
*/

export default function LoadingOverlay({ message = 'Processing...' }) {
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center safe-top safe-bottom" style={{ background: 'var(--bg-primary)' }}>
      {/* Animated loader */}
      <div className="relative mb-8">
        {/* Outer ring */}
        <div className="w-24 h-24 rounded-full" style={{ border: '4px solid var(--accent-glow)' }} />
        
        {/* Spinning ring */}
        <div className="absolute inset-0 w-24 h-24 rounded-full border-4 border-transparent animate-spin" style={{ borderTopColor: 'var(--accent)' }} />
        
        {/* Center icon */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ background: 'var(--accent-glow)' }}>
            <Loader2 className="w-6 h-6 animate-spin" style={{ color: 'var(--accent-light)', animationDirection: 'reverse' }} />
          </div>
        </div>
      </div>

      {/* Message */}
      <p className="text-lg font-medium mb-2 animate-pulse-soft" style={{ color: 'var(--text-primary)' }}>
        {message}
      </p>
      
      {/* Sub-message */}
      <p className="text-sm max-w-[250px] text-center" style={{ color: 'var(--text-tertiary)' }}>
        This may take 10-30 seconds. Please don't close the app.
      </p>

      {/* Progress dots */}
      <div className="flex gap-2 mt-6">
        {[0, 1, 2].map(i => (
          <div
            key={i}
            className="w-2 h-2 rounded-full animate-pulse-soft"
            style={{ background: 'var(--accent)', animationDelay: `${i * 0.3}s` }}
          />
        ))}
      </div>
    </div>
  )
}





