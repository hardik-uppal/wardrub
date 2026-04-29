import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { 
  signInWithPopup, 
  signOut as firebaseSignOut,
  onAuthStateChanged 
} from 'firebase/auth'
import { auth, googleProvider } from '../config/firebase'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Listen for auth state changes
  useEffect(() => {
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
      const result = await signInWithPopup(auth, googleProvider)
      return result.user
    } catch (err) {
      console.error('Google sign-in error:', err)
      setError(err.message)
      throw err
    }
  }, [])

  // Sign out
  const signOut = useCallback(async () => {
    setError(null)
    try {
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



