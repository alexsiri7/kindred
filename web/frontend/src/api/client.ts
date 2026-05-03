import { useAuth } from '../store/auth'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8001'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const session = useAuth.getState().session
  const headers = new Headers(init.headers)
  if (session?.access_token) {
    headers.set('Authorization', `Bearer ${session.access_token}`)
  }
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new ApiError(res.status, text || res.statusText)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: 'GET' }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: 'PATCH',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}

export type EntrySummary = {
  id: string
  date: string
  summary: string
  mood: string | null
  created_at: string
}

export type Entry = EntrySummary & {
  transcript?: Array<{ role: string; content: string }> | null
  occurrences?: PatternOccurrence[]
}

export type Pattern = {
  id: string
  name: string
  description: string | null
  typical_thoughts: string | null
  typical_emotions: string | null
  typical_behaviors: string | null
  typical_sensations: string | null
  last_seen_at: string
  occurrence_count: number
  occurrences?: PatternOccurrence[]
}

export type PatternOccurrence = {
  id: string
  pattern_id: string
  entry_id: string
  date: string
  thoughts: string | null
  emotions: string | null
  behaviors: string | null
  sensations: string | null
  intensity: number | null
  trigger: string | null
  notes: string | null
}

export type SearchHit = {
  entry_id: string
  similarity: number
  content: string
}

export type UserSettings = {
  timezone: string | null
  transcript_enabled: boolean
  crisis_disclaimer_acknowledged_at: string | null
}

export type ConnectorToken = {
  token: string
  created_at: string | null
}
