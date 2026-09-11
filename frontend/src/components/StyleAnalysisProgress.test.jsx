import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import StyleAnalysisProgress from './StyleAnalysisProgress'

describe('StyleAnalysisProgress', () => {
  it('shows available colors while inviting a full-length photo', () => {
    render(<StyleAnalysisProgress profile={{ skin_tone: { season: 'autumn' } }} />)
    expect(screen.getByText('Your colors · Ready')).toBeInTheDocument()
    expect(screen.getByText('Your fit · Photo needed')).toBeInTheDocument()
    expect(screen.getByText('Add a full-length photo for better fit analysis.')).toBeInTheDocument()
  })

  it('preserves useful results and provides an exit from repeated uncertain attempts', () => {
    render(<StyleAnalysisProgress profile={{
      skin_tone: { season: 'autumn' },
      style_analysis: { color: {
        status: 'needs_input', attempts: 3,
        requested_input: { reason: 'Lighting is uneven.', instructions: 'Try indirect daylight.' },
      } },
    }} />)
    expect(screen.getByText('Lighting is uneven.')).toBeInTheDocument()
    expect(screen.getByText('Try indirect daylight.')).toBeInTheDocument()
    expect(screen.getByText(/previous recommendations are still available/)).toBeInTheDocument()
    expect(screen.getByText(/Photos may not resolve this reliably/)).toBeInTheDocument()
  })
})
