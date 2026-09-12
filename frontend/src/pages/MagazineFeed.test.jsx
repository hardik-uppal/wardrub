import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
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
    garments: [],
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
