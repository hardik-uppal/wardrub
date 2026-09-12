import { act, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const auth = vi.hoisted(() => ({ user: { uid: 'alice' }, getIdToken: vi.fn() }))
vi.mock('./AuthContext', () => ({ useAuth: () => auth }))
import { WardrobeProvider, useWardrobe } from './WardrobeContext'

function Probe() {
  const { userProfile, analyzeProfile, fetchProfile } = useWardrobe()
  return <>
    <p>Season: {userProfile?.skin_tone?.season || 'none'}</p>
    <button onClick={() => analyzeProfile([new File(['photo'], 'face.jpg', { type: 'image/jpeg' })], 'color')}>Analyze</button>
    <button onClick={() => fetchProfile()}>Reload</button>
  </>
}

const result = { skin_tone: { season: 'spring' }, style_analysis: { color: { status: 'ready' } } }
const response = data => ({ ok: true, json: async () => data })

describe('WardrobeProvider analysis state', () => {
  beforeEach(() => {
    auth.user = { uid: 'alice' }
    auth.getIdToken.mockResolvedValue('token')
  })
  afterEach(() => vi.unstubAllGlobals())

  it('shares concurrent wardrobe reads and caches empty results', async () => {
    let finish
    vi.stubGlobal('fetch', vi.fn(url => {
      if (url === '/api/wardrobe') return new Promise(resolve => { finish = resolve })
      return Promise.resolve(response({ avatar_url: null, profile: null }))
    }))
    const { result } = renderHook(() => useWardrobe(), { wrapper: WardrobeProvider })
    const firstCallback = result.current.fetchGarments
    let first, second
    act(() => {
      first = result.current.fetchGarments()
      second = result.current.fetchGarments()
    })
    await waitFor(() => expect(finish).toBeTypeOf('function'))
    await act(async () => {
      finish(response({ garments: [] }))
      await Promise.all([first, second])
      await result.current.fetchGarments()
    })
    expect(fetch.mock.calls.filter(([url]) => url === '/api/wardrobe')).toHaveLength(1)
    expect(result.current.fetchGarments).toBe(firstCallback)
  })

  it('preserves loaded garments on failed refresh and retries without caching errors', async () => {
    let failed = false
    vi.stubGlobal('fetch', vi.fn(async url => {
      if (url === '/api/wardrobe') return failed
        ? { ok: false, json: async () => ({ detail: 'offline' }) }
        : response({ garments: [{ id: 'saved' }] })
      return response({ avatar_url: null, profile: null })
    }))
    const { result } = renderHook(() => useWardrobe(), { wrapper: WardrobeProvider })
    await act(async () => { await result.current.fetchGarments() })
    failed = true
    await act(async () => { await result.current.fetchGarments(null, true) })
    expect(result.current.garments).toEqual([{ id: 'saved' }])
    failed = false
    await act(async () => { await result.current.fetchGarments() })
    expect(fetch.mock.calls.filter(([url]) => url === '/api/wardrobe')).toHaveLength(3)
  })

  it('does not let a pending wardrobe refresh resurrect a deleted garment', async () => {
    let finish, delayed = false
    vi.stubGlobal('fetch', vi.fn(url => {
      if (url === '/api/wardrobe') return delayed
        ? new Promise(resolve => { finish = resolve })
        : Promise.resolve(response({ garments: [{ id: 'deleted' }] }))
      return Promise.resolve(response({ avatar_url: null, profile: null }))
    }))
    const { result } = renderHook(() => useWardrobe(), { wrapper: WardrobeProvider })
    await act(async () => { await result.current.fetchGarments() })
    delayed = true
    let refresh
    act(() => { refresh = result.current.fetchGarments(null, true) })
    await waitFor(() => expect(finish).toBeTypeOf('function'))
    await act(async () => { await result.current.deleteGarment('deleted') })
    await act(async () => {
      finish(response({ garments: [{ id: 'deleted' }] }))
      await refresh
    })
    expect(result.current.garments).toEqual([])
  })

  it('clears private data on direct account switch and ignores old responses', async () => {
    let finishAlice
    vi.stubGlobal('fetch', vi.fn(url => {
      if (url === '/api/profile' && auth.user.uid === 'alice') return new Promise(resolve => { finishAlice = resolve })
      return Promise.resolve(response({ avatar_url: auth.user.uid === 'alice' ? 'alice-avatar' : null, profile: null }))
    }))
    const { result, rerender } = renderHook(() => useWardrobe(), { wrapper: WardrobeProvider })
    await waitFor(() => expect(result.current.avatarUrl).toBe('alice-avatar'))
    auth.user = { uid: 'bob' }
    rerender()
    expect(result.current.avatarUrl).toBe(null)
    await act(async () => { finishAlice(response({ profile: { skin_tone: { season: 'spring' } } })) })
    expect(result.current.userProfile).toBe(null)
    expect(fetch.mock.calls.filter(([url]) => url === '/api/avatar')).toHaveLength(2)
  })

  it('ignores a slow initial profile read after a newer analysis succeeds', async () => {
    let finishRead
    vi.stubGlobal('fetch', vi.fn(url => {
      if (url === '/api/profile') return new Promise(resolve => { finishRead = resolve })
      if (url === '/api/profile/analyze') return Promise.resolve(response({ profile: result, status: 'analyzed' }))
      return Promise.resolve(response({ avatar_url: null }))
    }))
    render(<WardrobeProvider><Probe /></WardrobeProvider>)
    await waitFor(() => expect(finishRead).toBeTypeOf('function'))
    fireEvent.click(screen.getByRole('button', { name: 'Analyze' }))
    expect(await screen.findByText('Season: spring')).toBeInTheDocument()
    const request = fetch.mock.calls.find(([url]) => url === '/api/profile/analyze')[1]
    expect(request.body.get('stage')).toBe('color')
    expect(request.body.getAll('files')).toHaveLength(1)
    await act(async () => { finishRead(response({ profile: null })) })
    expect(screen.getByText('Season: spring')).toBeInTheDocument()
  })

  it('restores backend progress on mount and clears it when the backend returns no profile', async () => {
    let saved = result
    vi.stubGlobal('fetch', vi.fn(async url => response(url === '/api/profile' ? { profile: saved } : { avatar_url: null })))
    render(<WardrobeProvider><Probe /></WardrobeProvider>)
    expect(await screen.findByText('Season: spring')).toBeInTheDocument()
    saved = null
    fireEvent.click(screen.getByRole('button', { name: 'Reload' }))
    expect(await screen.findByText('Season: none')).toBeInTheDocument()
  })
})
