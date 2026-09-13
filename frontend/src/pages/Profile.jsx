import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { PageHeader } from '../components/AppChrome'
import BottomNav from '../components/BottomNav'
import { useCloset } from '../context/ClosetContext'
import { useWardrobe } from '../context/WardrobeContext'
import { useAuth } from '../context/AuthContext'
import ResilientImage from '../components/ResilientImage'
import StyleProfile from './StyleProfile'
const styles = [
  'casual',
  'minimalist',
  'classic',
  'sporty',
  'formal',
  'streetwear',
  'bohemian',
]
const cities = [
  { city: 'New Delhi', lat: 28.6139, lon: 77.209 },
  { city: 'Mumbai', lat: 19.076, lon: 72.8777 },
  { city: 'Bengaluru', lat: 12.9716, lon: 77.5946 },
  { city: 'London', lat: 51.5074, lon: -0.1278 },
  { city: 'New York', lat: 40.7128, lon: -74.006 },
]
function Preferences() {
  const { library, action, busy } = useCloset()
  const [selected, setSelected] = useState(library?.styles || []),
    [message, setMessage] = useState('')
  return (
    <section className="profile-section">
      <h2>Your style preferences</h2>
      <p className="muted">
        Choose styles you enjoy. These give matching clothes a small boost; you
        can change them anytime.
      </p>
      <div className="filter-row">
        {styles.map((s) => (
          <button
            key={s}
            aria-pressed={selected.includes(s)}
            onClick={() =>
              setSelected((p) =>
                p.includes(s) ? p.filter((v) => v !== s) : [...p, s],
              )
            }
          >
            {s}
          </button>
        ))}
      </div>
      <button
        className="btn-primary"
        disabled={busy || !library}
        onClick={async () => {
          try {
            await action({ action: 'styles', styles: selected })
            setMessage('Preferences saved. Today will use these on refresh.')
          } catch (e) {
            setMessage(e.message)
          }
        }}
      >
        Save preferences
      </button>
      <p role="status">{message}</p>
    </section>
  )
}
function Location() {
  const { userProfile, updateLocation } = useWardrobe()
  const [message, setMessage] = useState(''),
    [busy, setBusy] = useState(false)
  const save = async (place) => {
    setBusy(true)
    try {
      await updateLocation(place.lat, place.lon, place.city)
      setMessage('Location saved. Today will refresh your suggestions.')
    } catch (e) {
      setMessage(e.message)
    } finally {
      setBusy(false)
    }
  }
  const locate = () => {
    if (!navigator.geolocation) {
      setMessage('Location is unavailable. Choose a city instead.')
      return
    }
    setBusy(true)
    navigator.geolocation.getCurrentPosition(
      (p) =>
        save({
          lat: p.coords.latitude,
          lon: p.coords.longitude,
          city: 'Current location',
        }),
      () => {
        setBusy(false)
        setMessage(
          'Location permission was unavailable. Choose a city instead.',
        )
      },
    )
  }
  return (
    <section className="profile-section">
      <h2>Your location</h2>
      <p className="muted">
        {userProfile?.location?.city || 'No location saved'}. Used for weather
        when you open Today.
      </p>
      <div className="filter-row">
        {cities.map((c) => (
          <button key={c.city} disabled={busy} onClick={() => save(c)}>
            {c.city}
          </button>
        ))}
      </div>
      <button className="btn-primary" disabled={busy} onClick={locate}>
        Use current location
      </button>
      <p role="status">{message}</p>
    </section>
  )
}
function History() {
  const { library, action, busy } = useCloset()
  const [message, setMessage] = useState('')
  return (
    <section className="profile-section">
      <h2>Plans and wear history</h2>
      <p className="muted">
        Only wear you explicitly confirmed is recorded as worn.
      </p>
      {Object.entries(library?.days || {})
        .sort(([a], [b]) => b.localeCompare(a))
        .map(([day, outfit]) => (
          <div key={day} className="context-row">
            <span>
              {day} · {outfit.title}
              <small className="muted">
                {' '}
                · {outfit.worn ? 'Worn' : 'Planned'}
              </small>
            </span>
            <button
              disabled={busy}
              className="text-action"
              onClick={async () => {
                try {
                  await action({
                    action: outfit.worn ? 'unwear' : 'unplan',
                    day,
                    outfit_id: outfit.id,
                  })
                  setMessage('Entry updated.')
                } catch (e) {
                  setMessage(e.message)
                }
              }}
            >
              {outfit.worn ? 'Undo wear' : 'Remove plan'}
            </button>
          </div>
        ))}
      {!Object.keys(library?.days || {}).length && (
        <p>No plans or confirmed wear yet.</p>
      )}
      <h3>Outfit corrections</h3>
      {Object.values(library?.feedback || {}).map((entry) => (
        <div className="context-row" key={entry.id}>
          <span>
            {entry.day} · {entry.reason}
          </span>
          <button
            className="text-action"
            disabled={busy}
            onClick={async () => {
              try {
                await action({ action: 'undo_feedback', outfit_id: entry.id })
                setMessage('Correction removed.')
              } catch (e) {
                setMessage(e.message)
              }
            }}
          >
            Undo correction
          </button>
        </div>
      ))}
      <p role="status">{message}</p>
    </section>
  )
}
export default function Profile() {
  const [params, setParams] = useSearchParams()
  const { avatarUrl } = useWardrobe(),
    { signOut } = useAuth(),
    { library, error } = useCloset()
  const navigate = useNavigate()
  const section =
    params.get('section') || (params.has('analysis') ? 'style' : '')
  const [signOutError, setSignOutError] = useState('')
  if (section === 'style' || section === 'recovery')
    return <StyleProfile recoveryOnly={section === 'recovery'} />
  return (
    <div className="quiet-page">
      <PageHeader
        title="Profile"
        subtitle="Your preferences, on your terms."
        back="/"
      />
      {error && <p role="alert">{error}</p>}
      <section className="avatar-summary">
        {avatarUrl && (
          <ResilientImage
            src={avatarUrl}
            alt="Your current avatar"
            className="profile-avatar"
          />
        )}
        <div>
          <h2>My avatar</h2>
          <p className="muted">Optional. Preview outfits on yourself.</p>
          <Link className="text-action" to="/create-avatar">
            {avatarUrl ? 'Review or update avatar' : 'Create avatar'}
          </Link>
        </div>
      </section>
      <nav className="profile-links" aria-label="Profile sections">
        {[
          ['location', 'Location', 'Weather for your day'],
          ['preferences', 'Style preferences', 'Guide your suggestions'],
          ['history', 'Plans and wear history', 'Your confirmed daily choices'],
          ['style', 'Optional style guidance', 'Your colors and fit'],
          ['recovery', 'Account recovery', 'Previous-session data'],
        ].map(([key, title, detail]) => (
          <button
            key={key}
            aria-current={section === key ? 'page' : undefined}
            onClick={() => setParams({ section: key })}
          >
            <span>
              {title}
              <small>{detail}</small>
            </span>
            <span aria-hidden="true">→</span>
          </button>
        ))}
      </nav>
      {section === 'preferences' && library && (
        <Preferences key={library.version} />
      )}
      {section === 'location' && <Location />}
      {section === 'history' && <History />}
      <button
        className="text-action sign-out"
        onClick={async () => {
          try {
            await signOut()
            navigate('/login')
          } catch (e) {
            setSignOutError(e.message)
          }
        }}
      >
        Sign out
      </button>
      {signOutError && <p role="alert">{signOutError}</p>}
      <BottomNav />
    </div>
  )
}
