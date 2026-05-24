/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { 
  signInWithPopup, 
  signOut as firebaseSignOut,
  onAuthStateChanged 
} from 'firebase/auth'
import { auth, googleProvider } from '../config/firebase'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const storedDevUser = localStorage.getItem('dev_mock_user')
    if (storedDevUser) {
      try {
        const parsed = JSON.parse(storedDevUser)
        parsed.getIdToken = async () => 'dev-mock-admin-token'
        return parsed
      } catch (err) {
        console.error('Failed to parse stored dev user:', err)
      }
    }
    return null
  })
  const [loading, setLoading] = useState(() => {
    return !localStorage.getItem('dev_mock_user')
  })
  const [error, setError] = useState(null)

  // Listen for auth state changes
  useEffect(() => {
    if (localStorage.getItem('dev_mock_user')) {
      return
    }

    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setUser(user)
      setLoading(false)
    })

    return () => unsubscribe()
  }, [])

  // Sign in with Google
  const signInWithGoogle = useCallback(async () => {
    setError(null)
    try {
      localStorage.removeItem('dev_mock_user')
      const result = await signInWithPopup(auth, googleProvider)
      return result.user
    } catch (err) {
      console.error('Google sign-in error:', err)
      setError(err.message)
      throw err
    }
  }, [])

  // Dev bypass sign in
  const signInWithDevBypass = useCallback(async (uid = 'dev-admin-user-id') => {
    setError(null)
    const mockUser = {
      uid,
      email: 'admin@wardrub.test',
      displayName: 'Dev Admin',
      photoURL: 'https://lh3.googleusercontent.com/a/default-user=s96-c',
    }
    localStorage.setItem('dev_mock_user', JSON.stringify(mockUser))
    mockUser.getIdToken = async () => 'dev-mock-admin-token'
    setUser(mockUser)
    return mockUser
  }, [])

  // Sign out
  const signOut = useCallback(async () => {
    setError(null)
    try {
      localStorage.removeItem('dev_mock_user')
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
    if (user.uid === 'dev-admin-user-id' || user.uid.startsWith('mock-token-')) {
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
    if (user.uid === 'dev-admin-user-id' || user.uid.startsWith('mock-token-')) {
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
    isAuthenticated: !!user,
    signInWithGoogle,
    signInWithDevBypass,
    signOut,
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



