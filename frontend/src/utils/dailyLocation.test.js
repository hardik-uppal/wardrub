import { beforeEach, afterEach, expect, test, vi } from 'vitest'
import { refreshDailyLocation, setLocationPreference } from './dailyLocation'

beforeEach(() => {
  localStorage.clear()
  vi.stubGlobal('navigator', {
    permissions: { query: vi.fn().mockResolvedValue({ state: 'granted' }) },
    geolocation: { getCurrentPosition: vi.fn((ok) => ok({ coords: { latitude: 1, longitude: 2 } })) },
  })
})
afterEach(() => vi.unstubAllGlobals())
test('requires explicit opt-in and keeps manual cities', async () => {
  const save = vi.fn()
  await refreshDailyLocation('a', save)
  expect(save).not.toHaveBeenCalled()
  setLocationPreference('a', false)
  await refreshDailyLocation('a', save)
  expect(navigator.permissions.query).not.toHaveBeenCalled()
})
test('deduplicates requests and updates at most once daily per account', async () => {
  const save = vi.fn()
  setLocationPreference('a', true)
  await Promise.all([refreshDailyLocation('a', save), refreshDailyLocation('a', save)])
  await refreshDailyLocation('a', save)
  expect(save).toHaveBeenCalledTimes(1)
  expect(save).toHaveBeenCalledWith(1, 2, 'Current location')
  setLocationPreference('b', true)
  await refreshDailyLocation('b', save)
  expect(save).toHaveBeenCalledTimes(2)
})
test('updates on a later day', async () => {
  setLocationPreference('a', true, '2000-01-01')
  const save = vi.fn()
  await refreshDailyLocation('a', save)
  expect(save).toHaveBeenCalledTimes(1)
})
test('never prompts automatically or retries denied permission that day', async () => {
  navigator.permissions.query.mockResolvedValue({ state: 'prompt' })
  setLocationPreference('a', true)
  const save = vi.fn()
  await refreshDailyLocation('a', save)
  await refreshDailyLocation('a', save)
  expect(navigator.permissions.query).toHaveBeenCalledTimes(1)
  expect(navigator.geolocation.getCurrentPosition).not.toHaveBeenCalled()
  expect(save).not.toHaveBeenCalled()
})
test('location failure preserves the saved location', async () => {
  navigator.geolocation.getCurrentPosition.mockImplementation((ok, fail) => fail(new Error('unavailable')))
  setLocationPreference('a', true)
  const save = vi.fn()
  await expect(refreshDailyLocation('a', save)).resolves.toBeUndefined()
  expect(save).not.toHaveBeenCalled()
})
