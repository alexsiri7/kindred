import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { api, type Entry } from '../api/client'

export function EntryDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [entry, setEntry] = useState<Entry | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showTranscript, setShowTranscript] = useState(false)

  useEffect(() => {
    if (!id) return
    api
      .get<Entry>(`/entries/${id}`)
      .then(setEntry)
      .catch((e: Error) => setError(e.message))
  }, [id])

  if (error) return <p style={{ color: 'var(--rust)' }}>{error}</p>
  if (!entry) return <p style={{ color: 'var(--ink-3)' }}>Loading…</p>

  const fullDate = new Date(entry.date + 'T12:00').toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  })

  const transcriptCount = entry.transcript?.length ?? 0

  return (
    <>
      <button className="back-link" type="button" onClick={() => void navigate(-1)}>
        ← All entries
      </button>

      <div className="entry-detail-head">
        <div>
          <div className="page-eye">
            <span className="glyph">◈</span> Entry
          </div>
          <div className="entry-detail-date">{fullDate}</div>
        </div>
        <div className="entry-detail-meta">
          {entry.mood && <span className="mood-big">◉ {entry.mood}</span>}
          {entry.transcript ? 'transcript on' : 'summary only'}
        </div>
      </div>

      <p className="entry-summary">{entry.summary}</p>

      {entry.occurrences && entry.occurrences.length > 0 && (
        <>
          <div className="entry-section-eye">Patterns named in this entry</div>
          {entry.occurrences.map((o) => (
            <div key={o.id} className="occ-card">
              <div className="occ-head">
                <span className="occ-name">
                  <span className="glyph">✶</span>
                  Pattern
                </span>
                {o.intensity != null && (
                  <span className="occ-intensity">
                    intensity {o.intensity}/5
                    {o.trigger ? ` · trigger: ${o.trigger}` : ''}
                  </span>
                )}
              </div>
              <div className="occ-quads">
                {o.thoughts && (
                  <div className="occ-quad">
                    <span className="occ-quad-label">Thoughts</span>
                    {o.thoughts}
                  </div>
                )}
                {o.emotions && (
                  <div className="occ-quad">
                    <span className="occ-quad-label">Emotions</span>
                    {o.emotions}
                  </div>
                )}
                {o.behaviors && (
                  <div className="occ-quad">
                    <span className="occ-quad-label">Behaviours</span>
                    {o.behaviors}
                  </div>
                )}
                {o.sensations && (
                  <div className="occ-quad">
                    <span className="occ-quad-label">Body</span>
                    {o.sensations}
                  </div>
                )}
              </div>
            </div>
          ))}
        </>
      )}

      {entry.transcript && entry.transcript.length > 0 && (
        <div className="transcript-wrap">
          <button
            type="button"
            className={`transcript-toggle ${showTranscript ? 'is-open' : ''}`}
            onClick={() => setShowTranscript((v) => !v)}
          >
            <span className="chev">▸</span>
            {showTranscript ? 'Hide' : 'Show'} full transcript ({transcriptCount} messages)
          </button>
          {showTranscript && (
            <div className="transcript-body">
              {entry.transcript.map((m, i) => (
                <div
                  key={i}
                  className={`t-msg ${m.role === 'assistant' ? 'kindred' : 'user'}`}
                >
                  <span className="who">{m.role === 'assistant' ? 'kindred' : 'you'}</span>
                  <span className="text">{m.content}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </>
  )
}
