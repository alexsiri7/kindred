import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { api, type SearchHit } from '../api/client'

function SearchIcon() {
  return (
    <svg
      width={20}
      height={20}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ color: 'var(--ink-3)', flexShrink: 0 }}
    >
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-5-5" />
    </svg>
  )
}

export function Search() {
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const [inputVal, setInputVal] = useState(q)
  const [hits, setHits] = useState<SearchHit[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Sync inputVal when URL param changes
  useEffect(() => {
    setInputVal(q)
  }, [q])

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

  const handleChange = (val: string) => {
    setInputVal(val)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      if (val.trim()) {
        setParams({ q: val.trim() })
      } else {
        setParams({})
      }
    }, 300)
  }

  return (
    <>
      <div className="page-head">
        <div className="page-eye">
          <span className="glyph">◈</span> Search
        </div>
        <h1 className="page-title">
          Find by <em>feeling</em>, not just date.
        </h1>
        <p className="page-sub">
          Semantic search over your entry summaries. Try phrases — &quot;the bracing feeling&quot;,
          &quot;afternoon slump&quot;, &quot;something about my dad&quot;.
        </p>
      </div>

      <div className="search-bar">
        <SearchIcon />
        <input
          value={inputVal}
          onChange={(e) => handleChange(e.target.value)}
          placeholder="What are you looking for?"
          autoFocus
        />
        {hits !== null && (
          <span className="hint">{hits.length} {hits.length === 1 ? 'match' : 'matches'}</span>
        )}
      </div>

      {error && <p style={{ color: 'var(--rust)' }}>{error}</p>}
      {hits === null && q && <p style={{ color: 'var(--ink-3)' }}>Searching…</p>}

      {hits?.map((h) => {
        const date = new Date(h.content.slice(0, 10) + 'T12:00')
        const isValidDate = !isNaN(date.getTime())
        return (
          <Link
            key={h.entry_id}
            to={`/entries/${h.entry_id}`}
            style={{ textDecoration: 'none', color: 'inherit' }}
          >
            <div className="search-result">
              <div className="search-result-head">
                <span className="search-result-date">
                  {isValidDate
                    ? date.toLocaleDateString('en-US', {
                        weekday: 'short',
                        month: 'short',
                        day: 'numeric',
                      })
                    : 'Entry'}
                </span>
                <span className="search-result-score">
                  {(h.similarity * 100).toFixed(0)}% match
                </span>
              </div>
              <p className="search-result-snippet">{h.content}</p>
            </div>
          </Link>
        )
      })}
    </>
  )
}
