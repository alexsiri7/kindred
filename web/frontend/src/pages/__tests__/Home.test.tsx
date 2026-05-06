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

  it('renders the title with "Your" as the italic accent', async () => {
    useNavCounts.setState({ entryCount: null })
    vi.mocked(api.get).mockResolvedValueOnce([])
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>,
    )
    expect(
      screen.getByRole('heading', { name: /your library/i }),
    ).toBeInTheDocument()
    const em = document.querySelector('.page-title em')
    expect(em?.textContent).toBe('Your')
  })

  it('renders the date column as "{monthShort} · {weekday}"', async () => {
    useNavCounts.setState({ entryCount: null })
    vi.mocked(api.get).mockResolvedValueOnce([
      {
        id: 'e1',
        date: '2026-04-04',
        summary: 'a quiet morning',
        mood: null,
        created_at: '2026-04-04T12:00:00Z',
      },
    ])
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>,
    )
    await waitFor(() => {
      const matches = screen.getAllByText(/quiet morning/i)
      expect(matches.length).toBeGreaterThan(0)
    })
    const dateCell = document.querySelector('.entry-date')
    expect(dateCell?.querySelector('.day')?.textContent).toBe('4')
    expect(dateCell?.textContent).toMatch(/Apr · Sat/)
  })

  it('renders the read-only banner above the entries list', async () => {
    useNavCounts.setState({ entryCount: null })
    vi.mocked(api.get).mockResolvedValueOnce([])
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>,
    )
    const readonlyText = screen.getByText(/read-only/i)
    expect(readonlyText).toBeInTheDocument()
    expect(readonlyText.closest('.readonly-banner')).not.toBeNull()
  })
})
