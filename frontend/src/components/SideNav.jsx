import { Link, useLocation } from 'react-router-dom'
import { Sun, Shirt, User } from 'lucide-react'
export default function SideNav() {
  const { pathname } = useLocation()
  return (
    <nav className="quiet-sidebar" aria-label="Main navigation">
      <Link className="brand" to="/">
        Wardrub
      </Link>
      <p className="muted">A little less to think about.</p>
      <Link
        to="/"
        aria-current={
          ['/', '/daily-outfit'].includes(pathname) ? 'page' : undefined
        }
      >
        <Sun size={20} />
        Today
      </Link>
      <Link
        to="/wardrobe"
        aria-current={
          ['/wardrobe', '/looks', '/dressing-room'].includes(pathname)
            ? 'page'
            : undefined
        }
      >
        <Shirt size={20} />
        Wardrobe
      </Link>
      <Link className="sidebar-profile" to="/profile">
        <User size={20} />
        Profile
      </Link>
    </nav>
  )
}
