import { useState, useEffect } from 'react'
import { Shirt, User, Sparkles, ChevronRight, ArrowRight } from 'lucide-react'
import { useOnboarding } from '../context/OnboardingContext'

// Slide data
const slides = [
  {
    icon: Shirt,
    title: 'Your Digital Closet',
    subtitle: 'Upload your clothes to build a virtual wardrobe that lives in your pocket.',
    accent: 'var(--accent)',
  },
  {
    icon: Sparkles,
    title: 'AI Styling',
    subtitle: 'Get personalized outfit recommendations curated in a daily magazine format.',
    accent: 'var(--accent)',
  },
  {
    icon: User,
    title: 'Virtual Try-On',
    subtitle: 'See outfits on your avatar before wearing them. Mix, match, and discover your style.',
    accent: 'var(--accent)',
  },
]

export default function WelcomeModal() {
  const { welcomeSeen, markWelcomeSeen } = useOnboarding()
  const [currentSlide, setCurrentSlide] = useState(0)
  const [isVisible, setIsVisible] = useState(false)
  const [isExiting, setIsExiting] = useState(false)

  useEffect(() => {
    if (!welcomeSeen) {
      // Slight delay for entrance animation
      const timer = setTimeout(() => setIsVisible(true), 300)
      return () => clearTimeout(timer)
    }
  }, [welcomeSeen])

  if (welcomeSeen || !isVisible) return null

  const handleNext = () => {
    if (currentSlide < slides.length - 1) {
      setCurrentSlide(prev => prev + 1)
    }
  }

  const handlePrev = () => {
    if (currentSlide > 0) {
      setCurrentSlide(prev => prev - 1)
    }
  }

  const handleDismiss = () => {
    setIsExiting(true)
    setTimeout(() => {
      markWelcomeSeen()
    }, 400)
  }

  const slide = slides[currentSlide]
  const SlideIcon = slide.icon
  const isLast = currentSlide === slides.length - 1

  return (
    <div 
      className={`fixed inset-0 z-[100] flex items-center justify-center p-5 transition-all duration-400 ${
        isExiting ? 'opacity-0 scale-95' : 'opacity-100 scale-100'
      }`}
      style={{ background: 'rgba(0, 0, 0, 0.7)', backdropFilter: 'blur(12px)' }}
    >
      <div 
        className="w-full max-w-sm animate-slide-up"
        style={{
          background: 'var(--bg-primary)',
          border: '1px solid var(--glass-border)',
          borderRadius: '20px',
          boxShadow: 'var(--shadow-lg)',
          overflow: 'hidden',
        }}
      >
        {/* Brand Header */}
        <div 
          className="pt-8 pb-4 text-center"
          style={{ borderBottom: '1px solid var(--glass-border)' }}
        >
          <span 
            className="text-3xl font-bold tracking-tight"
            style={{ fontFamily: "'Playfair Display', Georgia, serif", color: 'var(--text-primary)' }}
          >
            Wardrub
          </span>
          <p 
            className="text-[9px] tracking-[0.25em] font-semibold uppercase mt-1"
            style={{ color: 'var(--text-tertiary)' }}
          >
            Your Closet, Curated
          </p>
        </div>

        {/* Slide Content */}
        <div className="px-8 py-8 text-center" style={{ minHeight: '220px' }}>
          {/* Icon */}
          <div 
            className="w-16 h-16 mx-auto mb-5 rounded-2xl flex items-center justify-center transition-all duration-300"
            style={{ 
              background: 'var(--accent-glow)',
              border: '1px solid var(--glass-border)',
            }}
            key={currentSlide} // Re-trigger animation on slide change
          >
            <SlideIcon 
              className="w-8 h-8 animate-fade-in" 
              style={{ color: slide.accent }} 
            />
          </div>

          {/* Text */}
          <h2 
            className="text-xl font-bold mb-3 animate-fade-in"
            style={{ color: 'var(--text-primary)' }}
            key={`title-${currentSlide}`}
          >
            {slide.title}
          </h2>
          <p 
            className="text-sm leading-relaxed animate-fade-in max-w-[260px] mx-auto"
            style={{ color: 'var(--text-secondary)' }}
            key={`sub-${currentSlide}`}
          >
            {slide.subtitle}
          </p>
        </div>

        {/* Navigation Dots */}
        <div className="flex justify-center gap-2 pb-5">
          {slides.map((_, i) => (
            <button
              key={i}
              onClick={() => setCurrentSlide(i)}
              className="transition-all duration-300"
              style={{
                width: i === currentSlide ? '24px' : '8px',
                height: '8px',
                borderRadius: '4px',
                background: i === currentSlide ? 'var(--accent)' : 'var(--glass-border)',
              }}
              aria-label={`Go to slide ${i + 1}`}
            />
          ))}
        </div>

        {/* Actions */}
        <div 
          className="px-6 py-5 flex items-center gap-3"
          style={{ borderTop: '1px solid var(--glass-border)' }}
        >
          {currentSlide > 0 ? (
            <button
              onClick={handlePrev}
              className="px-4 py-3 text-sm font-medium transition-colors"
              style={{ color: 'var(--text-secondary)' }}
            >
              Back
            </button>
          ) : (
            <button
              onClick={handleDismiss}
              className="px-4 py-3 text-sm font-medium transition-colors"
              style={{ color: 'var(--text-tertiary)' }}
            >
              Skip
            </button>
          )}
          
          <button
            onClick={isLast ? handleDismiss : handleNext}
            className="flex-1 btn-primary py-3 flex items-center justify-center gap-2"
          >
            {isLast ? (
              <>
                <span>Get Started</span>
                <ArrowRight className="w-4 h-4" />
              </>
            ) : (
              <>
                <span>Next</span>
                <ChevronRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
