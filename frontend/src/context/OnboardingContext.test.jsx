import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const wardrobeState = vi.hoisted(() => ({
  current: {
    avatarUrl: null,
    garments: [],
    userProfile: null,
  },
}))

vi.mock('./WardrobeContext', () => ({
  useWardrobe: () => wardrobeState.current,
}))

import { OnboardingProvider, useOnboarding } from './OnboardingContext'

function GarmentCountProbe() {
  const { garmentsCount } = useOnboarding()
  return <p>Garments: {garmentsCount}</p>
}

function StyleProbe() {
  const { profileDone, isOnboardingComplete, milestones } = useOnboarding()
  const style = milestones.find(item => item.id === 'style')
  return <>
    <p>Style complete: {String(profileDone)}</p>
    <p>Onboarding complete: {String(isOnboardingComplete)}</p>
    <a href={style.route}>{style.label}</a>
    <p>{style.description}</p>
  </>
}

describe('OnboardingProvider garment progress', () => {
  beforeEach(() => {
    window.localStorage.clear()
    wardrobeState.current = {
      avatarUrl: null,
      garments: [],
      userProfile: null,
    }
  })

  it('counts every garment returned by the wardrobe API', () => {
    wardrobeState.current.garments = [
      { id: 'garment-1' },
      { id: 'mock-prefixed-but-server-owned' },
    ]

    render(
      <OnboardingProvider>
        <GarmentCountProbe />
      </OnboardingProvider>,
    )

    expect(screen.getByText('Garments: 2')).toBeInTheDocument()
  })

  it('keeps fit guidance visible after colors are available, including legacy profiles', () => {
    wardrobeState.current.userProfile = { skin_tone: { season: 'autumn' } }
    wardrobeState.current.avatarUrl = '/avatar.jpg'
    wardrobeState.current.garments = Array.from({ length: 10 }, (_, id) => ({ id }))
    render(<OnboardingProvider><StyleProbe /></OnboardingProvider>)
    expect(screen.getByText('Style complete: false')).toBeInTheDocument()
    expect(screen.getByText('Onboarding complete: false')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Add a full-length photo' })).toHaveAttribute('href', '/profile?analysis=fit')
    expect(screen.getByText(/Your color recommendations are available/)).toBeInTheDocument()
  })

  it('finishes only when both stages are ready and responds to shared profile updates', () => {
    wardrobeState.current.userProfile = { skin_tone: { season: 'autumn' } }
    const { rerender } = render(<OnboardingProvider><StyleProbe /></OnboardingProvider>)
    wardrobeState.current.userProfile = {
      ...wardrobeState.current.userProfile, body_type: 'rectangle',
      style_analysis: { color: { status: 'ready' }, fit: { status: 'ready' } },
    }
    rerender(<OnboardingProvider><StyleProbe /></OnboardingProvider>)
    expect(screen.getByText('Style complete: true')).toBeInTheDocument()
  })

  it('uses backend photo instructions and does not mark an uncertain retry complete', () => {
    wardrobeState.current.userProfile = {
      skin_tone: { season: 'autumn' }, body_type: 'rectangle',
      style_analysis: {
        color: { status: 'ready' },
        fit: { status: 'needs_input', requested_input: { instructions: 'Wear comfortable clothes that follow your shape.' } },
      },
    }
    render(<OnboardingProvider><StyleProbe /></OnboardingProvider>)
    expect(screen.getByText(/Wear comfortable clothes that follow your shape/)).toBeInTheDocument()
    expect(screen.getByText('Style complete: false')).toBeInTheDocument()
  })

  it('offers retry rather than requesting a better photo on provider failure', () => {
    wardrobeState.current.userProfile = { style_analysis: { color: { status: 'failed' } } }
    render(<OnboardingProvider><StyleProbe /></OnboardingProvider>)
    expect(screen.getByRole('link', { name: 'Retry your style analysis' })).toHaveAttribute('href', '/profile?analysis=color')
    expect(screen.getByText(/Retry with the same photos/)).toBeInTheDocument()
  })
})
