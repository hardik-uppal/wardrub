import { localDay } from '../utils/localDay'
import { useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useCloset } from '../context/ClosetContext'
import { useWardrobe } from '../context/WardrobeContext'
import ResilientImage from './ResilientImage'
export default function OutfitPanel({ outfit, onSwap, compact = false }) {
  const { garments } = useWardrobe()
  const { library, action, busy, setDraft, readiness } = useCloset()
  const navigate = useNavigate()
  const location = useLocation()
  const [message, setMessage] = useState('')
  const [failure, setFailure] = useState('')
  const selected = outfit.garment_ids.map((id) =>
    garments.find((g) => g.id === id),
  )
  const missing = selected.some((g) => !g)
  const day = localDay()
  const plan = library?.days?.[day]
  const isPlanned = plan?.id === outfit.id
  const saved = !!library?.outfits?.[outfit.id]
  const run = async (kind) => {
    setFailure('')
    setMessage('')
    try {
      await action({
        action: kind,
        garment_ids: outfit.garment_ids,
        title: outfit.title,
        day,
        outfit_id: outfit.id,
      })
      setMessage(
        {
          save: 'Outfit saved in Wardrobe.',
          plan: 'Planned for today.',
          wore: 'Wear confirmed. Clothes stay in their current readiness state.',
          unwear: 'Wear confirmation undone.',
          unplan: 'Plan removed.',
        }[kind],
      )
    } catch (e) {
      setFailure(e.message)
    }
  }
  return (
    <article className={`outfit-panel ${compact ? 'compact-outfit' : ''}`}>
      <div className="outfit-collage">
        {selected.map((g, i) => (
          <div key={outfit.garment_ids[i]}>
            {g ? (
              <ResilientImage
                src={g.thumbnail_url || g.front_url || g.url}
                alt={
                  typeof g.description === 'string'
                    ? g.description
                    : g.description?.short || g.category
                }
                className="outfit-image"
              />
            ) : (
              <p className="missing-piece">Item no longer available</p>
            )}
          </div>
        ))}
      </div>
      <div className="outfit-copy">
        {isPlanned && (
          <p className="eyebrow">
            {plan.worn ? 'Worn today' : 'Your plan for today'}
          </p>
        )}
        <h2>{outfit.title || 'Your outfit'}</h2>
        <div className="actions">
          <button
            className="btn-primary"
            disabled={busy || !library || missing}
            onClick={() =>
              run(isPlanned ? (plan.worn ? 'unwear' : 'wore') : 'plan')
            }
          >
            {isPlanned
              ? plan.worn
                ? 'Undo wear'
                : 'I wore this'
              : 'Plan for today'}
          </button>
          <button
            className="btn-secondary"
            disabled={busy || !library || missing || saved}
            onClick={() => run('save')}
          >
            {saved ? 'Saved outfit' : 'Save outfit'}
          </button>
        </div>
        {outfit.why_it_works && (
          <details>
            <summary>Why this works</summary>
            <p className="muted">{outfit.why_it_works}</p>
          </details>
        )}
        {missing && (
          <p role="status">
            Some pieces are missing.{' '}
            <Link to="/">Find another outfit from your current clothes</Link>.
          </p>
        )}
        <ul className="outfit-items">
          {selected.map((g, i) => (
            <li key={outfit.garment_ids[i]}>
              <span>
                {typeof g?.description === 'string'
                  ? g.description
                  : g?.description?.short ||
                    g?.name ||
                    g?.category ||
                    'Missing piece'}
                <small>
                  {
                    {
                      ready: 'Ready',
                      laundry: 'In laundry',
                      unknown: 'Readiness unknown',
                    }[readiness[outfit.garment_ids[i]] || 'unknown']
                  }{' '}
                  ·{' '}
                  {library?.locations?.[outfit.garment_ids[i]] ||
                    'Location not set'}
                </small>
              </span>
              {onSwap && g && (
                <button className="text-action" onClick={() => onSwap(g.id)}>
                  Swap {g.category}
                </button>
              )}
            </li>
          ))}
        </ul>

        <div className="actions">
          <button
            className="text-action"
            disabled={missing}
            onClick={() => {
              setDraft({ ...outfit, origin: location.pathname })
              navigate('/dressing-room')
            }}
          >
            Try on me
          </button>
          {isPlanned && !plan.worn && (
            <button
              className="text-action"
              disabled={busy}
              onClick={() => run('unplan')}
            >
              Undo plan
            </button>
          )}
        </div>
        {message && <p role="status">{message}</p>}
        {failure && (
          <p role="alert" className="error-text">
            {failure}
          </p>
        )}
      </div>
    </article>
  )
}
