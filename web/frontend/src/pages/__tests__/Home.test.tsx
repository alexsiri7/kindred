import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(async () => []),
  },
}))

import { Home } from '../Home'

describe('Home', () => {
  it('renders the recent-entries heading', async () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>,
    )
    expect(
      screen.getByRole('heading', { name: /recent/i }),
    ).toBeInTheDocument()
    await waitFor(() =>
      expect(screen.getByText(/no entries yet/i)).toBeInTheDocument(),
    )
  })
})
