import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { PageHeader, WardrobeTabs } from '../components/AppChrome'
import { useCloset } from '../context/ClosetContext'
import { useWardrobe } from '../context/WardrobeContext'
import OutfitPanel from '../components/OutfitPanel'
import BottomNav from '../components/BottomNav'
import Dialog from '../components/Dialog'
import SavedLooks from './SavedLooks'
export default function Outfits() {
  const { library, action, error, busy, setDraft, reload } = useCloset()
  const { fetchGarments, fetchLooks } = useWardrobe()
  const [view, setView] = useState('all'),
    [remove, setRemove] = useState(null),
    [failure, setFailure] = useState('')
  useEffect(() => {
    fetchGarments()
    fetchLooks(true)
    reload().catch(() => {})
  }, [fetchGarments, fetchLooks, reload])
  return (
    <div className="quiet-page">
      <PageHeader
        title="Wardrobe"
        subtitle="Good combinations, ready to revisit."
      />
      <WardrobeTabs active="outfits" />
      <div className="context-row">
        <div className="filter-row">
          {['all', 'saved', 'tryons'].map((v) => (
            <button
              key={v}
              aria-pressed={view === v}
              onClick={() => setView(v)}
            >
              {{ all: 'All', saved: 'Saved outfits', tryons: 'Try-ons' }[v]}
            </button>
          ))}
        </div>
        <Link
          className="btn-secondary"
          to="/dressing-room"
          onClick={() => setDraft(null)}
        >
          Create a try-on
        </Link>
      </div>
      {(error || failure) && <p role="alert">{error || failure}</p>}
      {view !== 'tryons' && (
        <section>
          <h2 className="section-title">Saved outfits</h2>
          {!library && <p role="status">Loading your saved combinations…</p>}
          {library && !Object.keys(library.outfits).length && (
            <div className="empty-state">
              <p>
                Save a combination from Today. You don’t need to generate an
                image.
              </p>
              <Link to="/">Find an outfit</Link>
            </div>
          )}
          {Object.values(library?.outfits || {}).map((outfit) => (
            <div key={outfit.id} className="saved-combination">
              <OutfitPanel outfit={outfit} compact />
              <button className="text-action" onClick={() => setRemove(outfit)}>
                Remove saved outfit…
              </button>
            </div>
          ))}
        </section>
      )}
      {view !== 'saved' && (
        <section className="embedded-history">
          <h2 className="section-title">Try-ons</h2>
          <SavedLooks embedded />
        </section>
      )}
      {remove && (
        <Dialog title="Remove saved outfit?" onClose={() => setRemove(null)}>
          <p>Your clothes and generated images will stay in Wardrub.</p>
          <div className="actions">
            <button onClick={() => setRemove(null)}>Cancel</button>
            <button
              disabled={busy}
              onClick={async () => {
                try {
                  await action({ action: 'delete', outfit_id: remove.id })
                  setRemove(null)
                } catch (e) {
                  setFailure(e.message)
                  setRemove(null)
                }
              }}
            >
              Remove outfit
            </button>
          </div>
        </Dialog>
      )}
      <BottomNav />
    </div>
  )
}
