import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(async () => []),
  },
}))

import { Search } from '../Search'
import { api } from '../../api/client'

describe('Search', () => {
  it('renders the spec page title', () => {
    render(
      <MemoryRouter>
        <Search />
      </MemoryRouter>,
    )
    expect(
      screen.getByRole('heading', { name: /search the archive/i }),
    ).toBeInTheDocument()
  })

  it('shows the empty-state prompt when there is no query', () => {
    render(
      <MemoryRouter>
        <Search />
      </MemoryRouter>,
    )
    expect(screen.getByText(/try a phrase/i)).toBeInTheDocument()
    expect(screen.getByText(/search by feeling/i)).toBeInTheDocument()
  })

  it('shows "Nothing found for …" when a query returns no hits', async () => {
    vi.mocked(api.get).mockResolvedValueOnce([])
    render(
      <MemoryRouter initialEntries={['/app/search?q=zzz']}>
        <Search />
      </MemoryRouter>,
    )
    await waitFor(() =>
      expect(screen.getByText(/nothing found for/i)).toBeInTheDocument(),
    )
  })
})
