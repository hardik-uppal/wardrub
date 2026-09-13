import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  garments: [],
  fetchGarments: vi.fn(),
  getIdToken: vi.fn(),
  navigate: vi.fn(),
}))

vi.mock('react-router-dom', () => ({
  useNavigate: () => mocks.navigate,
}))

vi.mock('../context/WardrobeContext', () => ({
  useWardrobe: () => ({
    avatarUrl: null,
    garments: mocks.garments,
    fetchGarments: mocks.fetchGarments,
  }),
}))

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ getIdToken: mocks.getIdToken }),
}))

vi.mock('../context/OnboardingContext', () => ({
  useOnboarding: () => ({
    milestones: [],
    overallProgress: 0,
    GARMENT_GOAL: 10,
  }),
}))

vi.mock('../components/BottomNav', () => ({ default: () => null }))

import MagazineFeed from './MagazineFeed'

describe('MagazineFeed onboarding', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getIdToken.mockResolvedValue('token')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      json: async () => ({ status: 'onboarding' }),
    }))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('labels the returned edition date, not the browser date or Issue 01', async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date('2026-09-13T01:00:00Z'))
    fetch.mockResolvedValue({ json: async () => ({ status: 'success', feed: { date: '2026-09-12' } }) })
    render(<MagazineFeed />)
    expect(await screen.findByText('SEP 12, 2026 · UTC')).toBeInTheDocument()
    expect(screen.getByText('DAILY EDITION')).toBeInTheDocument()
    expect(screen.queryByText('ISSUE NO. 01')).not.toBeInTheDocument()
  })

  it('checks a new day on focus without forcing regeneration or repeated requests', async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date('2026-09-12T23:59:00Z'))
    let day = '2026-09-12'
    fetch.mockImplementation(async () => ({ json: async () => ({ status: 'success', feed: { date: day } }) }))
    // Flush the successful read and passive listener effect before sending focus.
    // Seeing the masthead alone does not prove the focus listener is installed.
    await act(async () => { render(<MagazineFeed />) })
    await screen.findByText('SEP 12, 2026 · UTC')
    fireEvent.focus(window)
    expect(fetch).toHaveBeenCalledTimes(1)
    day = '2026-09-13'
    vi.setSystemTime(new Date('2026-09-13T00:01:00Z'))
    fireEvent.focus(window)
    fireEvent.focus(window)
    await screen.findByText('SEP 13, 2026 · UTC')
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(fetch.mock.calls.every(([, options]) => options.method === 'GET')).toBe(true)
    fireEvent.focus(window)
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('skips hidden tabs and does not automatically retry a failed daily read', async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date('2026-09-12T23:59:00Z'))
    fetch.mockResolvedValueOnce({ json: async () => ({ status: 'success', feed: { date: '2026-09-12' } }) })
    await act(async () => { render(<MagazineFeed />) })
    await screen.findByText('SEP 12, 2026 · UTC')
    vi.setSystemTime(new Date('2026-09-13T00:01:00Z'))
    const visibility = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden')
    fireEvent.focus(window)
    expect(fetch).toHaveBeenCalledTimes(1)
    visibility.mockReturnValue('visible')
    fetch.mockResolvedValueOnce({ json: async () => ({ status: 'failed' }) })
    await act(async () => { fireEvent(document, new Event('visibilitychange')) })
    expect(fetch).toHaveBeenCalledTimes(2)
    await act(async () => { fireEvent.focus(window) })
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('checks rollover in a visible open tab and cleans up the timer', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    vi.setSystemTime(new Date('2026-09-12T23:59:30Z'))
    fetch.mockImplementation(async () => ({ json: async () => ({ status: 'success', feed: { date: new Date().toISOString().slice(0, 10) } }) }))
    let view
    await act(async () => { view = render(<MagazineFeed />) })
    await screen.findByText('SEP 12, 2026 · UTC')
    await act(async () => { await vi.advanceTimersByTimeAsync(60000) })
    expect(await screen.findByText('SEP 13, 2026 · UTC')).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledTimes(2)
    view.unmount()
    await act(async () => { await vi.advanceTimersByTimeAsync(86400000) })
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('keeps explicit refresh as a POST and does not invent dates for legacy responses', async () => {
    fetch.mockResolvedValue({ json: async () => ({ status: 'success', feed: {} }) })
    render(<MagazineFeed />)
    await screen.findByText('EDITION DATE UNAVAILABLE')
    fireEvent.click(screen.getByRole('button', { name: 'REFRESH ISSUE' }))
    await waitFor(() => expect(fetch).toHaveBeenCalledWith('/api/magazine-feed/generate', expect.objectContaining({ method: 'POST' })))
  })

  it('discloses failed refreshes instead of silently displaying stale suggestions', async () => {
    fetch.mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'success', feed: { date: '2026-09-12' } }) })
    await act(async () => { render(<MagazineFeed />) })
    fetch.mockResolvedValueOnce({ ok: false, json: async () => ({ detail: 'Storage unavailable' }) })
    fireEvent.click(screen.getByRole('button', { name: 'REFRESH ISSUE' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('may be out of date')
    fetch.mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'success', feed: { date: '2026-09-13' } }) })
    fireEvent.click(screen.getByRole('button', { name: 'Retry outfits' }))
    await screen.findByText('SEP 13, 2026 · UTC')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('offers only the real wardrobe flow and never requests demo data', async () => {
    render(<MagazineFeed />)

    expect(
      await screen.findByRole('button', { name: 'Capture Clothes' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /demo closet/i }),
    ).not.toBeInTheDocument()

    expect(fetch).toHaveBeenCalledWith(
      '/api/magazine-feed',
      expect.objectContaining({ method: 'GET' }),
    )
    expect(fetch.mock.calls.flat().join(' ')).not.toContain('mock=true')
  })
})


describe('grounded outfit actions', () => {
  const look = { id: 'original', title: 'Starting outfit', garment_ids: ['a', 'b'], score: 0.8,
    policy_version: 'closet-rules-v1', why_it_works: 'Check readiness.', swaps: [], styling_tips: [] }
  const feed = { date: '2026-09-13', policy_version: 'closet-rules-v1', weather_status: 'no_location', cover_look: look, daily_fits: [] }
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getIdToken.mockResolvedValue('token')
    mocks.garments = [{ id: 'a', category: 'top' }, { id: 'b', category: 'bottom' }, { id: 'c', category: 'top' }]
    vi.stubGlobal('fetch', vi.fn(async (url) => ({ ok: true, json: async () =>
      url.endsWith('/closet-state') ? { garments: [] } : { status: 'success', feed } })))
  })
  afterEach(() => { mocks.garments = []; vi.unstubAllGlobals(); vi.restoreAllMocks() })

  it('shows unknown weather and makes a server-validated one-piece swap', async () => {
    render(<MagazineFeed />)
    expect(await screen.findByText('No location set. These suggestions do not use weather.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'View details for Starting outfit' }))
    fetch.mockImplementation(async (url) => ({ ok: true, json: async () => url.endsWith('/outfits/swap')
      ? { status: 'success', look: { ...look, id: 'changed', title: 'Changed outfit', garment_ids: ['c', 'b'] } }
      : { garments: [] } }))
    fireEvent.click(screen.getByRole('button', { name: 'Swap Top' }))
    await waitFor(() => expect(fetch).toHaveBeenCalledWith('/api/outfits/swap', expect.objectContaining({
      method: 'POST', body: JSON.stringify({ garment_ids: ['a', 'b'], replace_item_id: 'a' }),
    })))
    expect((await screen.findAllByText('Changed outfit')).length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: 'Swap Bottom' })).toBeInTheDocument()
    expect(screen.queryByText('Strong match')).not.toBeInTheDocument()
  })

  it('keeps the original outfit when no replacement exists', async () => {
    render(<MagazineFeed />)
    fireEvent.click(await screen.findByRole('button', { name: 'View details for Starting outfit' }))
    fetch.mockResolvedValue({ ok: true, json: async () => ({ status: 'no_alternative', look: null }) })
    fireEvent.click(screen.getByRole('button', { name: 'Swap Top' }))
    expect((await screen.findAllByText('No available alternative for this piece. Your outfit is unchanged.')).length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: 'View details for Starting outfit' })).toBeInTheDocument()
  })

  it('shows server conflict and never displays an unavailable replacement', async () => {
    render(<MagazineFeed />)
    fireEvent.click(await screen.findByRole('button', { name: 'View details for Starting outfit' }))
    fetch.mockResolvedValue({ ok: false, json: async () => ({ detail: 'Another piece is unavailable. Refresh your outfit first' }) })
    fireEvent.click(screen.getByRole('button', { name: 'Swap Top' }))
    expect((await screen.findAllByText('Another piece is unavailable. Refresh your outfit first')).length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: 'View details for Starting outfit' })).toBeInTheDocument()
  })

  it('keeps laundry controls reachable when no viable outfit exists', async () => {
    fetch.mockImplementation(async url => ({ ok: true, json: async () => url.endsWith('/closet-state')
      ? { garments: [] } : { status: 'success', feed: { ...feed, cover_look: null } } }))
    render(<MagazineFeed />)
    expect(await screen.findByText('No outfit available yet')).toBeInTheDocument()
    expect(screen.getByText('Clothing readiness · 0 in laundry')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Capture Clothes' })).toBeInTheDocument()
  })
})
