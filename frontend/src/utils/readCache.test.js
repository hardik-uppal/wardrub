import { describe, expect, it, vi } from 'vitest'
import { createReadCache } from './readCache'

const deferred = () => {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

describe('private read cache', () => {
  it('coalesces simultaneous consumers including forced reads', async () => {
    const cache = createReadCache()
    const pending = deferred()
    const load = vi.fn(() => pending.promise)
    const a = cache.read('garments:all', load)
    const b = cache.read('garments:all', load, true)
    pending.resolve([])
    const [first, second] = await Promise.all([a, b])
    expect(load).toHaveBeenCalledTimes(1)
    expect(first.value).toBe(second.value)
  })

  it('caches empty results but expires them and supports explicit refresh', async () => {
    let now = 0
    const cache = createReadCache(100, () => now)
    const load = vi.fn(async () => [])
    await cache.read('looks', load)
    await cache.read('looks', load)
    expect(load).toHaveBeenCalledTimes(1)
    now = 100
    await cache.read('looks', load)
    await cache.read('looks', load, true)
    expect(load).toHaveBeenCalledTimes(3)
  })

  it('invalidates all category caches and prevents an older read overwriting mutations', async () => {
    const cache = createReadCache()
    const pending = deferred()
    const old = cache.read('garments:top', () => pending.promise)
    const all = await cache.read('garments:all', async () => ['deleted'])
    cache.invalidate('garments')
    const fresh = await cache.read('garments:top', async () => [])
    pending.resolve(['deleted'])
    expect((await old).isCurrent()).toBe(false)
    expect(all.isCurrent()).toBe(false)
    expect(fresh.isCurrent()).toBe(true)
  })

  it('a failed request is retryable and cannot evict a newer request', async () => {
    const cache = createReadCache()
    const pending = deferred()
    const old = cache.read('avatar', () => pending.promise)
    const handled = old.catch(() => null)
    cache.invalidate('avatar')
    const fresh = await cache.read('avatar', async () => null)
    pending.reject(new Error('old request failed'))
    await handled
    expect(fresh.isCurrent()).toBe(true)
    cache.invalidate('avatar')
    await expect(cache.read('avatar', async () => { throw new Error('offline') })).rejects.toThrow('offline')
    expect((await cache.read('avatar', async () => 'retry')).value).toBe('retry')
  })

  it('instances cannot reuse another account data', async () => {
    const alice = createReadCache()
    const bob = createReadCache()
    await alice.read('avatar', async () => 'alice-private')
    expect((await bob.read('avatar', async () => null)).value).toBe(null)
  })
})
