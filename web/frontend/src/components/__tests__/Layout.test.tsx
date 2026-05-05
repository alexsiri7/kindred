import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router'

const authState: { session: unknown; initialized: boolean } = {
  session: { user: { email: 'tester@example.com' } },
  initialized: true,
}

vi.mock('../../store/auth', () => ({
  useAuth: (
    selector: (s: { session: unknown; initialized: boolean }) => unknown,
  ) => selector(authState),
}))

const navState: { entryCount: number | null; patternCount: number | null } = {
  entryCount: null,
  patternCount: null,
}

vi.mock('../../store/navCounts', () => ({
  useNavCounts: (
    selector: (s: {
      entryCount: number | null
      patternCount: number | null
    }) => unknown,
  ) => selector(navState),
}))

vi.mock('../../lib/supabase', () => ({
  supabase: { auth: { signOut: vi.fn() } },
}))

import { Layout } from '../Layout'

describe('Layout — Report an issue link', () => {
  it('renders a sidebar link to the GitHub new-issue page', () => {
    render(
      <MemoryRouter initialEntries={['/app']}>
        <Layout />
      </MemoryRouter>,
    )

    const link = screen.getByRole('link', { name: /report an issue/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')

    const url = new URL(link.getAttribute('href') ?? '')
    expect(url.origin + url.pathname).toBe(
      'https://github.com/alexsiri7/kindred/issues/new',
    )
    expect(url.searchParams.get('template')).toBe('bug_report.md')

    const body = url.searchParams.get('body') ?? ''
    expect(body).toContain('- **Page:**')
    expect(body).toContain('- **Browser:**')
  })

  it('uses a native anchor (keyboard-activatable on Enter)', () => {
    render(
      <MemoryRouter initialEntries={['/app']}>
        <Layout />
      </MemoryRouter>,
    )
    const link = screen.getByRole('link', { name: /report an issue/i })
    expect(link.tagName).toBe('A')
  })

  it('embeds the current page path and user-agent in the issue body', () => {
    const originalUA = navigator.userAgent
    Object.defineProperty(navigator, 'userAgent', {
      value: 'TestUA/1.0',
      configurable: true,
    })
    try {
      render(
        <MemoryRouter initialEntries={['/app/entries']}>
          <Layout />
        </MemoryRouter>,
      )
      const link = screen.getByRole('link', { name: /report an issue/i })
      const body =
        new URL(link.getAttribute('href') ?? '').searchParams.get('body') ?? ''
      expect(body).toContain('- **Page:** /app/entries')
      expect(body).toContain('- **Browser:** TestUA/1.0')
    } finally {
      Object.defineProperty(navigator, 'userAgent', {
        value: originalUA,
        configurable: true,
      })
    }
  })

  it('only emits the intentional query params (no smuggling)', () => {
    render(
      <MemoryRouter initialEntries={['/app/entries']}>
        <Layout />
      </MemoryRouter>,
    )
    const link = screen.getByRole('link', { name: /report an issue/i })
    const url = new URL(link.getAttribute('href') ?? '')
    // Regression detector: a refactor that swaps URLSearchParams.set for
    // string concatenation would leak smuggled keys here.
    expect([...url.searchParams.keys()].sort()).toEqual(['body', 'template'])
  })

  it('renders the side-brand wordmark with the canonical .wm structure', () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/app']}>
        <Layout />
      </MemoryRouter>,
    )
    const sideBrand = container.querySelector('.side-brand')
    expect(sideBrand).toBeInTheDocument()
    expect(sideBrand?.querySelector('.wm em')?.textContent).toBe('Kindred')
    expect(sideBrand?.querySelector('.wm .dot')?.textContent).toBe('.')
  })

  it('does not embed window.location query/fragment in the issue body', () => {
    // Simulate a route that carries sensitive query/fragment data.
    Object.defineProperty(window, 'location', {
      value: new URL('https://app.kindred.test/app/search?q=secret#frag'),
      writable: true,
      configurable: true,
    })

    render(
      <MemoryRouter initialEntries={['/app/search']}>
        <Layout />
      </MemoryRouter>,
    )

    const link = screen.getByRole('link', { name: /report an issue/i })
    const body =
      new URL(link.getAttribute('href') ?? '').searchParams.get('body') ?? ''
    expect(body).not.toContain('q=secret')
    expect(body).not.toContain('#frag')
    expect(body).toContain('- **Page:** /app/search')
  })
})

describe('Layout — auth gate', () => {
  function renderGate() {
    return render(
      <MemoryRouter initialEntries={['/app']}>
        <Routes>
          <Route path="/app" element={<Layout />} />
          <Route path="/login" element={<div>LOGIN_ROUTE</div>} />
        </Routes>
      </MemoryRouter>,
    )
  }

  it('renders nothing while auth is still initializing (does not <Navigate>)', () => {
    authState.session = null
    authState.initialized = false
    try {
      renderGate()
      expect(screen.queryByText('LOGIN_ROUTE')).not.toBeInTheDocument()
    } finally {
      authState.session = { user: { email: 'tester@example.com' } }
      authState.initialized = true
    }
  })

  it('navigates to /login once initialized=true and session=null', () => {
    authState.session = null
    authState.initialized = true
    try {
      renderGate()
      expect(screen.getByText('LOGIN_ROUTE')).toBeInTheDocument()
    } finally {
      authState.session = { user: { email: 'tester@example.com' } }
      authState.initialized = true
    }
  })
})

describe('Layout — sidebar nav', () => {
  function findSideLink(container: HTMLElement, label: string) {
    return Array.from(container.querySelectorAll('.side-link')).find((el) =>
      el.textContent?.includes(label),
    ) as HTMLElement | undefined
  }

  it('renders count badges for Entries and Patterns when counts are loaded', () => {
    navState.entryCount = 24
    navState.patternCount = 7
    try {
      const { container } = render(
        <MemoryRouter initialEntries={['/app']}>
          <Layout />
        </MemoryRouter>,
      )
      const entriesLink = findSideLink(container, 'Entries')
      const patternsLink = findSideLink(container, 'Patterns')
      expect(entriesLink?.querySelector('.count')?.textContent).toBe('24')
      expect(patternsLink?.querySelector('.count')?.textContent).toBe('7')
    } finally {
      navState.entryCount = null
      navState.patternCount = null
    }
  })

  it('omits count badges when counts are null', () => {
    navState.entryCount = null
    navState.patternCount = null
    const { container } = render(
      <MemoryRouter initialEntries={['/app']}>
        <Layout />
      </MemoryRouter>,
    )
    const entriesLink = findSideLink(container, 'Entries')
    const patternsLink = findSideLink(container, 'Patterns')
    const searchLink = findSideLink(container, 'Search')
    expect(entriesLink?.querySelector('.count')).toBeNull()
    expect(patternsLink?.querySelector('.count')).toBeNull()
    expect(searchLink?.querySelector('.count')).toBeNull()
  })

  it('never renders a count badge on the Search nav item', () => {
    navState.entryCount = 24
    navState.patternCount = 7
    try {
      const { container } = render(
        <MemoryRouter initialEntries={['/app']}>
          <Layout />
        </MemoryRouter>,
      )
      const searchLink = findSideLink(container, 'Search')
      expect(searchLink?.querySelector('.count')).toBeNull()
    } finally {
      navState.entryCount = null
      navState.patternCount = null
    }
  })

  it("renders 'Connect to Claude' as the connect nav label", () => {
    render(
      <MemoryRouter initialEntries={['/app']}>
        <Layout />
      </MemoryRouter>,
    )
    expect(
      screen.getByRole('link', { name: /connect to claude/i }),
    ).toBeInTheDocument()
  })

  it('renders a "0" badge when count is loaded as zero (distinguishes 0 from null)', () => {
    navState.entryCount = 0
    navState.patternCount = 0
    try {
      const { container } = render(
        <MemoryRouter initialEntries={['/app']}>
          <Layout />
        </MemoryRouter>,
      )
      const entriesLink = findSideLink(container, 'Entries')
      const patternsLink = findSideLink(container, 'Patterns')
      expect(entriesLink?.querySelector('.count')?.textContent).toBe('0')
      expect(patternsLink?.querySelector('.count')?.textContent).toBe('0')
    } finally {
      navState.entryCount = null
      navState.patternCount = null
    }
  })
})
