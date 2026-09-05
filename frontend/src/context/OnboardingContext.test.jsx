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
})
