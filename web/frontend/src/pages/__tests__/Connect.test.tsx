import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'

vi.mock('../../api/client', () => ({
  api: {
    post: vi.fn(async () => ({ token: 'kdr_test_token', created_at: null })),
  },
}))

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
    expect(screen.getByRole('tab', { name: /claude/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /chatgpt/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /gemini/i })).toBeInTheDocument()
  })

  it('selects the claude tab by default', () => {
    renderConnect()
    expect(screen.getByRole('tab', { name: /claude/i })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(screen.getByRole('tab', { name: /chatgpt/i })).toHaveAttribute(
      'aria-selected',
      'false',
    )
  })

  it('switches panel content when ChatGPT tab is clicked', () => {
    renderConnect()
    const chatgptTab = screen.getByRole('tab', { name: /chatgpt/i })
    fireEvent.click(chatgptTab)
    expect(chatgptTab).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByText(/save_entry runs/i)).toBeInTheDocument()
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
})
