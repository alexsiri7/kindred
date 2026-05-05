import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { api, type Pattern } from '../api/client'
import { useNavCounts } from '../store/navCounts'

const MS_PER_WEEK = 7 * 24 * 60 * 60 * 1000

function weekBars(
  lastSeenAt: string,
  now: Date,
): { isMonth: boolean; height: number }[] {
  const lastSeen = new Date(lastSeenAt)
  const lastSeenValid = !isNaN(lastSeen.getTime())
  const lastSeenWeeksAgo = lastSeenValid
    ? Math.floor((now.getTime() - lastSeen.getTime()) / MS_PER_WEEK)
    : -1
  return Array.from({ length: 12 }, (_, i) => {
    // Decorative bucketing: weekStart is UTC-derived, month check uses local time.
    // At most one bar may shift class around month boundaries — acceptable.
    const weekStart = new Date(now.getTime() - (11 - i) * MS_PER_WEEK)
    const isMonth =
      weekStart.getFullYear() === now.getFullYear() &&
      weekStart.getMonth() === now.getMonth()
    const isLastSeenWeek = lastSeenWeeksAgo === 11 - i
    return { isMonth, height: isLastSeenWeek ? 24 : 4 }
  })
}

export function Patterns() {
  const [patterns, setPatterns] = useState<Pattern[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let stale = false
    api
      .get<Pattern[]>('/patterns')
      .then((arr) => {
        if (stale) return
        setPatterns(arr)
        useNavCounts.getState().setPatternCount(arr.length)
      })
      .catch((e: Error) => {
        if (!stale) setError(e.message)
      })
    return () => {
      stale = true
    }
  }, [])

  if (error) return <p style={{ color: 'var(--rust)' }}>{error}</p>
  if (!patterns) return <p style={{ color: 'var(--ink-3)' }}>Loading…</p>

  const sorted = [...patterns].sort(
    (a, b) => new Date(b.last_seen_at).getTime() - new Date(a.last_seen_at).getTime(),
  )
  const now = new Date()

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
          The recurring emotional patterns you and your guide have named — sorted by when
          you last saw them.
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
          No named patterns yet. They&apos;ll appear after a journaling session that examines a recurring experience.
        </p>
      )}

      <div className="pat-list">
        {sorted.map((p) => {
          const lastSeen = new Date(p.last_seen_at).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
          })
          const bars = weekBars(p.last_seen_at, now)
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
                  <div className="sparkline">
                    {bars.map((bar, i) => (
                      <span
                        key={`bar-${i}`}
                        className={bar.isMonth ? 'is-month' : ''}
                        style={{ height: bar.height }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </Link>
          )
        })}
      </div>
    </>
  )
}
