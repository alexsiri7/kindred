import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(),
    patch: vi.fn(),
  },
}))

import { api } from '../../api/client'
import { CrisisDisclaimerModal } from '../CrisisDisclaimerModal'

describe('CrisisDisclaimerModal', () => {
  it('shows modal when ack timestamp is null', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      timezone: null,
      transcript_enabled: true,
      crisis_disclaimer_acknowledged_at: null,
    })

    render(<CrisisDisclaimerModal />)

    await waitFor(() =>
      expect(
        screen.getByText(/Kindred is a journaling tool/i),
      ).toBeInTheDocument(),
    )
    expect(screen.getAllByText(/Samaritans/i).length).toBeGreaterThan(0)
  })

  it('hides modal when ack timestamp is set', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      timezone: null,
      transcript_enabled: true,
      crisis_disclaimer_acknowledged_at: '2026-05-03T00:00:00Z',
    })

    render(<CrisisDisclaimerModal />)

    await waitFor(() => expect(api.get).toHaveBeenCalled())
    expect(
      screen.queryByText(/Kindred is a journaling tool/i),
    ).not.toBeInTheDocument()
  })

  it('persists ack on button click and hides modal', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      timezone: null,
      transcript_enabled: true,
      crisis_disclaimer_acknowledged_at: null,
    })
    vi.mocked(api.patch).mockResolvedValueOnce({
      timezone: null,
      transcript_enabled: true,
      crisis_disclaimer_acknowledged_at: '2026-05-03T12:00:00Z',
    })

    render(<CrisisDisclaimerModal />)

    const button = await screen.findByRole('button', { name: /i understand/i })
    fireEvent.click(button)

    await waitFor(() =>
      expect(api.patch).toHaveBeenCalledWith('/settings', {
        crisis_disclaimer_acknowledged_at: expect.stringMatching(
          /^\d{4}-\d{2}-\d{2}T/,
        ),
      }),
    )
    await waitFor(() =>
      expect(
        screen.queryByText(/Kindred is a journaling tool/i),
      ).not.toBeInTheDocument(),
    )
  })
})
