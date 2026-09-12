import { fireEvent, render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import UploadPreview from './UploadPreview'

it('explains browser preview failure and retries when a different photo is selected', () => {
  const { rerender } = render(<UploadPreview src="blob:heic" alt="Selected photo" />)
  fireEvent.error(screen.getByRole('img'))
  expect(screen.getByRole('status')).toHaveTextContent('You can still upload')
  rerender(<UploadPreview src="blob:jpeg" alt="New photo" />)
  expect(screen.getByRole('img')).toHaveAccessibleName('New photo')
})
