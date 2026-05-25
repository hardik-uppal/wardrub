import { useNavigate, useLocation } from 'react-router-dom'
import { Shirt, BookOpen, Sparkles, Image, User } from 'lucide-react'
import { useWardrobe } from '../context/WardrobeContext'

const navItems = [
  { path: '/', icon: BookOpen, label: 'Feed' },
  { path: '/wardrobe', icon: Shirt, label: 'Wardrobe' },
  { path: '/dressing-room', icon: Sparkles, label: 'Try On' },
  { path: '/looks', icon: Image, label: 'Looks' },
]

export default function SideNav() {
  const navigate = useNavigate()
  const location = useLocation()
  const { avatarUrl } = useWardrobe()

  const isActive = (path) => {
    if (path === '/') return location.pathname === '/' || location.pathname === '/daily-outfit'
    return location.pathname === path
  }

  return (
    <nav
      className="hidden md:flex fixed left-0 top-0 bottom-0 flex-col z-40"
      style={{
        width: 'var(--sidebar-width)',
        background: 'var(--bg-secondary)',
        borderRight: '1px solid var(--glass-border)',
      }}
    >
      {/* Brand */}
      <div
        className="flex items-center gap-3 px-6 py-7"
        style={{ borderBottom: '1px solid var(--glass-border)' }}
      >
        <div
          className="w-10 h-10 rounded-md flex items-center justify-center flex-shrink-0"
          style={{ background: 'var(--accent)' }}
        >
          <Shirt className="w-5 h-5 text-white" />
        </div>
        <span
          className="text-lg font-bold"
          style={{ fontFamily: "'Playfair Display', Georgia, serif", color: 'var(--text-primary)' }}
        >
          Wardrub
        </span>
      </div>

      {/* Nav Items */}
      <div className="flex-1 flex flex-col gap-1 px-4 py-5">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = isActive(item.path)

          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className="flex items-center gap-3 px-4 py-3 rounded-md transition-all group relative"
              style={{
                background: active ? 'var(--glass-bg-elevated)' : 'transparent',
                border: active ? '1px solid var(--glass-border-hover)' : '1px solid transparent',
              }}
            >
              {/* Active indicator bar */}
              {active && (
                <div
                  className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-8 rounded-full"
                  style={{ background: 'var(--accent)' }}
                />
              )}
              <div
                className="w-9 h-9 rounded-md flex items-center justify-center flex-shrink-0 transition-all"
                style={{
                  background: active ? 'var(--accent-glow)' : 'transparent',
                }}
              >
                <Icon
                  className="w-[18px] h-[18px] transition-colors"
                  style={{
                    color: active ? 'var(--accent-light)' : 'var(--text-tertiary)',
                  }}
                />
              </div>
              <span
                className="text-sm font-medium transition-colors"
                style={{
                  color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                }}
              >
                {item.label}
              </span>
            </button>
          )
        })}
      </div>

      {/* Profile Link at Bottom */}
      <div className="px-4 py-4" style={{ borderTop: '1px solid var(--glass-border)' }}>
        <button
          onClick={() => navigate('/profile')}
          className="flex items-center gap-3 px-4 py-3 rounded-md transition-all group w-full relative"
          style={{
            background: location.pathname === '/profile' ? 'var(--glass-bg-elevated)' : 'transparent',
            border: location.pathname === '/profile' ? '1px solid var(--glass-border-hover)' : '1px solid transparent',
          }}
        >
          {location.pathname === '/profile' && (
            <div
              className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-8 rounded-full"
              style={{ background: 'var(--accent)' }}
            />
          )}
          <div
            className="w-9 h-9 rounded-full overflow-hidden flex items-center justify-center flex-shrink-0"
            style={{
              background: avatarUrl ? 'transparent' : (location.pathname === '/profile' ? 'var(--accent-glow)' : 'var(--glass-bg)'),
              border: avatarUrl ? '1px solid var(--accent)' : 'none',
            }}
          >
            {avatarUrl ? (
              <img 
                src={avatarUrl} 
                alt="Avatar" 
                className="w-full h-full object-cover" 
                style={{ objectPosition: 'top center' }}
              />
            ) : (
              <User
                className="w-[18px] h-[18px]"
                style={{
                  color: location.pathname === '/profile' ? 'var(--accent-light)' : 'var(--text-tertiary)',
                }}
              />
            )}
          </div>
          <span
            className="text-sm font-medium transition-colors"
            style={{
              color: location.pathname === '/profile' ? 'var(--text-primary)' : 'var(--text-secondary)',
            }}
          >
            Profile
          </span>
        </button>
      </div>
    </nav>
  )
}
