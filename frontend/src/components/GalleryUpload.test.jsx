import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import GalleryUpload from './GalleryUpload'
const api = vi.hoisted(() => ({ processUploadedClothes: vi.fn() }))
vi.mock('../context/WardrobeContext', () => ({ useWardrobe: () => api }))
const photo = (name) => new File(['image'], name, { type: 'image/jpeg' })
const select = (files) =>
  fireEvent.change(screen.getByLabelText('Clothing photos'), {
    target: { files },
  })
const success = { garments: [{ id: 'one' }] }

describe('gallery batch', () => {
  beforeEach(() => {
    api.processUploadedClothes.mockReset()
    api.processUploadedClothes.mockResolvedValue(success)
    let id = 0
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => `blob:${++id}`),
      revokeObjectURL: vi.fn(),
    })
  })
  afterEach(() => vi.unstubAllGlobals())

  it('allows multiple previews and removal before processing', async () => {
    render(<GalleryUpload />)
    expect(screen.getByLabelText('Clothing photos')).toHaveAttribute('multiple')
    const first = photo('first.jpg'),
      second = photo('second.jpg')
    select([first, second])
    expect(screen.getAllByRole('img')).toHaveLength(2)
    fireEvent.click(screen.getByLabelText('Remove first.jpg'))
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:1')
    fireEvent.click(screen.getByRole('button', { name: 'Add clothes' }))
    await screen.findByText('Added 1 piece')
    expect(api.processUploadedClothes).toHaveBeenCalledExactlyOnceWith(second)
  })

  it('processes sequentially, reports progress and retries only the failed photo', async () => {
    let finish
    api.processUploadedClothes
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            finish = resolve
          }),
      )
      .mockRejectedValueOnce(new Error('Could not process this photo'))
      .mockResolvedValueOnce(success)
    render(<GalleryUpload />)
    const first = photo('first.jpg'),
      second = photo('second.jpg')
    select([first, second])
    fireEvent.click(screen.getByRole('button', { name: 'Add clothes' }))
    expect(screen.getByText('Adding photo 1 of 2…')).toBeInTheDocument()
    expect(api.processUploadedClothes).toHaveBeenCalledTimes(1)
    await act(async () => {
      finish(success)
    })
    await screen.findByText('Could not process this photo')
    expect(screen.getByText('Added 1 piece')).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText('Retry second.jpg'))
    await waitFor(() =>
      expect(screen.getAllByText('Added 1 piece')).toHaveLength(2),
    )
    expect(api.processUploadedClothes.mock.calls.map(([file]) => file)).toEqual(
      [first, second, second],
    )
  })

  it('marks empty detections as a retryable failure and continues', async () => {
    api.processUploadedClothes.mockResolvedValueOnce({ garments: [] })
    render(<GalleryUpload />)
    select([photo('empty.jpg'), photo('shirt.jpg')])
    fireEvent.click(screen.getByRole('button', { name: 'Add clothes' }))
    await screen.findByText('Added 1 piece')
    expect(
      screen.getByText('No clothes detected. Try a clearer photo.'),
    ).toBeInTheDocument()
  })

  it('keeps partial successes without retrying the whole photo', async () => {
    api.processUploadedClothes.mockResolvedValueOnce({
      ...success,
      failed_count: 1,
    })
    render(<GalleryUpload />)
    select([photo('outfit.jpg')])
    fireEvent.click(screen.getByRole('button', { name: 'Add clothes' }))
    await screen.findByText('Added 1 piece')
    expect(
      screen.getByText(/Some pieces could not be added/),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /Retry/ }),
    ).not.toBeInTheDocument()
  })

  it('rejects excessive batches and invalid/oversized files before any requests', () => {
    render(<GalleryUpload />)
    select(Array.from({ length: 6 }, (_, i) => photo(`${i}.jpg`)))
    expect(screen.getByRole('alert')).toHaveTextContent('up to 5')
    const huge = photo('huge.jpg')
    Object.defineProperty(huge, 'size', { value: 26 * 1024 * 1024 })
    select([huge])
    expect(screen.getByRole('alert')).toHaveTextContent('25 MB')
    select([new File(['bad'], 'bad.txt', { type: 'text/plain' })])
    expect(screen.queryAllByRole('img')).toHaveLength(0)
    expect(api.processUploadedClothes).not.toHaveBeenCalled()
  })

  it('stops scheduling after unmount and releases preview URLs', async () => {
    let finish
    api.processUploadedClothes.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve
        }),
    )
    const { unmount } = render(<GalleryUpload />)
    select([photo('one.jpg'), photo('two.jpg')])
    fireEvent.click(screen.getByRole('button', { name: 'Add clothes' }))
    unmount()
    expect(URL.revokeObjectURL).toHaveBeenCalledTimes(2)
    await act(async () => {
      finish(success)
    })
    expect(api.processUploadedClothes).toHaveBeenCalledTimes(1)
  })
})
