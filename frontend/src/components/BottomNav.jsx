import { NavLink } from 'react-router-dom'
import { Sun, Shirt } from 'lucide-react'
export default function BottomNav() {
  return (
    <nav className="quiet-bottom" aria-label="Main navigation">
      <NavLink to="/" end>
        <Sun size={20} />
        Today
      </NavLink>
      <NavLink to="/wardrobe">
        <Shirt size={20} />
        Wardrobe
      </NavLink>
    </nav>
  )
}
