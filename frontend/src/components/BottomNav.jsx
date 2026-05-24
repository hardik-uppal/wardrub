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
    <nav
      className="fixed bottom-0 left-0 right-0 md:hidden safe-bottom z-40"
      style={{
        background: 'var(--bg-secondary)',
        borderTop: '1px solid var(--glass-border)',
      }}
    >
      <div className="flex items-center justify-around px-2 py-2 max-w-lg mx-auto">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = isActive(item.path)
          
          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className="flex flex-col items-center gap-1 py-2 px-3 min-w-[60px] transition-all active:scale-90"
            >
              <div
                className="w-10 h-10 rounded-md flex items-center justify-center transition-all relative"
                style={{
                  background: active ? 'var(--accent-glow)' : 'transparent',
                }}
              >
                <Icon
                  className="w-5 h-5 transition-colors"
                  style={{
                    color: active ? 'var(--accent-light)' : 'var(--text-tertiary)',
                  }}
                />
                {/* Active dot indicator */}
                {active && (
                  <div
                    className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full"
                    style={{ background: 'var(--accent)' }}
                  />
                )}
              </div>
              <span
                className="text-[10px] font-medium transition-colors"
                style={{
                  color: active ? 'var(--accent-light)' : 'var(--text-tertiary)',
                }}
              >
                {item.label}
              </span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}
