import { Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { WardrobeProvider } from './context/WardrobeContext'
import Home from './pages/Home'
import Capture from './pages/Capture'
import DressingRoom from './pages/DressingRoom'
import CreateAvatar from './pages/CreateAvatar'
import MagazineFeed from './pages/MagazineFeed'
import Profile from './pages/Profile'
import SavedLooks from './pages/SavedLooks'
import Login from './pages/Login'
import SideNav from './components/SideNav'
import { Shirt } from 'lucide-react'

// Loading spinner component
function LoadingSpinner() {
  return (
    <div 
      className="min-h-screen flex items-center justify-center"
      style={{ backgroundColor: 'var(--bg-primary)' }}
    >
      <div className="animate-pulse-soft">
        <Shirt className="w-12 h-12" style={{ color: 'var(--accent)' }} />
      </div>
    </div>
  )
}

// Protected layout - wraps all protected routes with WardrobeProvider
// On md+ screens, renders a sidebar nav and offsets the main content area
function ProtectedLayout() {
  const { user, loading } = useAuth()

  if (loading) {
    return <LoadingSpinner />
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return (
    <WardrobeProvider>
      <SideNav />
      <main className="main-layout-content">
        <Outlet />
      </main>
    </WardrobeProvider>
  )
}

// App routes
function AppRoutes() {
  const { loading } = useAuth()

  // Show loading while checking auth state
  if (loading) {
    return <LoadingSpinner />
  }

  return (
    <div className="min-h-screen" style={{ background: 'var(--bg-primary)' }}>
      <Routes>
        {/* Public route */}
        <Route path="/login" element={<Login />} />
        
        {/* Protected routes - all wrapped in ProtectedLayout */}
        <Route element={<ProtectedLayout />}>
        <Route path="/" element={<MagazineFeed />} />
        <Route path="/capture" element={<Capture />} />
        <Route path="/wardrobe" element={<Home />} />
        <Route path="/dressing-room" element={<DressingRoom />} />
        <Route path="/create-avatar" element={<CreateAvatar />} />
        <Route path="/daily-outfit" element={<MagazineFeed />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/looks" element={<SavedLooks />} />
        </Route>
      </Routes>
    </div>
  )
}

function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}

export default App
