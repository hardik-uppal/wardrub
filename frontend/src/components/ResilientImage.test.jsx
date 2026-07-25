import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import ResilientImage from './ResilientImage'

describe('ResilientImage', () => {
  it('replaces a failed image with an accessible fallback', () => {
    render(
      <ResilientImage
        src="https://example.com/missing.png"
        alt="Saved look"
      />,
    )

    fireEvent.error(screen.getByRole('img', { name: 'Saved look' }))

    expect(
      screen.getByRole('img', { name: 'Saved look unavailable' }),
    ).toBeInTheDocument()
  })

  it('tries again when the source changes', () => {
    const { rerender } = render(
      <ResilientImage src="/missing.png" alt="Avatar" />,
    )
    fireEvent.error(screen.getByRole('img', { name: 'Avatar' }))

    rerender(<ResilientImage src="/new-avatar.png" alt="Avatar" />)

    expect(screen.getByRole('img', { name: 'Avatar' }))
      .toHaveAttribute('src', '/new-avatar.png')
  })
})
