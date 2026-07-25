/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { 
  signInWithPopup, 
  signOut as firebaseSignOut,
  onAuthStateChanged 
} from 'firebase/auth'
import { auth, googleProvider } from '../config/firebase'
import { trackActivationEvent } from '../utils/analytics'

const AuthContext = createContext(null)
const AUTH_INITIALIZATION_TIMEOUT_MS = 10_000
const DEV_AUTH_STORAGE_KEY = 'dev_mock_user'
const DEV_AUTH_BYPASS_ENABLED =
  import.meta.env.DEV && import.meta.env.VITE_ENABLE_DEV_AUTH_BYPASS === 'true'

function readStoredDevUser() {
  if (!DEV_AUTH_BYPASS_ENABLED) {
    window.localStorage.removeItem(DEV_AUTH_STORAGE_KEY)
    return null
  }

  const storedDevUser = window.localStorage.getItem(DEV_AUTH_STORAGE_KEY)
  if (!storedDevUser) return null

  try {
    const parsed = JSON.parse(storedDevUser)
    parsed.getIdToken = async () => 'dev-mock-admin-token'
    return parsed
  } catch (err) {
    console.error('Failed to parse stored dev user:', err)
    window.localStorage.removeItem(DEV_AUTH_STORAGE_KEY)
    return null
  }
}

function isDevAuthUser(user) {
  return DEV_AUTH_BYPASS_ENABLED && (
    user?.uid === 'dev-admin-user-id' ||
    user?.uid?.startsWith('mock-token-')
  )
}

export function AuthProvider({ children }) {
  const [initialDevUser] = useState(readStoredDevUser)
  const [user, setUser] = useState(initialDevUser)
  const [loading, setLoading] = useState(!initialDevUser)
  const [error, setError] = useState(null)
  const [initializationError, setInitializationError] = useState(null)
  const [authAttempt, setAuthAttempt] = useState(0)

  // Listen for auth state changes
  useEffect(() => {
    if (initialDevUser) return

    let active = true
    let unsubscribe = () => {}

    const finishInitialization = (nextUser, nextError = null) => {
      if (!active) return
      window.clearTimeout(timeoutId)
      setUser(nextUser)
      setInitializationError(nextError)
      setLoading(false)
    }

    const timeoutId = window.setTimeout(() => {
      finishInitialization(
        null,
        'We could not verify your sign-in. Check your connection and try again.',
      )
    }, AUTH_INITIALIZATION_TIMEOUT_MS)

    try {
      unsubscribe = onAuthStateChanged(
        auth,
        (nextUser) => finishInitialization(nextUser),
        (authError) => {
          console.error('Authentication initialization failed:', authError)
          finishInitialization(
            null,
            'We could not verify your sign-in. Check your connection and try again.',
          )
        },
      )
    } catch (authError) {
      console.error('Authentication initialization failed:', authError)
      finishInitialization(
        null,
        'We could not verify your sign-in. Check your connection and try again.',
      )
    }

    return () => {
      active = false
      window.clearTimeout(timeoutId)
      unsubscribe()
    }
  }, [authAttempt, initialDevUser])

  const retryAuthInitialization = useCallback(() => {
    setInitializationError(null)
    setLoading(true)
    setAuthAttempt(attempt => attempt + 1)
  }, [])

  // Sign in with Google
  const signInWithGoogle = useCallback(async () => {
    setError(null)
    try {
      window.localStorage.removeItem(DEV_AUTH_STORAGE_KEY)
      const result = await signInWithPopup(auth, googleProvider)
      void trackActivationEvent(
        'sign_in_completed',
        () => result.user.getIdToken(),
        { provider: 'google' },
      )
      return result.user
    } catch (err) {
      console.error('Google sign-in error:', err)
      setError(err.message)
      throw err
    }
  }, [])

  // Dev bypass sign in
  const signInWithDevBypass = useCallback(async (uid = 'dev-admin-user-id') => {
    if (!DEV_AUTH_BYPASS_ENABLED) {
      throw new Error('Developer authentication is only available in local development.')
    }

    setError(null)
    const mockUser = {
      uid,
      email: 'admin@wardrub.test',
      displayName: 'Dev Admin',
      photoURL: 'https://lh3.googleusercontent.com/a/default-user=s96-c',
    }
    window.localStorage.setItem(DEV_AUTH_STORAGE_KEY, JSON.stringify(mockUser))
    mockUser.getIdToken = async () => 'dev-mock-admin-token'
    setUser(mockUser)
    return mockUser
  }, [])

  // Sign out
  const signOut = useCallback(async () => {
    setError(null)
    try {
      window.localStorage.removeItem(DEV_AUTH_STORAGE_KEY)
      await firebaseSignOut(auth)
      setUser(null)
    } catch (err) {
      console.error('Sign out error:', err)
      setError(err.message)
      throw err
    }
  }, [])

  // Get the current user's ID token for API calls
  const getIdToken = useCallback(async () => {
    if (!user) {
      return null
    }
    if (isDevAuthUser(user)) {
      return 'dev-mock-admin-token'
    }
    try {
      const token = await user.getIdToken()
      return token
    } catch (err) {
      console.error('Failed to get ID token:', err)
      return null
    }
  }, [user])

  // Get the current user's ID token, refreshing if necessary
  const getIdTokenFresh = useCallback(async () => {
    if (!user) {
      return null
    }
    if (isDevAuthUser(user)) {
      return 'dev-mock-admin-token'
    }
    try {
      const token = await user.getIdToken(true) // Force refresh
      return token
    } catch (err) {
      console.error('Failed to refresh ID token:', err)
      return null
    }
  }, [user])

  const value = {
    user,
    loading,
    error,
    initializationError,
    isAuthenticated: !!user,
    isDevAuthBypassEnabled: DEV_AUTH_BYPASS_ENABLED,
    signInWithGoogle,
    signInWithDevBypass,
    signOut,
    retryAuthInitialization,
    getIdToken,
    getIdTokenFresh,
    clearError: () => setError(null),
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
