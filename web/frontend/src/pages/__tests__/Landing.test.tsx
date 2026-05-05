import { describe, expect, it, vi, beforeEach, afterAll } from 'vitest'
import { act, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'

let observerCallback: IntersectionObserverCallback | null = null
const disconnectSpy = vi.fn()
const observeSpy = vi.fn()

vi.stubGlobal(
  'IntersectionObserver',
  class {
    constructor(cb: IntersectionObserverCallback) {
      observerCallback = cb
    }
    observe(target: Element) { observeSpy(target) }
    disconnect() { disconnectSpy() }
    unobserve() {}
    takeRecords() { return [] }
  },
)

afterAll(() => {
  vi.unstubAllGlobals()
})

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
  observerCallback = null
  disconnectSpy.mockClear()
  observeSpy.mockClear()
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
    const signIn = within(nav).getByRole('link', { name: /^sign in$/i })
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

describe('Landing — scroll-spy', () => {
  const fakeEntry = (id: string, ratio: number): IntersectionObserverEntry =>
    ({
      target: { id } as Element,
      isIntersecting: ratio > 0,
      intersectionRatio: ratio,
    } as IntersectionObserverEntry)

  it('observes each in-page section on mount', () => {
    render(<MemoryRouter><Landing /></MemoryRouter>)
    expect(observeSpy).toHaveBeenCalled()
    const observedIds = observeSpy.mock.calls.map(([el]) => (el as HTMLElement).id)
    expect(observedIds).toEqual(expect.arrayContaining(['how', 'demo', 'patterns']))
    expect(observedIds).not.toContain('privacy')
  })

  it('marks the most-visible section as is-active and sets aria-current=location', () => {
    const { container } = render(<MemoryRouter><Landing /></MemoryRouter>)
    expect(observerCallback).not.toBeNull()

    act(() => {
      observerCallback!(
        [fakeEntry('how', 0.2), fakeEntry('demo', 0.8), fakeEntry('patterns', 0.1)],
        {} as IntersectionObserver,
      )
    })

    const nav = container.querySelector('nav.nav') as HTMLElement
    const active = within(nav).getByRole('link', { name: 'A session' })
    expect(active).toHaveClass('is-active')
    expect(active).toHaveAttribute('aria-current', 'location')

    const inactive = within(nav).getByRole('link', { name: 'How it works' })
    expect(inactive).not.toHaveClass('is-active')
    expect(inactive).not.toHaveAttribute('aria-current')
  })

  it('does not change activeId when no section is intersecting', () => {
    const { container } = render(<MemoryRouter><Landing /></MemoryRouter>)
    act(() => {
      observerCallback!(
        [fakeEntry('how', 0)],
        {} as IntersectionObserver,
      )
    })
    const nav = container.querySelector('nav.nav') as HTMLElement
    expect(within(nav).getByRole('link', { name: 'How it works' })).not.toHaveClass('is-active')
  })

  it('disconnects the IntersectionObserver on unmount', () => {
    const { unmount } = render(<MemoryRouter><Landing /></MemoryRouter>)
    expect(disconnectSpy).not.toHaveBeenCalled()
    unmount()
    expect(disconnectSpy).toHaveBeenCalled()
  })
})
