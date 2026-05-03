import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { api, type Pattern } from '../api/client'

export function PatternDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [pattern, setPattern] = useState<Pattern | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    api
      .get<Pattern>(`/patterns/${id}`)
      .then(setPattern)
      .catch((e: Error) => setError(e.message))
  }, [id])

  if (error) return <p style={{ color: 'var(--rust)' }}>{error}</p>
  if (!pattern) return <p style={{ color: 'var(--ink-3)' }}>Loading…</p>

  const lastSeen = new Date(pattern.last_seen_at).toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  })

  return (
    <>
      <button className="back-link" type="button" onClick={() => void navigate(-1)}>
        ← All patterns
      </button>

      <div className="pat-detail-head">
        <div className="page-eye">
          <span className="glyph">◈</span> Pattern
        </div>
        <h1 className="pat-detail-name">{pattern.name}</h1>
        {pattern.description && (
          <p className="pat-detail-desc">{pattern.description}</p>
        )}
        <div className="pat-detail-stats">
          <div>
            Occurrences
            <strong>×{pattern.occurrence_count}</strong>
          </div>
          <div>
            Last seen
            <strong>{lastSeen}</strong>
          </div>
        </div>
      </div>

      <div className="entry-section-eye">The typical shape</div>
      <div className="typical">
        <div className="typical-q">
          <span className="q-eye">Quadrant 01</span>
          <div className="q-name">Thoughts</div>
          <p className="q-text">{pattern.typical_thoughts ?? '—'}</p>
        </div>
        <div className="typical-q">
          <span className="q-eye">Quadrant 02</span>
          <div className="q-name">Emotions</div>
          <p className="q-text">{pattern.typical_emotions ?? '—'}</p>
        </div>
        <div className="typical-q">
          <span className="q-eye">Quadrant 03</span>
          <div className="q-name">Behaviours</div>
          <p className="q-text">{pattern.typical_behaviors ?? '—'}</p>
        </div>
        <div className="typical-q">
          <span className="q-eye">Quadrant 04</span>
          <div className="q-name">Body</div>
          <p className="q-text">{pattern.typical_sensations ?? '—'}</p>
        </div>
      </div>

      {pattern.occurrences && pattern.occurrences.length > 0 && (
        <>
          <div className="entry-section-eye">When it has shown up</div>
          <div className="timeline">
            {pattern.occurrences.map((o, i) => {
              const occDate = new Date(o.date + 'T12:00').toLocaleDateString('en-US', {
                month: 'long',
                day: 'numeric',
              })
              return (
                <div key={o.id} className={`tl-item ${i === 0 ? 'is-recent' : ''}`}>
                  <div className="tl-date">
                    {occDate}
                    {o.intensity != null && ` · intensity ${o.intensity}/5`}
                    {' · '}
                    <Link to={`/entries/${o.entry_id}`} style={{ color: 'var(--terracotta)' }}>
                      read entry →
                    </Link>
                  </div>
                  {o.trigger && <p className="tl-trigger">Trigger: {o.trigger}</p>}
                  <div className="tl-quads">
                    {o.thoughts && (
                      <div>
                        <em>Thoughts</em>
                        {o.thoughts}
                      </div>
                    )}
                    {o.sensations && (
                      <div style={{ marginTop: 6 }}>
                        <em>Body</em>
                        {o.sensations}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}
    </>
  )
}
