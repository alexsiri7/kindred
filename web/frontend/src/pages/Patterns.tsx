import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { api, type Pattern } from '../api/client'

export function Patterns() {
  const [patterns, setPatterns] = useState<Pattern[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<Pattern[]>('/patterns')
      .then(setPatterns)
      .catch((e: Error) => setError(e.message))
  }, [])

  if (error) return <p style={{ color: 'var(--rust)' }}>{error}</p>
  if (!patterns) return <p style={{ color: 'var(--ink-3)' }}>Loading…</p>

  const sorted = [...patterns].sort(
    (a, b) => new Date(b.last_seen_at).getTime() - new Date(a.last_seen_at).getTime(),
  )

  return (
    <>
      <div className="page-head">
        <div className="page-eye">
          <span className="glyph">◈</span> Patterns
        </div>
        <h1 className="page-title">
          What <em>keeps</em> coming back
        </h1>
        <p className="page-sub">
          Sorted by when you last saw them. Each one is named in your words.
        </p>
      </div>

      <div className="readonly-banner">
        <span className="lock">🔒</span>
        <span>
          <strong>Read-only.</strong> Patterns are named during your journaling sessions with your AI assistant.
        </span>
      </div>

      {patterns.length === 0 && (
        <p style={{ color: 'var(--ink-3)' }}>
          No named patterns yet. They&apos;ll appear once /kindred-hcb logs an occurrence.
        </p>
      )}

      <div className="pat-list">
        {sorted.map((p) => {
          const lastSeen = new Date(p.last_seen_at).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
          })
          return (
            <Link
              key={p.id}
              to={`/app/patterns/${p.id}`}
              style={{ textDecoration: 'none', color: 'inherit' }}
            >
              <div className="pat-card">
                <div>
                  <h3 className="pat-card-name">{p.name}</h3>
                  {p.description && <p className="pat-card-desc">{p.description}</p>}
                </div>
                <div className="pat-card-stats">
                  <span className="big">×{p.occurrence_count}</span>
                  last seen {lastSeen}
                </div>
              </div>
            </Link>
          )
        })}
      </div>
    </>
  )
}
