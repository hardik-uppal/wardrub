import { Link } from 'react-router-dom'
import { ArrowLeft, User } from 'lucide-react'
export function PageHeader({ title, subtitle, back, children }) {
  return (
    <header className="quiet-header">
      <div className="quiet-heading">
        {back && (
          <Link className="icon-control" to={back} aria-label="Back">
            <ArrowLeft size={20} />
          </Link>
        )}
        <div>
          <p className="eyebrow">Wardrub</p>
          <h1>{title}</h1>
          {subtitle && <p className="muted">{subtitle}</p>}
        </div>
      </div>
      <div className="actions">
        {children}
        {title !== 'Profile' && (
          <Link
            className="icon-control"
            to="/profile"
            aria-label="Open profile"
          >
            <User size={20} />
          </Link>
        )}
      </div>
    </header>
  )
}
export function WardrobeTabs({ active }) {
  return (
    <nav className="wardrobe-tabs" aria-label="Wardrobe sections">
      <Link
        to="/wardrobe"
        aria-current={active === 'items' ? 'page' : undefined}
      >
        Items
      </Link>
      <Link
        to="/looks"
        aria-current={active === 'outfits' ? 'page' : undefined}
      >
        Outfits
      </Link>
    </nav>
  )
}
