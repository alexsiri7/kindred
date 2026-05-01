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

  if (error) return <p className="text-red-700">{error}</p>
  if (!patterns) return <p className="text-stone-500">Loading…</p>

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Patterns</h1>
      {patterns.length === 0 && (
        <p className="text-stone-500">
          No named patterns yet. They'll appear once /kindred-hcb logs an
          occurrence.
        </p>
      )}
      <ul className="space-y-3">
        {patterns.map((p) => (
          <li key={p.id} className="rounded border border-stone-200 bg-white p-4">
            <Link to={`/patterns/${p.id}`} className="block">
              <div className="font-semibold">{p.name}</div>
              <div className="mt-1 text-xs text-stone-500">
                last seen {new Date(p.last_seen_at).toLocaleDateString()} ·{' '}
                {p.occurrence_count} occurrences
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}
