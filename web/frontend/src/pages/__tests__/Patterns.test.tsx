import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(async () => []),
  },
}))

import { Patterns } from '../Patterns'
import { api } from '../../api/client'
import { useNavCounts } from '../../store/navCounts'

const samplePatterns = [
  {
    id: 'p1',
    name: 'Recurring overwhelm',
    description: null,
    typical_thoughts: null,
    typical_emotions: null,
    typical_behaviors: null,
    typical_sensations: null,
    last_seen_at: '2026-04-01',
    occurrence_count: 4,
  },
  {
    id: 'p2',
    name: 'Sunday dread',
    description: null,
    typical_thoughts: null,
    typical_emotions: null,
    typical_behaviors: null,
    typical_sensations: null,
    last_seen_at: '2026-04-15',
    occurrence_count: 2,
  },
]

describe('Patterns', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders the patterns heading', async () => {
    useNavCounts.setState({ patternCount: null })
    vi.mocked(api.get).mockResolvedValueOnce(samplePatterns)
    render(
      <MemoryRouter>
        <Patterns />
      </MemoryRouter>,
    )
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /keeps/i })).toBeInTheDocument(),
    )
  })

  it('publishes the pattern count to useNavCounts after fetch', async () => {
    useNavCounts.setState({ patternCount: null })
    vi.mocked(api.get).mockResolvedValueOnce(samplePatterns)
    render(
      <MemoryRouter>
        <Patterns />
      </MemoryRouter>,
    )
    await waitFor(() =>
      expect(useNavCounts.getState().patternCount).toBe(2),
    )
  })

  it('renders the spec subtitle', async () => {
    useNavCounts.setState({ patternCount: null })
    vi.mocked(api.get).mockResolvedValueOnce(samplePatterns)
    render(
      <MemoryRouter>
        <Patterns />
      </MemoryRouter>,
    )
    await waitFor(() =>
      expect(screen.getByText(/recurring emotional patterns/i)).toBeInTheDocument(),
    )
  })

  it('renders a 12-bar sparkline per pattern card', async () => {
    useNavCounts.setState({ patternCount: null })
    vi.mocked(api.get).mockResolvedValueOnce(samplePatterns)
    render(
      <MemoryRouter>
        <Patterns />
      </MemoryRouter>,
    )
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /keeps/i })).toBeInTheDocument(),
    )
    expect(document.querySelectorAll('.sparkline span').length).toBe(
      12 * samplePatterns.length,
    )
  })

  it('marks bars in the current month with .is-month', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.setSystemTime(new Date('2026-05-05T12:00:00Z'))
    useNavCounts.setState({ patternCount: null })
    vi.mocked(api.get).mockResolvedValueOnce([
      {
        id: 'p1',
        name: 'Recurring overwhelm',
        description: null,
        typical_thoughts: null,
        typical_emotions: null,
        typical_behaviors: null,
        typical_sensations: null,
        last_seen_at: '2026-05-04',
        occurrence_count: 1,
      },
    ])
    render(
      <MemoryRouter>
        <Patterns />
      </MemoryRouter>,
    )
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /keeps/i })).toBeInTheDocument(),
    )
    expect(
      document.querySelectorAll('.sparkline span.is-month').length,
    ).toBeGreaterThanOrEqual(1)
  })
})
