import { Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { WardrobeProvider } from './context/WardrobeContext'
import Home from './pages/Home'
import Capture from './pages/Capture'
import DressingRoom from './pages/DressingRoom'
import CreateAvatar from './pages/CreateAvatar'
import DailyOutfit from './pages/DailyOutfit'
import Profile from './pages/Profile'
import SavedLooks from './pages/SavedLooks'
import Login from './pages/Login'
import { Shirt } from 'lucide-react'

// Loading spinner component
function LoadingSpinner() {
  return (
    <div 
      className="min-h-screen flex items-center justify-center"
      style={{ backgroundColor: 'var(--color-cream)' }}
    >
      <div className="animate-pulse-soft">
        <Shirt className="w-12 h-12" style={{ color: 'var(--color-terracotta)' }} />
      </div>
    </div>
  )
}

// Protected layout - wraps all protected routes with WardrobeProvider
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
      <Outlet />
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
    <div className="min-h-screen bg-[var(--color-cream)]">
      <Routes>
        {/* Public route */}
        <Route path="/login" element={<Login />} />
        
        {/* Protected routes - all wrapped in ProtectedLayout */}
        <Route element={<ProtectedLayout />}>
        <Route path="/" element={<DailyOutfit />} />
        <Route path="/capture" element={<Capture />} />
        <Route path="/wardrobe" element={<Home />} />
        <Route path="/dressing-room" element={<DressingRoom />} />
        <Route path="/create-avatar" element={<CreateAvatar />} />
        <Route path="/daily-outfit" element={<DailyOutfit />} />
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
