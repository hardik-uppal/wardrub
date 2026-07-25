import { act, fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const firebaseMocks = vi.hoisted(() => ({
  onAuthStateChanged: vi.fn(),
  signInWithPopup: vi.fn(),
  signOut: vi.fn(),
}))

vi.mock('firebase/auth', () => firebaseMocks)
vi.mock('../config/firebase', () => ({
  auth: {},
  googleProvider: {},
}))

import { AuthProvider, useAuth } from './AuthContext'

function AuthProbe() {
  const {
    loading,
    user,
    initializationError,
    retryAuthInitialization,
  } = useAuth()

  if (loading) return <p>Checking session</p>
  if (initializationError) {
    return (
      <>
        <p role="alert">{initializationError}</p>
        <button type="button" onClick={retryAuthInitialization}>Retry</button>
      </>
    )
  }
  return <p>{user ? 'Signed in' : 'Signed out'}</p>
}

describe('AuthProvider initialization', () => {
  beforeEach(() => {
    window.localStorage.clear()
    vi.useFakeTimers()
    firebaseMocks.onAuthStateChanged.mockReset()
    firebaseMocks.onAuthStateChanged.mockReturnValue(vi.fn())
  })

  it('recovers from an authentication listener that never responds', async () => {
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    )

    expect(screen.getByText('Checking session')).toBeInTheDocument()

    await act(async () => {
      vi.advanceTimersByTime(10_000)
    })

    expect(screen.getByRole('alert')).toHaveTextContent(
      'We could not verify your sign-in',
    )
  })

  it('allows the failed authentication check to be retried', async () => {
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    )

    await act(async () => {
      vi.advanceTimersByTime(10_000)
    })
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))

    expect(screen.getByText('Checking session')).toBeInTheDocument()
    expect(firebaseMocks.onAuthStateChanged).toHaveBeenCalledTimes(2)
  })
})
