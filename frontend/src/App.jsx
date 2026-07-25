import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { WardrobeProvider } from './context/WardrobeContext'
import { OnboardingProvider } from './context/OnboardingContext'
import SideNav from './components/SideNav'
import OnboardingWidget from './components/OnboardingWidget'
import { Shirt } from 'lucide-react'

const Home = lazy(() => import('./pages/Home'))
const Capture = lazy(() => import('./pages/Capture'))
const DressingRoom = lazy(() => import('./pages/DressingRoom'))
const CreateAvatar = lazy(() => import('./pages/CreateAvatar'))
const MagazineFeed = lazy(() => import('./pages/MagazineFeed'))
const Profile = lazy(() => import('./pages/Profile'))
const SavedLooks = lazy(() => import('./pages/SavedLooks'))
const Login = lazy(() => import('./pages/Login'))

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
      <OnboardingProvider>
        <SideNav />
        <main className="main-layout-content">
          <Outlet />
        </main>
        <OnboardingWidget />
      </OnboardingProvider>
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
      <Suspense fallback={<LoadingSpinner />}>
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
      </Suspense>
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
