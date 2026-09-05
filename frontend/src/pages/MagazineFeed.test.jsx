import { render, screen } from '@testing-library/react'
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
