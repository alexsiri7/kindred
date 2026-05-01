import { useEffect, useState } from 'react'
import { useParams } from 'react-router'
import { api, type Pattern } from '../api/client'

export function PatternDetail() {
  const { id } = useParams<{ id: string }>()
  const [pattern, setPattern] = useState<Pattern | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    api
      .get<Pattern>(`/patterns/${id}`)
      .then(setPattern)
      .catch((e: Error) => setError(e.message))
  }, [id])

  if (error) return <p className="text-red-700">{error}</p>
  if (!pattern) return <p className="text-stone-500">Loading…</p>

  return (
    <article className="prose max-w-none">
      <h1>{pattern.name}</h1>
      {pattern.description && <p>{pattern.description}</p>}
      <section className="not-prose mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Quadrant title="Typical thoughts" value={pattern.typical_thoughts} />
        <Quadrant title="Typical emotions" value={pattern.typical_emotions} />
        <Quadrant title="Typical behaviors" value={pattern.typical_behaviors} />
        <Quadrant title="Typical sensations" value={pattern.typical_sensations} />
      </section>
      <h2 className="mt-8">Occurrences</h2>
      <ul className="space-y-3">
        {pattern.occurrences?.map((o) => (
          <li key={o.id} className="rounded border border-stone-200 bg-white p-4 text-sm">
            <div className="text-xs text-stone-500">{o.date}</div>
            {o.thoughts && <div>Thoughts: {o.thoughts}</div>}
            {o.emotions && <div>Emotions: {o.emotions}</div>}
            {o.behaviors && <div>Behaviors: {o.behaviors}</div>}
            {o.sensations && <div>Sensations: {o.sensations}</div>}
          </li>
        ))}
      </ul>
    </article>
  )
}

function Quadrant({ title, value }: { title: string; value: string | null }) {
  return (
    <div className="rounded border border-stone-200 bg-white p-4">
      <div className="text-xs uppercase tracking-wide text-stone-500">{title}</div>
      <div className="mt-1 text-sm">{value || '—'}</div>
    </div>
  )
}
