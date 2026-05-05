import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router'

vi.mock('../../api/client', () => ({
  api: { get: vi.fn() },
}))

import { PatternDetail } from '../PatternDetail'
import { api } from '../../api/client'

const samplePattern = {
  id: 'p1',
  name: 'Recurring overwhelm',
  description: 'When deadlines stack up.',
  typical_thoughts: 'I will never finish.',
  typical_emotions: 'Anxious, foggy.',
  typical_behaviors: 'Open ten tabs, close them.',
  typical_sensations: 'Tight chest.',
  last_seen_at: '2026-04-01',
  occurrence_count: 2,
  occurrences: [
    {
      id: 'o1',
      pattern_id: 'p1',
      entry_id: 'e1',
      date: '2026-04-01',
      thoughts: 'I will never finish.',
      emotions: null,
      behaviors: null,
      sensations: 'Tight chest.',
      intensity: 3,
      trigger: 'deadline',
      notes: null,
    },
    {
      id: 'o2',
      pattern_id: 'p1',
      entry_id: 'e2',
      date: '2026-03-15',
      thoughts: null,
      emotions: null,
      behaviors: null,
      sensations: null,
      intensity: 2,
      trigger: null,
      notes: null,
    },
  ],
}

function renderDetail() {
  return render(
    <MemoryRouter initialEntries={['/app/patterns/p1']}>
      <Routes>
        <Route path="/app/patterns/:id" element={<PatternDetail />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('PatternDetail', () => {
  it('renders the pattern header with the spec class names', async () => {
    vi.mocked(api.get).mockResolvedValueOnce(samplePattern)
    renderDetail()
    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: /recurring overwhelm/i }),
      ).toBeInTheDocument(),
    )
    expect(document.querySelector('.pat-detail-head')).not.toBeNull()
    expect(document.querySelector('.pat-detail-name')).not.toBeNull()
    expect(document.querySelector('.pat-detail-desc')).not.toBeNull()
    expect(document.querySelector('.pat-detail-stats')).not.toBeNull()
  })

  it('renders four .typical-q cells inside .typical', async () => {
    vi.mocked(api.get).mockResolvedValueOnce(samplePattern)
    renderDetail()
    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: /recurring overwhelm/i }),
      ).toBeInTheDocument(),
    )
    const typical = document.querySelector('.typical')
    expect(typical).not.toBeNull()
    expect(typical!.querySelectorAll('.typical-q').length).toBe(4)
  })

  it('marks the first occurrence as .is-recent and renders the timeline', async () => {
    vi.mocked(api.get).mockResolvedValueOnce(samplePattern)
    renderDetail()
    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: /recurring overwhelm/i }),
      ).toBeInTheDocument(),
    )
    const timeline = document.querySelector('.timeline')
    expect(timeline).not.toBeNull()
    const items = timeline!.querySelectorAll('.tl-item')
    expect(items.length).toBe(2)
    expect(items[0].classList.contains('is-recent')).toBe(true)
    expect(items[1].classList.contains('is-recent')).toBe(false)
  })
})
