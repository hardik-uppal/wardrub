import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { useWardrobe } from '../context/WardrobeContext'
import { useCloset } from '../context/ClosetContext'
import { PageHeader, WardrobeTabs } from '../components/AppChrome'
import BottomNav from '../components/BottomNav'
import ResilientImage from '../components/ResilientImage'
import Dialog from '../components/Dialog'
const name = (g) =>
  g.name ||
  (typeof g.description === 'string'
    ? g.description
    : g.description?.short || `${g.category} item`)
export default function Home() {
  const { garments, fetchGarments, deleteGarment } = useWardrobe()
  const {
    request,
    setDraft,
    library,
    action,
    busy: libraryBusy,
    error: libraryError,
  } = useCloset()
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const [query, setQuery] = useState(''),
    [category, setCategory] = useState(params.get('category') || 'all'),
    [readiness, setReadiness] = useState('all'),
    [sort, setSort] = useState('recent')
  const [states, setStates] = useState({}),
    [selected, setSelected] = useState([]),
    [detail, setDetail] = useState(null),
    [back, setBack] = useState(false)
  const [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState(''),
    [undo, setUndo] = useState(null),
    [pendingDelete, setPendingDelete] = useState(false),
    [location, setLocation] = useState('')
  const load = useCallback(async () => {
    try {
      const data = await request('/closet-state')
      if (!Array.isArray(data.garments))
        throw new Error('Could not read clothing readiness.')
      setStates(Object.fromEntries(data.garments.map((g) => [g.id, g])))
      setError('')
    } catch (e) {
      setError(e.message)
    }
  }, [request])
  useEffect(() => {
    fetchGarments()
    load()
  }, [fetchGarments, load])
  const visible = useMemo(() => {
    const items = garments.filter(
      (g) =>
        (category === 'all' || g.category === category) &&
        (readiness === 'all' ||
          (states[g.id]?.readiness || 'unknown') === readiness) &&
        `${name(g)} ${g.category}`.toLowerCase().includes(query.toLowerCase()),
    )
    return sort === 'recent'
      ? items
      : items.sort((a, b) =>
          (sort === 'name' ? name(a) : a.category).localeCompare(
            sort === 'name' ? name(b) : b.category,
          ),
        )
  }, [garments, states, query, category, readiness, sort])
  const changeReadiness = async (ids, value, undoChanges = null) => {
    if (busy) return
    setBusy(true)
    setMessage('')
    setError('')
    const changes =
      undoChanges ||
      ids.map((id) => ({
        id,
        readiness: value,
        expected_version: states[id]?.version,
      }))
    const before = changes.map((c) => ({
      id: c.id,
      readiness: states[c.id]?.readiness || 'unknown',
      expected_version: c.expected_version + 1,
    }))
    try {
      if (changes.some((c) => c.expected_version === undefined))
        throw new Error(
          'Readiness is unknown. Refresh the wardrobe before changing it.',
        )
      await request('/closet-state/batch', {
        method: 'POST',
        body: JSON.stringify({ changes }),
      })
      setUndo(undoChanges ? null : before)
      setSelected([])
      setMessage(
        undoChanges
          ? 'Readiness change undone.'
          : 'Clothing readiness updated.',
      )
      await load()
    } catch (e) {
      setUndo(null)
      await load()
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }
  const saveLocation = async (ids) => {
    try {
      await action({ action: 'location', garment_ids: ids, location })
      setMessage('Storage location updated.')
    } catch (e) {
      setError(e.message)
    }
  }
  const remove = async () => {
    setBusy(true)
    setError('')
    try {
      await deleteGarment(detail.id)
      setDetail(null)
      setSelected((s) => s.filter((id) => id !== detail.id))
      setMessage(
        'Item removed. Existing generated images remain in your history.',
      )
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="quiet-page">
      <PageHeader
        title="Wardrobe"
        subtitle={`${garments.length} pieces. More possibilities.`}
      >
        <Link className="btn-primary" to="/capture?from=wardrobe">
          Add clothes
        </Link>
      </PageHeader>
      <WardrobeTabs active="items" />
      {(error || libraryError) && (
        <p role="alert" className="notice">
          {error || libraryError}{' '}
          <button
            onClick={() => {
              load()
              fetchGarments(null, true)
            }}
          >
            Refresh wardrobe
          </button>
        </p>
      )}
      {message && <p role="status">{message}</p>}
      <div className="wardrobe-controls">
        <label className="search-field">
          <span className="sr-only">Search wardrobe</span>
          <input
            type="search"
            placeholder="Find a piece…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
      </div>
      <details
        className="wardrobe-filters"
        open={params.has('category') || undefined}
      >
        <summary>
          Filters
          {category !== 'all' || readiness !== 'all' || sort !== 'recent'
            ? ' · Active'
            : ''}
        </summary>
        <label>
          <span className="sr-only">Sort wardrobe</span>
          <select value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="recent">Recent</option>
            <option value="name">Name</option>
            <option value="category">Category</option>
          </select>
        </label>

        <div
          className="filter-row category-filters"
          aria-label="Clothing categories"
        >
          {['all', 'top', 'bottom', 'dress', 'outerwear', 'shoes'].map((c) => (
            <button
              key={c}
              aria-pressed={category === c}
              onClick={() => setCategory(c)}
            >
              {
                {
                  all: 'All',
                  top: 'Tops',
                  bottom: 'Bottoms',
                  dress: 'Dresses',
                  outerwear: 'Outerwear',
                  shoes: 'Shoes',
                }[c]
              }
            </button>
          ))}
        </div>
        <div className="context-row">
          <label>
            Readiness{' '}
            <select
              value={readiness}
              onChange={(e) => setReadiness(e.target.value)}
            >
              <option value="all">All pieces</option>
              <option value="ready">Ready to wear</option>
              <option value="laundry">In laundry</option>
              <option value="unknown">Unknown</option>
            </select>
          </label>
          <span className="muted">{visible.length} shown</span>
        </div>
      </details>
      {undo && (
        <button
          className="text-action"
          disabled={busy}
          onClick={() => changeReadiness([], null, undo)}
        >
          Undo last readiness change
        </button>
      )}
      {!!selected.length && (
        <section className="selection-bar" aria-label="Manage selected clothes">
          <strong>{selected.length} selected</strong>
          <div className="actions">
            <button
              disabled={busy}
              onClick={() => changeReadiness(selected, 'laundry')}
            >
              Send to laundry
            </button>
            <button
              disabled={busy}
              onClick={() => changeReadiness(selected, 'ready')}
            >
              Mark ready
            </button>
            <button onClick={() => setSelected([])}>Clear selection</button>
          </div>
          <label>
            Storage location (optional)
            <input
              value={location}
              maxLength={80}
              placeholder="e.g. Bedroom · top drawer"
              onChange={(e) => setLocation(e.target.value)}
            />
          </label>
          <button
            disabled={libraryBusy || !library}
            onClick={() => saveLocation(selected)}
          >
            Save location for selected pieces
          </button>
        </section>
      )}
      <div className="wardrobe-grid">
        {visible.map((g) => (
          <article key={g.id} className="garment-tile">
            <button
              aria-label={`View ${name(g)}`}
              onClick={() => {
                setDetail(g)
                setBack(false)
                setPendingDelete(false)
                setLocation(library?.locations?.[g.id] || '')
              }}
            >
              <ResilientImage
                src={g.thumbnail_url || g.front_url || g.url}
                alt={name(g)}
                className="garment-image"
              />
              <span className="garment-name">{name(g)}</span>
            </button>
            <div className="context-row">
              <small>
                {
                  {
                    ready: 'Ready',
                    laundry: 'In laundry',
                    unknown: 'Readiness unknown',
                  }[states[g.id]?.readiness || 'unknown']
                }
              </small>
              <label>
                <span className="sr-only">Select {name(g)}</span>
                <input
                  type="checkbox"
                  checked={selected.includes(g.id)}
                  disabled={!selected.includes(g.id) && selected.length >= 50}
                  onChange={(e) =>
                    setSelected((previous) =>
                      e.target.checked
                        ? [...previous, g.id]
                        : previous.filter((id) => id !== g.id),
                    )
                  }
                />
              </label>
            </div>
            {library?.locations?.[g.id] && (
              <small className="muted">{library.locations[g.id]}</small>
            )}
          </article>
        ))}
      </div>
      {!visible.length && (
        <section className="empty-state">
          <h2>
            {garments.length
              ? 'No matching pieces'
              : 'Your wardrobe starts here'}
          </h2>
          <p>
            {garments.length
              ? 'Try another search or filter.'
              : 'Add a top and bottom, or a dress, to see your first outfit.'}
          </p>
          {garments.length ? (
            <button
              onClick={() => {
                setQuery('')
                setCategory('all')
                setReadiness('all')
              }}
            >
              Clear filters
            </button>
          ) : (
            <Link className="btn-primary" to="/capture?from=wardrobe">
              Add your first clothes
            </Link>
          )}
        </section>
      )}
      {detail && (
        <Dialog title={name(detail)} onClose={() => setDetail(null)}>
          <ResilientImage
            src={back ? detail.back_url : detail.front_url || detail.url}
            alt={`${name(detail)} ${back ? 'back' : 'front'}`}
            className="detail-image"
          />
          {detail.fit_observation?.fit &&
            detail.fit_observation.fit !== 'unknown' && (
              <details>
                <summary>
                  Fit in this photo · {detail.fit_observation.fit}
                </summary>
                <p className="muted">
                  Observed on the person pictured; not a size or comfort
                  guarantee.
                </p>
                <p>{detail.fit_observation.drape}</p>
                <ul>
                  {detail.fit_observation.evidence?.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </details>
            )}
          {detail.back_url && (
            <button onClick={() => setBack(!back)}>
              Show {back ? 'front' : 'back'}
            </button>
          )}
          <label>
            Clothing readiness
            <select
              disabled={busy || !states[detail.id]}
              value={states[detail.id]?.readiness || 'unknown'}
              onChange={(e) => changeReadiness([detail.id], e.target.value)}
            >
              <option value="unknown">Unknown</option>
              <option value="ready">Ready to wear</option>
              <option value="laundry">In laundry</option>
            </select>
          </label>
          <label>
            Storage location (optional)
            <input
              maxLength={80}
              value={location}
              onChange={(e) => setLocation(e.target.value)}
            />
          </label>
          <button
            disabled={libraryBusy || !library}
            onClick={() => saveLocation([detail.id])}
          >
            Save location
          </button>
          {['top', 'bottom', 'dress', 'outerwear'].includes(
            detail.category,
          ) && (
            <button
              className="btn-secondary"
              onClick={() => {
                setDraft({ garment_ids: [detail.id], origin: '/wardrobe' })
                navigate('/dressing-room')
              }}
            >
              Use in a try-on
            </button>
          )}
          {message && <p role="status">{message}</p>}
          {error && <p role="alert">{error}</p>}
          <details>
            <summary>Remove this piece</summary>
            <p>
              Removing a garment keeps generated images. Saved outfits will show
              a missing piece.
            </p>
            {pendingDelete ? (
              <div className="actions">
                <button onClick={() => setPendingDelete(false)}>Cancel</button>
                <button disabled={busy} onClick={remove}>
                  Confirm delete
                </button>
              </div>
            ) : (
              <button onClick={() => setPendingDelete(true)}>
                Delete item…
              </button>
            )}
          </details>
        </Dialog>
      )}
      <BottomNav />
    </div>
  )
}
