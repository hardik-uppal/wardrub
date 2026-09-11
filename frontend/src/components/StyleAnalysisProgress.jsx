import { getStyleProgress } from '../utils/styleAnalysis'

export default function StyleAnalysisProgress({ profile }) {
  const { stages } = getStyleProgress(profile)
  return (
    <section aria-label="Style analysis progress" className="mt-4 space-y-3 text-left" aria-live="polite">
      {stages.map(stage => (
        <div key={stage.name} className="rounded-xl p-3" style={{ background: 'var(--glass-bg)', border: '1px solid var(--glass-border)' }}>
          <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
            {stage.name === 'color' ? 'Your colors' : 'Your fit'} · {stage.done ? 'Ready' : stage.status === 'failed' ? 'Retry available' : 'Photo needed'}
          </p>
          {stage.hasResult && !stage.done && (
            <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>Your previous recommendations are still available below.</p>
          )}
          {!stage.done && (
            <>
              {stage.reason && <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{stage.reason}</p>}
              <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{stage.message}</p>
              {stage.attempts >= 3 && stage.status === 'needs_input' && (
                <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>Photos may not resolve this reliably. You can continue using your wardrobe and return whenever you like.</p>
              )}
            </>
          )}
        </div>
      ))}
    </section>
  )
}
