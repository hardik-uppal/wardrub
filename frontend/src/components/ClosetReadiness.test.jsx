import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ClosetReadiness from './ClosetReadiness'

const original = { id: 'a', name: 'White tee', category: 'top', readiness: 'unknown', version: 0 }
const response = (data, ok = true) => ({ ok, json: async () => data })

describe('Clothing readiness', () => {
  it('confirms a change and undoes it using the returned version', async () => {
    const request = vi.fn().mockResolvedValueOnce(response({ garments: [original] }))
      .mockResolvedValueOnce(response({ garment: { ...original, readiness: 'laundry', version: 1 } }))
      .mockResolvedValueOnce(response({ garment: { ...original, version: 2 } }))
    const changed = vi.fn()
    render(<ClosetReadiness authFetch={request} apiUrl="" onChanged={changed} />)
    fireEvent.click(screen.getByText('Clothing readiness · 0 in laundry'))
    fireEvent.change(await screen.findByLabelText('White tee · top'), { target: { value: 'laundry' } })
    await screen.findByText('Readiness updated. Outfits refreshed.')
    expect(request).toHaveBeenCalledWith('/api/closet-state/a', { method: 'PUT', body: JSON.stringify({ readiness: 'laundry', expected_version: 0 }) })
    fireEvent.click(screen.getByRole('button', { name: 'Undo last readiness change' }))
    await screen.findByText('Readiness change undone.')
    expect(request).toHaveBeenLastCalledWith('/api/closet-state/a', { method: 'PUT', body: JSON.stringify({ readiness: 'unknown', expected_version: 1 }) })
    expect(changed).toHaveBeenCalledTimes(2)
  })

  it('refreshes after uncertain writes without automatically retrying a mutation', async () => {
    const request = vi.fn().mockResolvedValueOnce(response({ garments: [original] }))
      .mockRejectedValueOnce(new Error('Connection lost.'))
      .mockResolvedValueOnce(response({ garments: [{ ...original, readiness: 'laundry', version: 1 }] }))
    const changed = vi.fn()
    render(<ClosetReadiness authFetch={request} apiUrl="" onChanged={changed} />)
    fireEvent.click(screen.getByText('Clothing readiness · 0 in laundry'))
    fireEvent.change(await screen.findByLabelText('White tee · top'), { target: { value: 'laundry' } })
    await screen.findByRole('alert')
    await waitFor(() => expect(changed).toHaveBeenCalledOnce())
    expect(request.mock.calls.filter(([, options]) => options?.method === 'PUT')).toHaveLength(1)
    expect(screen.queryByRole('button', { name: 'Undo last readiness change' })).not.toBeInTheDocument()
  })
})
