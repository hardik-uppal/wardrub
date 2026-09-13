import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useWardrobe } from '../context/WardrobeContext'
import { useCloset } from '../context/ClosetContext'
import { PageHeader } from '../components/AppChrome'
import BottomNav from '../components/BottomNav'
import OutfitPanel from '../components/OutfitPanel'
import { localDay } from '../utils/localDay'
import ResilientImage from '../components/ResilientImage'
import { editionLabel } from '../utils/magazineEdition'
import { useAuth } from '../context/AuthContext'
import { refreshDailyLocation } from '../utils/dailyLocation'
export default function Today() {
  const location = useLocation()
  const returnOutfit = useRef(location.state?.outfit)
  const { garments, fetchGarments, updateLocation } = useWardrobe()
  const { user } = useAuth()
  const locationSave = useRef({ uid: user?.uid, save: updateLocation })
  useEffect(() => { locationSave.current = { uid: user?.uid, save: updateLocation } }, [updateLocation, user?.uid])
  const {
    request,
    library,
    error: libraryError,
    reload,
    action,
    busy: actionBusy,
  } = useCloset()
  const [feed, setFeed] = useState(null),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false)
  const [swapId, setSwapId] = useState(null),
    [message, setMessage] = useState(''),
    [day, setDay] = useState(localDay())
  const pending = useRef(false),
    feedDate = useRef(null),
    lastAutomaticDay = useRef(null),
    lastLocalDay = useRef(localDay())
  const refresh = useCallback(async () => {
    if (pending.current) return
    pending.current = true
    setBusy(true)
    setError('')
    setSwapId(null)
    try {
      await refreshDailyLocation(user?.uid, (...args) => {
        if (locationSave.current.uid === user?.uid) return locationSave.current.save(...args)
      })
      await fetchGarments(null, true)
      const data = await request(`/magazine-feed?local_day=${localDay()}`)
      if (data.status !== 'success' || !data.feed)
        throw new Error('Could not read today’s suggestion.')
      setFeed(
        returnOutfit.current
          ? { ...data.feed, cover_look: returnOutfit.current }
          : data.feed,
      )
      returnOutfit.current = null
      feedDate.current = data.feed.date
    } catch (e) {
      setFeed(null)
      setError(e.message)
    } finally {
      pending.current = false
      setBusy(false)
    }
  }, [request, fetchGarments, user?.uid])
  useEffect(() => {
    refresh()
    const focus = () => {
      if (document.visibilityState !== 'hidden') {
        refresh()
        reload().catch(() => {})
        setDay(localDay())
      }
    }
    const timer = setInterval(() => {
      const currentLocalDay = localDay()
      setDay(currentLocalDay)
      const localDayChanged = lastLocalDay.current !== currentLocalDay
      lastLocalDay.current = currentLocalDay
      const utcDay = new Date().toISOString().slice(0, 10)
      if (
        localDayChanged ||
        (feedDate.current &&
          feedDate.current !== utcDay &&
          lastAutomaticDay.current !== utcDay)
      ) {
        lastAutomaticDay.current = utcDay
        refresh()
      }
    }, 60000)
    window.addEventListener('focus', focus)
    document.addEventListener('visibilitychange', focus)
    return () => {
      clearInterval(timer)
      window.removeEventListener('focus', focus)
      document.removeEventListener('visibilitychange', focus)
    }
  }, [refresh, reload])
  const plan = library?.days?.[day]
  const outfit = plan || feed?.cover_look
  const change = async (withId) => {
    if (busy) return
    setBusy(true)
    setMessage('')
    setError('')
    try {
      const data = await request('/outfits/swap', {
        method: 'POST',
        body: JSON.stringify({
          garment_ids: outfit.garment_ids,
          replace_item_id: swapId,
          with_item_id: withId,
        }),
      })
      if (data.status === 'no_alternative')
        setMessage('No available alternative. Your outfit is unchanged.')
      else {
        setFeed((previous) => ({ ...previous, cover_look: data.look }))
        setMessage('Piece changed. The other pieces stayed the same.')
      }
      setSwapId(null)
    } catch (e) {
      setMessage(e.message)
    } finally {
      setBusy(false)
    }
  }
  const correct = async (reason) => {
    try {
      await action({
        action: 'feedback',
        reason,
        day: localDay(),
        garment_ids: outfit.garment_ids,
        policy_version:
          outfit.policy_version || feed?.policy_version || 'unknown',
      })
      await refresh()
      setMessage(
        'This combination is set aside for today. Your lasting preferences are unchanged.',
      )
    } catch (e) {
      setMessage(e.message)
    }
  }
  const target = garments.find((g) => g.id === swapId)
  const alternatives = garments.filter(
    (g) =>
      g.category === target?.category && !outfit?.garment_ids.includes(g.id),
  )
  return (
    <div className="quiet-page">
      <PageHeader title="Today" subtitle="Get dressed. Get on with your day." />
      <div className="context-row">
        <span>{feed ? editionLabel(feed.date) : 'Your daily wardrobe'}</span>

      </div>
      {feed?.weather_status === 'available' && (
        <p className="muted weather-line">
          {`${feed.weather.feels_like ?? feed.weather.temperature}°C · ${feed.weather.description}`}
        </p>
      )}
      {error && (
        <div role="alert" className="notice">
          {error} <button onClick={refresh}>Retry suggestion</button>
        </div>
      )}
      {libraryError && (
        <div role="alert" className="notice">
          {libraryError}{' '}
          <button onClick={() => reload().catch(() => {})}>
            Retry saved outfits
          </button>
        </div>
      )}
      {busy && !outfit && (
        <p role="status">Finding a combination from your clothes…</p>
      )}
      {outfit && (
        <>
          <OutfitPanel
            key={outfit.id}
            outfit={outfit}
            onSwap={!plan ? setSwapId : undefined}
          />
          {plan && (
            <p className="muted">
              Undo your plan to choose or swap a different outfit.
            </p>
          )}
        </>
      )}
      {!outfit && !busy && !error && (
        <section className="empty-state">
          <h2>
            {feed?.skipped_for_day
              ? 'No more combinations for today'
              : 'Start with an outfit you own'}
          </h2>
          <p>
            {feed?.skipped_for_day
              ? 'Review your corrections to bring a combination back, check laundry, or add more clothes.'
              : 'Add a top and bottom, or a dress. Avatar and style analysis are optional.'}
          </p>
          <Link className="btn-primary" to="/capture?from=today">
            Add clothes
          </Link>

        </section>
      )}
      {message && (
        <p role="status" className="notice">
          {message}
        </p>
      )}
      {swapId && (
        <section className="choice-panel" aria-label="Choose a replacement">
          <div className="context-row">
            <h2>Change your {target?.category}</h2>
            <button onClick={() => setSwapId(null)}>Cancel</button>
          </div>
          <p className="muted">
            We check availability before making the change.
          </p>
          <div className="choice-grid">
            {alternatives.map((g) => (
              <button disabled={busy} key={g.id} onClick={() => change(g.id)}>
                <ResilientImage
                  src={g.thumbnail_url || g.front_url || g.url}
                  alt={g.description?.short || g.category}
                  className="choice-image"
                />
                <span>{g.description?.short || g.category}</span>
              </button>
            ))}
          </div>
          {!alternatives.length && (
            <p>
              No alternative for this piece yet. Keep this outfit or add more
              clothes.
            </p>
          )}
        </section>
      )}
      {!plan && !!feed?.daily_fits?.length && (
        <section className="alternatives">
          <h2>A few other options</h2>
          <div className="alternative-grid">
            {feed.daily_fits.map((look) => (
              <button
                key={look.id}
                onClick={() =>
                  setFeed((previous) => ({
                    ...previous,
                    cover_look: look,
                    daily_fits: [
                      previous.cover_look,
                      ...previous.daily_fits.filter((x) => x.id !== look.id),
                    ].filter(Boolean),
                  }))
                }
              >
                <div className="mini-collage">
                  {look.garment_ids.map((id) => {
                    const g = garments.find((item) => item.id === id)
                    return (
                      g && (
                        <ResilientImage
                          key={id}
                          src={g.thumbnail_url || g.front_url || g.url}
                          alt={g.category}
                        />
                      )
                    )
                  })}
                </div>
                <span>{look.title}</span>
              </button>
            ))}
          </div>
        </section>
      )}
      {outfit && !plan && (
        <details className="daily-correction">
          <summary>Not right for today?</summary>
          <p className="muted">
            Set aside this combination for today. Readiness and lasting taste
            are separate.
          </p>
          <div className="actions">
            {[
              ['occasion', 'Different plans today'],
              ['comfort', 'Not comfortable today'],
              ['style', 'Not my style today'],
            ].map(([reason, label]) => (
              <button
                className="btn-secondary"
                disabled={busy || actionBusy}
                key={reason}
                onClick={() => correct(reason)}
              >
                {label}
              </button>
            ))}
          </div>
          <Link to="/wardrobe">A piece is unavailable</Link> ·{' '}
          <Link to="/profile?section=preferences">
            Edit lasting preferences
          </Link>
        </details>
      )}
      {feed?.skipped_for_day && (
        <p className="muted">
          Some combinations are set aside today.{' '}
          <Link to="/profile?section=history">Review or undo corrections</Link>.
        </p>
      )}
      <BottomNav />
    </div>
  )
}
