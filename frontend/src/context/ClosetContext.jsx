/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react'
import { useAuth } from './AuthContext'
const Context = createContext(null)
const base = import.meta.env.VITE_API_URL || ''
export function ClosetProvider({ children }) {
  const { user } = useAuth()
  return <Session key={user?.uid}>{children}</Session>
}
function Session({ children }) {
  const { getIdToken, user } = useAuth()
  const [library, setLibrary] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [draft, setDraft] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem(`wardrub-draft:${user.uid}`))
    } catch {
      return null
    }
  })
  const [readiness, setReadiness] = useState({})
  useEffect(() => {
    try {
      if (draft)
        sessionStorage.setItem(
          `wardrub-draft:${user.uid}`,
          JSON.stringify(draft),
        )
      else sessionStorage.removeItem(`wardrub-draft:${user.uid}`)
    } catch {
      /* In-memory navigation remains available. */
    }
  }, [draft, user.uid])
  const pending = useRef(false)
  const revision = useRef(0)
  const request = useCallback(
    async (path, options = {}) => {
      const token = await getIdToken()
      if (!token) throw new Error('Please sign in again.')
      const controller = new AbortController()
      const timer =
        !options.method || options.method === 'GET'
          ? setTimeout(() => controller.abort(), 30000)
          : null
      try {
        const response = await fetch(`${base}/api${path}`, {
          ...options,
          signal: options.signal || controller.signal,
          headers: {
            'Content-Type': 'application/json',
            ...options.headers,
            Authorization: `Bearer ${token}`,
          },
        })
        const data = await response.json()
        if (!response.ok)
          throw new Error(
            typeof data.detail === 'string'
              ? data.detail
              : 'This change was not confirmed. Please refresh.',
          )
        return data
      } finally {
        if (timer) clearTimeout(timer)
      }
    },
    [getIdToken],
  )
  const reload = useCallback(async () => {
    const current = ++revision.current
    try {
      const [data, state] = await Promise.all([
        request('/closet-library'),
        request('/closet-state'),
      ])
      if (!data.outfits || !data.days)
        throw new Error('Could not read your saved outfits.')
      if (current === revision.current) {
        setLibrary(data)
        setReadiness(
          Object.fromEntries(
            (state.garments || []).map((g) => [g.id, g.readiness]),
          ),
        )
        setError('')
      }
      return data
    } catch (e) {
      if (current === revision.current) setError(e.message)
      throw e
    }
  }, [request])
  useEffect(() => {
    reload().catch(() => {})
  }, [reload])
  const action = async (input) => {
    if (pending.current || !library)
      throw new Error('Please wait for your closet to finish loading.')
    pending.current = true
    setBusy(true)
    setError('')
    ++revision.current
    try {
      const data = await request('/closet-library/actions', {
        method: 'POST',
        body: JSON.stringify({
          ...input,
          expected_version: library.version,
          operation_id: crypto.randomUUID(),
        }),
      })
      ++revision.current
      setLibrary(data)
      return data
    } catch (e) {
      await reload().catch(() => {})
      setError(e.message)
      throw e
    } finally {
      pending.current = false
      setBusy(false)
    }
  }
  return (
    <Context.Provider
      value={{
        library,
        error,
        busy,
        action,
        reload,
        request,
        draft,
        setDraft,
        readiness,
      }}
    >
      {children}
    </Context.Provider>
  )
}
export const useCloset = () => useContext(Context)
