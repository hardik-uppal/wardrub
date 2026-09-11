import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
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
    auth.getIdToken.mockResolvedValue('token')
  })
  afterEach(() => vi.unstubAllGlobals())

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
