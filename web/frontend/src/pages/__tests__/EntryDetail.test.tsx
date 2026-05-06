import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router'

vi.mock('../../api/client', () => ({
  api: { get: vi.fn() },
}))

import { EntryDetail } from '../EntryDetail'
import { api } from '../../api/client'

const sampleEntry = {
  id: 'e1',
  date: '2026-04-04',
  summary:
    'I noticed the morning had a softness to it, like the air itself was unhurried.',
  mood: 'tender',
  created_at: '2026-04-04T08:00:00Z',
  transcript: [
    { role: 'assistant', content: 'How is your morning landing for you?' },
    { role: 'user', content: 'Quiet. A little tender.' },
  ],
  occurrences: [
    {
      id: 'o1',
      pattern_id: 'p1',
      entry_id: 'e1',
      date: '2026-04-04',
      thoughts: 'I should be doing more.',
      emotions: 'Wistful.',
      behaviors: 'Stared at the kettle.',
      sensations: 'Warm chest.',
      intensity: 3,
      trigger: 'morning',
      notes: null,
    },
  ],
}

function renderDetail() {
  return render(
    <MemoryRouter initialEntries={['/app/entries/e1']}>
      <Routes>
        <Route path="/app/entries/:id" element={<EntryDetail />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('EntryDetail', () => {
  it('renders the entry header with the spec class names', async () => {
    vi.mocked(api.get).mockResolvedValueOnce(sampleEntry)
    renderDetail()
    await waitFor(() =>
      expect(document.querySelector('.entry-detail-head')).not.toBeNull(),
    )
    expect(document.querySelector('.entry-detail-date')).not.toBeNull()
    expect(document.querySelector('.entry-detail-meta')).not.toBeNull()
    expect(document.querySelector('.entry-detail-meta .mood-big')).not.toBeNull()
  })

  it('renders the italic display summary with .entry-summary', async () => {
    vi.mocked(api.get).mockResolvedValueOnce(sampleEntry)
    renderDetail()
    await waitFor(() =>
      expect(document.querySelector('.entry-summary')).not.toBeNull(),
    )
    expect(document.querySelector('.entry-summary')!.textContent).toContain(
      'softness',
    )
  })

  it('renders an occurrence card with quadrants', async () => {
    vi.mocked(api.get).mockResolvedValueOnce(sampleEntry)
    renderDetail()
    await waitFor(() =>
      expect(document.querySelector('.occ-card')).not.toBeNull(),
    )
    expect(document.querySelector('.occ-head')).not.toBeNull()
    expect(document.querySelector('.occ-name .glyph')).not.toBeNull()
    const quads = document.querySelector('.occ-quads')
    expect(quads).not.toBeNull()
    expect(quads!.querySelectorAll('.occ-quad-label').length).toBe(4)
  })

  it('renders the transcript toggle and body with disclosure semantics', async () => {
    vi.mocked(api.get).mockResolvedValueOnce(sampleEntry)
    renderDetail()
    await waitFor(() =>
      expect(document.querySelector('.transcript-toggle')).not.toBeNull(),
    )
    const toggle = document.querySelector('.transcript-toggle') as HTMLButtonElement
    expect(toggle.getAttribute('aria-expanded')).toBe('false')
    expect(toggle.getAttribute('aria-controls')).toBe('entry-transcript-body')

    const body = document.querySelector('.transcript-body') as HTMLElement
    expect(body).not.toBeNull()
    expect(body.id).toBe('entry-transcript-body')
    expect(body.hasAttribute('hidden')).toBe(true)

    fireEvent.click(toggle)

    expect(toggle.getAttribute('aria-expanded')).toBe('true')
    expect(toggle.classList.contains('is-open')).toBe(true)
    expect(body.hasAttribute('hidden')).toBe(false)
    expect(document.querySelector('.t-msg.kindred')).not.toBeNull()

    fireEvent.click(toggle)

    expect(toggle.getAttribute('aria-expanded')).toBe('false')
    expect(toggle.classList.contains('is-open')).toBe(false)
    expect(body.hasAttribute('hidden')).toBe(true)
  })

  it('marks the chevron as decorative for screen readers', async () => {
    vi.mocked(api.get).mockResolvedValueOnce(sampleEntry)
    renderDetail()
    await waitFor(() =>
      expect(document.querySelector('.transcript-toggle')).not.toBeNull(),
    )
    const chev = document.querySelector('.transcript-toggle .chev')
    expect(chev).not.toBeNull()
    expect(chev!.getAttribute('aria-hidden')).toBe('true')
  })

  it('renders the back link with mono spec styling', async () => {
    vi.mocked(api.get).mockResolvedValueOnce(sampleEntry)
    renderDetail()
    await waitFor(() => expect(document.querySelector('.back-link')).not.toBeNull())
    expect(screen.getByRole('button', { name: /all entries/i })).toBeInTheDocument()
  })
})
