import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  getIdToken: vi.fn(), analyzeProfile: vi.fn(), fetchProfile: vi.fn(), checkLegacyData: vi.fn(), userProfile: null,
}))
vi.mock('../context/AuthContext', () => ({ useAuth: () => ({ getIdToken: mocks.getIdToken }) }))
vi.mock('../context/WardrobeContext', () => ({ useWardrobe: () => mocks }))
vi.mock('../components/BottomNav', () => ({ default: () => null }))
import Profile from './Profile'

const colors = { best: ['Coral'], good: ['Ivory'], avoid: [] }
const profile = {
  skin_tone: { season: 'spring', undertone: 'warm', depth: 'medium' },
  style_analysis: { color: { status: 'ready' }, fit: { status: 'needs_input' } },
}

describe('Profile style analysis', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getIdToken.mockResolvedValue('token')
    mocks.checkLegacyData.mockResolvedValue(false)
    mocks.userProfile = profile
    mocks.fetchProfile.mockResolvedValue({ profile })
    vi.stubGlobal('fetch', vi.fn(async url => ({
      ok: true,
      json: async () => url.includes('color-recommendations') ? { recommendations: colors } : { profile },
    })))
  })
  afterEach(() => vi.unstubAllGlobals())

  it('loads saved colors, requests fit photos, and submits the focused stage', async () => {
    const updated = { ...profile, body_type: 'rectangle', style_analysis: { color: { status: 'ready' }, fit: { status: 'ready' } } }
    mocks.analyzeProfile.mockImplementation(async () => {
      mocks.userProfile = updated
      return { profile: updated, color_recommendations: colors, fit_recommendations: null, status: 'analyzed' }
    })
    render(<MemoryRouter initialEntries={['/profile?analysis=fit']}><Profile /></MemoryRouter>)
    expect(await screen.findByText('Coral')).toBeInTheDocument()
    expect(screen.getByText('Your fit · Photo needed')).toBeInTheDocument()
    expect(mocks.fetchProfile).toHaveBeenCalled()
    const file = new File(['photo'], 'full-length.jpg', { type: 'image/jpeg' })
    fireEvent.change(screen.getByLabelText('Choose style analysis photos'), { target: { files: [file] } })
    fireEvent.click(screen.getByRole('button', { name: 'Analyze My Style' }))
    await waitFor(() => expect(mocks.analyzeProfile).toHaveBeenCalledWith([file], 'fit'))
    expect(await screen.findByText('Your fit · Ready')).toBeInTheDocument()
    expect(screen.getByText('Coral')).toBeInTheDocument()
  })

  it('retains selected files and available colors on provider failure', async () => {
    let finishAnalysis
    mocks.analyzeProfile.mockImplementationOnce(() => {
      mocks.userProfile = { ...profile, style_analysis: { ...profile.style_analysis, fit: { status: 'failed' } } }
      // Shared profile progress may render before the caller's await/finally finishes.
      return new Promise(resolve => {
        finishAnalysis = () => resolve({ profile: mocks.userProfile, color_recommendations: colors, fit_recommendations: null, status: 'failed' })
      })
    })
    render(<MemoryRouter><Profile /></MemoryRouter>)
    await screen.findByText('Coral')
    const file = new File(['photo'], 'face.png', { type: 'image/png' })
    fireEvent.change(screen.getByLabelText('Choose style analysis photos'), { target: { files: [file] } })
    fireEvent.click(screen.getByRole('button', { name: 'Analyze My Style' }))
    expect(await screen.findByText('Your fit · Retry available')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Analyze My Style' })).toBeDisabled()
    await act(async () => { finishAnalysis() })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Analyze My Style' })).toBeEnabled())
    expect(screen.getByText('1 selected')).toBeInTheDocument()
    expect(screen.getByText('Coral')).toBeInTheDocument()

    mocks.analyzeProfile.mockResolvedValueOnce({ profile: mocks.userProfile, color_recommendations: colors, fit_recommendations: null, status: 'failed' })
    fireEvent.click(screen.getByRole('button', { name: 'Analyze My Style' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Analyze My Style' })).toBeEnabled())
    expect(mocks.analyzeProfile).toHaveBeenCalledTimes(2)
    expect(mocks.analyzeProfile.mock.calls[1][0]).toEqual([file])
  })

  it('rejects unsupported uploads before making an analysis request', async () => {
    render(<MemoryRouter><Profile /></MemoryRouter>)
    await screen.findByText('Coral')
    fireEvent.change(screen.getByLabelText('Choose style analysis photos'), { target: { files: [new File(['fake'], 'document.pdf', { type: 'application/pdf' })] } })
    expect(screen.getByText('Use JPEG, PNG, or WebP photos.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Analyze My Style' })).not.toBeInTheDocument()
    expect(mocks.analyzeProfile).not.toHaveBeenCalled()
  })

  it('shows an analysis that finishes after returning to the page', async () => {
    const { rerender } = render(<MemoryRouter><Profile /></MemoryRouter>)
    await screen.findByText('Coral')
    mocks.userProfile = { ...profile, body_type: 'rectangle', style_analysis: { color: { status: 'ready' }, fit: { status: 'ready' } } }
    rerender(<MemoryRouter><Profile /></MemoryRouter>)
    expect(await screen.findByText('Your fit · Ready')).toBeInTheDocument()
    expect(screen.getByText('Coral')).toBeInTheDocument()
  })

  it('shows color recommendations even if loading fit recommendations fails', async () => {
    mocks.userProfile = { ...profile, body_type: 'rectangle' }
    fetch.mockImplementation(async url => ({
      ok: !url.includes('fit-recommendations'),
      json: async () => ({ recommendations: colors }),
    }))
    render(<MemoryRouter><Profile /></MemoryRouter>)
    expect(await screen.findByText('Coral')).toBeInTheDocument()
    expect(await screen.findByText(/Could not load your recommendations/)).toBeInTheDocument()
  })

  it('shows a profile load failure instead of silently presenting an empty analysis', async () => {
    mocks.userProfile = null
    mocks.fetchProfile.mockResolvedValue({ error: 'Failed to load your profile. Please reload to retry.' })
    render(<MemoryRouter><Profile /></MemoryRouter>)
    expect(await screen.findByText('Failed to load your profile. Please reload to retry.')).toBeInTheDocument()
  })
})
