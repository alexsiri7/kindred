import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(async () => []),
  },
}))

import { Home } from '../Home'
import { api } from '../../api/client'
import { useNavCounts } from '../../store/navCounts'

describe('Home', () => {
  it('renders the journal library heading', async () => {
    useNavCounts.setState({ entryCount: null })
    vi.mocked(api.get).mockResolvedValueOnce([])
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>,
    )
    expect(
      screen.getByRole('heading', { name: /library/i }),
    ).toBeInTheDocument()
    await waitFor(() =>
      expect(screen.getByText(/no entries yet/i)).toBeInTheDocument(),
    )
  })

  it('publishes the entry count to useNavCounts after fetch', async () => {
    useNavCounts.setState({ entryCount: null })
    vi.mocked(api.get).mockResolvedValueOnce([
      { id: 'a', date: '2026-01-01', summary: 'x', mood: null, created_at: '2026-01-01T00:00:00Z' },
      { id: 'b', date: '2026-01-02', summary: 'y', mood: null, created_at: '2026-01-02T00:00:00Z' },
      { id: 'c', date: '2026-01-03', summary: 'z', mood: null, created_at: '2026-01-03T00:00:00Z' },
    ])
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>,
    )
    await waitFor(() =>
      expect(useNavCounts.getState().entryCount).toBe(3),
    )
  })
})
