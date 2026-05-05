import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'

vi.stubGlobal(
  'IntersectionObserver',
  class {
    observe() {}
    disconnect() {}
    unobserve() {}
    takeRecords() { return [] }
  },
)

const authState: { session: unknown; initialized: boolean } = {
  session: null,
  initialized: true,
}
vi.mock('../../store/auth', () => ({
  useAuth: (
    selector: (s: { session: unknown; initialized: boolean }) => unknown,
  ) => selector(authState),
}))

import { Landing } from '../Landing'

beforeEach(() => {
  authState.session = null
  authState.initialized = true
})

describe('Landing — structural landmarks', () => {
  it('renders the four nav anchor labels per #32 spec', () => {
    const { container } = render(<MemoryRouter><Landing /></MemoryRouter>)
    const nav = container.querySelector('nav.nav') as HTMLElement
    expect(nav).toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: 'How it works' })).toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: 'A session' })).toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: 'Patterns' })).toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: 'Privacy' })).toBeInTheDocument()
  })

  it('renders the hero "See a session" and "How it works" CTAs', () => {
    const { container } = render(<MemoryRouter><Landing /></MemoryRouter>)
    const hero = container.querySelector('section.hero') as HTMLElement
    expect(hero).toBeInTheDocument()
    expect(within(hero).getByRole('button', { name: /see a session/i })).toBeInTheDocument()
    expect(within(hero).getByRole('button', { name: /how it works/i })).toBeInTheDocument()
  })

  it('renders three step cards in HowItWorks', () => {
    const { container } = render(<MemoryRouter><Landing /></MemoryRouter>)
    expect(container.querySelectorAll('.step')).toHaveLength(3)
  })

  it('renders the chat window with chrome bar and MCP pulse badge', () => {
    const { container } = render(<MemoryRouter><Landing /></MemoryRouter>)
    expect(container.querySelector('.chat')).toBeInTheDocument()
    expect(container.querySelector('.chrome-mcp .pulse')).toBeInTheDocument()
  })

  it('renders the Hot Cross Bun grid with four quadrants and a center medallion', () => {
    const { container } = render(<MemoryRouter><Landing /></MemoryRouter>)
    expect(container.querySelectorAll('.bun-q')).toHaveLength(4)
    expect(container.querySelector('.bun-center')).toBeInTheDocument()
  })

  it('renders four Privacy cards', () => {
    const { container } = render(<MemoryRouter><Landing /></MemoryRouter>)
    expect(container.querySelectorAll('.priv')).toHaveLength(4)
  })

  it('renders the EndCap and footer with version mark', () => {
    const { container } = render(<MemoryRouter><Landing /></MemoryRouter>)
    expect(container.querySelector('.endcap')).toBeInTheDocument()
    expect(container.querySelector('.foot')).toBeInTheDocument()
    expect(screen.getByText(/v0\.1/)).toBeInTheDocument()
  })
})

describe('Landing — session-aware nav CTA', () => {
  it('shows "Sign in" as a btn-ghost when no session', () => {
    const { container } = render(<MemoryRouter><Landing /></MemoryRouter>)
    const nav = container.querySelector('nav.nav') as HTMLElement
    const signIn = within(nav).getByRole('link', { name: /sign in/i })
    expect(signIn).toBeInTheDocument()
    expect(signIn).toHaveClass('btn', 'btn-ghost', 'btn-sm')
    expect(within(nav).getByRole('link', { name: /connect your ai/i })).toHaveClass(
      'btn',
      'btn-primary',
      'btn-sm',
    )
  })

  it('shows "Open app" instead of "Sign in" when session is set', () => {
    authState.session = { user: { email: 'tester@example.com' } }
    const { container } = render(<MemoryRouter><Landing /></MemoryRouter>)
    const nav = container.querySelector('nav.nav') as HTMLElement
    expect(within(nav).getByRole('link', { name: /open app/i })).toBeInTheDocument()
    expect(within(nav).queryByRole('link', { name: /^sign in$/i })).toBeNull()
  })
})
