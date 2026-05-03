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

  it.each([
    {
      key: 'claude',
      label: /claude/i,
      panelText: /one gentle open question/i,
    },
    {
      key: 'chatgpt',
      label: /chatgpt/i,
      panelText: /save_entry runs/i,
    },
    {
      key: 'gemini',
      label: /gemini/i,
      panelText: /confirm the AI asks one open question/i,
    },
  ])('renders $key panel content when its tab is selected', ({ label, panelText }) => {
    renderConnect()
    fireEvent.click(screen.getByRole('tab', { name: label }))
    expect(screen.getByRole('tab', { name: label })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(screen.getByText(panelText)).toBeInTheDocument()
  })

  it('copies the exact ONE_LINER string when the one-liner copy button is clicked', async () => {
    renderConnect()
    fireEvent.click(
      screen.getByRole('button', { name: /copy one-liner instruction/i }),
    )
    await waitFor(() =>
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(ONE_LINER),
    )
  })

  it('shows an error message when clipboard write fails', async () => {
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn(async () => {
          throw new Error('NotAllowedError: clipboard blocked')
        }),
      },
    })
    renderConnect()
    fireEvent.click(
      screen.getByRole('button', { name: /copy one-liner instruction/i }),
    )
    await waitFor(() =>
      expect(screen.getByText(/couldn't copy to clipboard/i)).toBeInTheDocument(),
    )
  })

  it('renders the provider-neutral page heading', () => {
    renderConnect()
    expect(
      screen.getByRole('heading', { name: /connect kindred to your ai assistant/i }),
    ).toBeInTheDocument()
  })
})
