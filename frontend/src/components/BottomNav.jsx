import { useNavigate, useLocation } from 'react-router-dom'
import { Shirt, Sun, Sparkles, Image } from 'lucide-react'

const navItems = [
  { path: '/wardrobe', icon: Shirt, label: 'Wardrobe' },
  { path: '/', icon: Sun, label: 'Daily' },
  { path: '/dressing-room', icon: Sparkles, label: 'Try On' },
  { path: '/looks', icon: Image, label: 'Looks' },
]

export default function BottomNav() {
  const navigate = useNavigate()
  const location = useLocation()
  
  const isActive = (path) => {
    if (path === '/') return location.pathname === '/' || location.pathname === '/daily-outfit'
    return location.pathname === path
  }

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white/95 backdrop-blur-md border-t border-[var(--color-warm-gray)]/10 safe-bottom z-40">
      <div className="flex items-center justify-around page-container page-padding py-3 gap-4">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = isActive(item.path)
          
          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className="flex flex-col items-center gap-2 py-2 px-4 min-w-[70px] transition-transform active:scale-95"
            >
              <div className={`w-11 h-11 rounded-full flex items-center justify-center transition-all ${
                active 
                  ? 'bg-[var(--color-terracotta)]/15' 
                  : 'bg-transparent hover:bg-[var(--color-warm-gray)]/10'
              }`}>
                <Icon className={`w-5 h-5 transition-colors ${
                  active ? 'text-[var(--color-terracotta)]' : 'text-[var(--color-warm-gray)]'
                }`} />
              </div>
              <span className={`text-xs font-medium transition-colors ${
                active ? 'text-[var(--color-terracotta)]' : 'text-[var(--color-warm-gray)]'
              }`}>
                {item.label}
              </span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}

