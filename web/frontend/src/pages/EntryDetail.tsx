import { useEffect, useState } from 'react'
import { useParams } from 'react-router'
import { api, type Entry } from '../api/client'

export function EntryDetail() {
  const { id } = useParams<{ id: string }>()
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

  if (error) return <p className="text-red-700">{error}</p>
  if (!entry) return <p className="text-stone-500">Loading…</p>

  return (
    <article className="prose max-w-none">
      <div className="text-xs text-stone-500">{entry.date}</div>
      {entry.mood && (
        <div className="mt-1 text-sm text-stone-600">Mood: {entry.mood}</div>
      )}
      <p className="mt-4 whitespace-pre-wrap">{entry.summary}</p>

      {entry.occurrences && entry.occurrences.length > 0 && (
        <section className="mt-8">
          <h2 className="text-lg font-semibold">Patterns this session</h2>
          <ul className="mt-2 space-y-2">
            {entry.occurrences.map((o) => (
              <li
                key={o.id}
                className="rounded border border-stone-200 bg-white p-3 text-sm"
              >
                <div className="text-stone-500">Pattern: {o.pattern_id}</div>
                {o.thoughts && <div>Thoughts: {o.thoughts}</div>}
                {o.emotions && <div>Emotions: {o.emotions}</div>}
                {o.behaviors && <div>Behaviors: {o.behaviors}</div>}
                {o.sensations && <div>Sensations: {o.sensations}</div>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {entry.transcript && (
        <section className="mt-8">
          <button
            type="button"
            onClick={() => setShowTranscript((v) => !v)}
            className="text-sm text-stone-600 underline"
          >
            {showTranscript ? 'Hide' : 'Show'} transcript
          </button>
          {showTranscript && (
            <div className="mt-2 space-y-2 text-sm">
              {entry.transcript.map((m, i) => (
                <div key={i}>
                  <span className="font-semibold">{m.role}:</span> {m.content}
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </article>
  )
}
