import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { api, type SearchHit } from '../api/client'

export function Search() {
  const [params] = useSearchParams()
  const q = params.get('q') ?? ''
  const [hits, setHits] = useState<SearchHit[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!q.trim()) {
      setHits([])
      return
    }
    setHits(null)
    api
      .get<SearchHit[]>(`/search?q=${encodeURIComponent(q)}`)
      .then(setHits)
      .catch((e: Error) => setError(e.message))
  }, [q])

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Search results</h1>
      <p className="text-sm text-stone-500">Query: {q || '(empty)'}</p>
      {error && <p className="text-red-700">{error}</p>}
      {hits === null && <p className="text-stone-500">Searching…</p>}
      {hits && hits.length === 0 && q && (
        <p className="text-stone-500">No matches.</p>
      )}
      <ul className="space-y-3">
        {hits?.map((h) => (
          <li key={h.entry_id} className="rounded border border-stone-200 bg-white p-4">
            <Link to={`/entries/${h.entry_id}`} className="block">
              <div className="text-xs text-stone-500">
                similarity {h.similarity.toFixed(3)}
              </div>
              <div className="mt-1 line-clamp-2">{h.content}</div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}
