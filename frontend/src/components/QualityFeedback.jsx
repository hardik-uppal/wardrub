import { AlertCircle, Camera, Check, X } from 'lucide-react'

/**
 * Quality feedback component for garment/avatar upload
 * Shows visibility score and prompts for more photos if needed
 */
export default function QualityFeedback({ 
  quality,
  onAddMore,
  onDismiss,
  type = 'garment' // 'garment' or 'avatar'
}) {
  if (!quality) return null
  
  const { 
    needs_more_images, 
    recommendation, 
    images_processed,
    visibility 
  } = quality
  
  // Determine status color
  const getStatusColor = () => {
    if (!needs_more_images) return 'green'
    if (visibility?.status === 'acceptable') return 'amber'
    return 'red'
  }
  
  const statusColor = getStatusColor()
  const colors = {
    green: {
      bg: 'bg-green-50',
      border: 'border-green-200',
      icon: 'text-green-600',
      text: 'text-green-800'
    },
    amber: {
      bg: 'bg-amber-50',
      border: 'border-amber-200',
      icon: 'text-amber-600',
      text: 'text-amber-800'
    },
    red: {
      bg: 'bg-red-50',
      border: 'border-red-200',
      icon: 'text-red-600',
      text: 'text-red-800'
    }
  }
  
  const c = colors[statusColor]

  return (
    <div className={`${c.bg} border ${c.border} rounded-xl p-4 animate-fade-in`}>
      <div className="flex items-start gap-3">
        <div className={`flex-shrink-0 mt-0.5 ${c.icon}`}>
          {needs_more_images ? (
            <AlertCircle className="w-5 h-5" />
          ) : (
            <Check className="w-5 h-5" />
          )}
        </div>
        
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-medium ${c.text}`}>
            {needs_more_images 
              ? 'More photos recommended' 
              : 'Image quality looks good!'
            }
          </p>
          
          {recommendation && (
            <p className={`text-xs ${c.text} opacity-80 mt-1`}>
              {recommendation}
            </p>
          )}
          
          {visibility && (
            <div className="mt-2 flex items-center gap-2">
              <div className="flex-1 h-1.5 bg-white/50 rounded-full overflow-hidden">
                <div 
                  className={`h-full rounded-full ${
                    visibility.score > 0.6 ? 'bg-green-500' :
                    visibility.score > 0.4 ? 'bg-amber-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${visibility.score * 100}%` }}
                />
              </div>
              <span className="text-xs text-gray-600">
                {Math.round(visibility.score * 100)}% visible
              </span>
            </div>
          )}
          
          {images_processed && (
            <p className="text-xs text-gray-500 mt-1">
              {images_processed} image{images_processed > 1 ? 's' : ''} processed
            </p>
          )}
        </div>
        
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="flex-shrink-0 p-1 hover:bg-black/5 rounded-full"
          >
            <X className="w-4 h-4 text-gray-400" />
          </button>
        )}
      </div>
      
      {needs_more_images && onAddMore && (
        <button
          onClick={onAddMore}
          className={`mt-3 w-full py-2 px-4 ${c.bg} border ${c.border} rounded-lg 
            flex items-center justify-center gap-2 text-sm font-medium ${c.text}
            hover:brightness-95 transition-all`}
        >
          <Camera className="w-4 h-4" />
          Add More Photos
        </button>
      )}
    </div>
  )
}


/**
 * Visibility badge for garment cards
 */
export function VisibilityBadge({ visibility }) {
  if (!visibility) return null
  
  const { score, status } = visibility
  
  const statusConfig = {
    good: { color: 'bg-green-100 text-green-700', label: 'Good' },
    acceptable: { color: 'bg-amber-100 text-amber-700', label: 'OK' },
    needs_more: { color: 'bg-red-100 text-red-700', label: 'Low' }
  }
  
  const config = statusConfig[status] || statusConfig.acceptable

  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${config.color}`}>
      {config.label}
    </span>
  )
}


/**
 * Recommendation score badge
 */
export function RecommendationBadge({ score }) {
  if (score === undefined || score === null) return null
  
  const percentage = Math.round(score * 100)
  
  let color = 'bg-gray-100 text-gray-700'
  if (percentage >= 80) color = 'bg-green-100 text-green-700'
  else if (percentage >= 60) color = 'bg-blue-100 text-blue-700'
  else if (percentage >= 40) color = 'bg-amber-100 text-amber-700'

  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${color}`}>
      {percentage}% match
    </span>
  )
}

