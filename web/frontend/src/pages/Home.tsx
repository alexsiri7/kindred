import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { api, type EntrySummary } from '../api/client'

export function Home() {
  const [entries, setEntries] = useState<EntrySummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    api
      .get<EntrySummary[]>('/entries')
      .then(setEntries)
      .catch((e: Error) => setError(e.message))
  }, [])

  const onSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      navigate(`/search?q=${encodeURIComponent(query.trim())}`)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Recent entries</h1>
      <form onSubmit={onSearch} className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by feeling or theme…"
          className="flex-1 rounded border border-stone-300 px-3 py-2"
        />
        <button
          type="submit"
          className="rounded bg-stone-900 px-4 py-2 text-white hover:bg-stone-800"
        >
          Search
        </button>
      </form>
      {error && <p className="text-red-700">{error}</p>}
      {entries === null && !error && <p className="text-stone-500">Loading…</p>}
      {entries && entries.length === 0 && (
        <p className="text-stone-500">
          No entries yet. Start a journaling session in Claude.ai.
        </p>
      )}
      <ul className="space-y-3">
        {entries?.map((e) => (
          <li key={e.id} className="rounded border border-stone-200 bg-white p-4">
            <Link to={`/entries/${e.id}`} className="block">
              <div className="text-xs text-stone-500">{e.date}</div>
              <div className="mt-1 line-clamp-2">{e.summary}</div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}
