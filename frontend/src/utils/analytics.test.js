import { beforeEach, describe, expect, it, vi } from 'vitest'
import { trackActivationEvent } from './analytics'

const tokenFor = uid => `header.${btoa(JSON.stringify({ sub: uid }))}.signature`

describe('activation analytics', () => {
  beforeEach(() => {
    window.localStorage.clear()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }))
  })

  it('records each activation milestone only once', async () => {
    const getToken = vi.fn().mockResolvedValue(tokenFor('alice'))

    await trackActivationEvent('avatar_created', getToken, { mode: 'upload' })
    await trackActivationEvent('avatar_created', getToken, { mode: 'upload' })

    expect(fetch).toHaveBeenCalledTimes(1)
    expect(fetch).toHaveBeenCalledWith(
      '/api/analytics/events',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          name: 'avatar_created',
          properties: { mode: 'upload' },
        }),
      }),
    )
  })

  it('does not suppress another user on the same browser', async () => {
    await trackActivationEvent('avatar_created', async () => tokenFor('alice'))
    await trackActivationEvent('avatar_created', async () => tokenFor('bob'))
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('does not mark a failed delivery as complete', async () => {
    fetch.mockResolvedValueOnce({ ok: false }).mockResolvedValueOnce({ ok: true })
    const getToken = vi.fn().mockResolvedValue('token')

    await trackActivationEvent('first_garment_added', getToken)
    await trackActivationEvent('first_garment_added', getToken)

    expect(fetch).toHaveBeenCalledTimes(2)
  })
})
