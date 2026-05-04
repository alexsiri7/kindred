import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'

vi.mock('../../api/client', () => ({
  api: {
    post: vi.fn(async () => ({
      token: 'kdr_test_token',
      created_at: '2026-05-04T00:00:00Z',
      expires_at: null,
    })),
  },
}))

import { api } from '../../api/client'
import { Connect, ONE_LINER } from '../Connect'

const renderConnect = () =>
  render(
    <MemoryRouter>
      <Connect />
    </MemoryRouter>,
  )

describe('Connect', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn(async () => undefined) },
    })
  })

  afterEach(() => {
    act(() => {
      vi.runOnlyPendingTimers()
    })
    vi.useRealTimers()
  })

  it('renders all three client tabs', () => {
    renderConnect()
    expect(screen.getByRole('tab', { name: /claude desktop/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /cursor/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /windsurf/i })).toBeInTheDocument()
  })

  it('selects the claude-desktop tab by default', () => {
    renderConnect()
    expect(screen.getByRole('tab', { name: /claude desktop/i })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(screen.getByRole('tab', { name: /cursor/i })).toHaveAttribute(
      'aria-selected',
      'false',
    )
  })

  it('switches panel content when Cursor tab is clicked', () => {
    renderConnect()
    const cursorTab = screen.getByRole('tab', { name: /cursor/i })
    fireEvent.click(cursorTab)
    expect(cursorTab).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByText(/agent mode/i)).toBeInTheDocument()
  })

  it('copies the exact ONE_LINER string when the one-liner copy button is clicked', async () => {
    renderConnect()
    const oneLinerCode = screen.getByText(ONE_LINER)
    const copyButton = oneLinerCode.parentElement?.querySelector('button')
    expect(copyButton).toBeTruthy()
    fireEvent.click(copyButton!)
    await waitFor(() =>
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(ONE_LINER),
    )
  })

  it('renders the provider-neutral page heading', () => {
    renderConnect()
    expect(
      screen.getByRole('heading', { name: /connect kindred to your ai assistant/i }),
    ).toBeInTheDocument()
  })

  it('renders the password warning banner above the token reveal', () => {
    renderConnect()
    const banner = screen.getByText(/treat this token like a password/i)
    expect(banner).toBeInTheDocument()
    // Pin position: the banner must come before the token-reveal code element
    // in document order so users see the warning before the token value.
    const tokenReveal = screen.getByText(/kdr_••••••••••••••••••••••••/)
    // Node.compareDocumentPosition: DOCUMENT_POSITION_FOLLOWING (4) means
    // tokenReveal follows banner in document order.
    expect(banner.compareDocumentPosition(tokenReveal)).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    )
  })

  it('renders the expiry date after minting', async () => {
    ;(api.post as Mock).mockResolvedValueOnce({
      token: 'kdr_x',
      created_at: '2026-05-04T00:00:00Z',
      expires_at: '2026-08-02T00:00:00Z',
    })
    renderConnect()
    fireEvent.click(screen.getByRole('button', { name: /mint token/i }))
    expect(await screen.findByText(/Expires .*2026/i)).toBeInTheDocument()
  })
})
