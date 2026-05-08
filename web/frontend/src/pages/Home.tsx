import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { api, type EntrySummary } from '../api/client'
import { useNavCounts } from '../store/navCounts'

function formatEntryDate(dateStr: string) {
  const d = new Date(dateStr + 'T12:00')
  return {
    day: d.getDate().toString(),
    weekday: d.toLocaleDateString('en-US', { weekday: 'short' }),
    monthShort: d.toLocaleDateString('en-US', { month: 'short' }),
    month: d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }),
  }
}

function groupByMonth(entries: EntrySummary[]): Record<string, EntrySummary[]> {
  const groups: Record<string, EntrySummary[]> = {}
  for (const entry of entries) {
    const { month } = formatEntryDate(entry.date)
    if (!groups[month]) groups[month] = []
    groups[month].push(entry)
  }
  return groups
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + '…' : s
}

export function Home() {
  const [entries, setEntries] = useState<EntrySummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let stale = false
    api
      .get<EntrySummary[]>('/entries')
      .then((arr) => {
        if (stale) return
        setEntries(arr)
        useNavCounts.setState({ entryCount: arr.length })
      })
      .catch((e: Error) => {
        if (!stale) setError(e.message)
      })
    return () => {
      stale = true
    }
  }, [])

  const byMonth = entries ? groupByMonth(entries) : {}

  return (
    <>
      <div className="page-head">
        <div className="page-eye">
          <span className="glyph">◈</span> Journal
        </div>
        <h1 className="page-title">
          <em>Your</em> library
        </h1>
        <p className="page-sub">Your entries, kept quietly.</p>
      </div>

      {error && <p style={{ color: 'var(--rust)' }}>{error}</p>}
      {entries === null && <p style={{ color: 'var(--ink-3)' }}>Loading…</p>}

      <div className="readonly-banner">
        <span className="lock">🔒</span>
        <span>
          <strong>Read-only.</strong> Entries are written through the journaling conversation in
          your AI assistant — not from here.
        </span>
      </div>

      {entries?.length === 0 && (
        <p style={{ color: 'var(--ink-3)' }}>
          No entries yet. Start a journaling session in your AI assistant.
        </p>
      )}

      {Object.entries(byMonth).map(([month, items]) => (
        <div key={month}>
          <div className="month-div">{month}</div>
          {items.map((entry) => {
            const { day, weekday, monthShort } = formatEntryDate(entry.date)
            const title = truncate(entry.summary, 80)
            const body = truncate(entry.summary, 200)

            return (
              <Link
                key={entry.id}
                to={`/app/entries/${entry.id}`}
                style={{ textDecoration: 'none', color: 'inherit' }}
              >
                <div className="entry-row">
                  <div className="entry-date">
                    <span className="day">{day}</span>
                    {monthShort} · {weekday}
                  </div>
                  <div className="entry-body">
                    <h3>{title}</h3>
                    <p>{body}</p>
                  </div>
                  <div className="entry-meta">
                    {entry.mood && <span className="mood">◉ {entry.mood}</span>}
                  </div>
                </div>
              </Link>
            )
          })}
        </div>
      ))}
    </>
  )
}
