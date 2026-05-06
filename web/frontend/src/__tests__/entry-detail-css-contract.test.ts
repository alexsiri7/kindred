import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const css = readFileSync(resolve(__dirname, '../index.css'), 'utf8')

describe('EntryDetail back-link contract (#26)', () => {
  it('.back-link uses mono uppercase ink-3 with reset button chrome', () => {
    const match = css.match(/\.back-link\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('font-family: var(--font-mono)')
    expect(match![1]).toContain('font-size: 11px')
    expect(match![1]).toContain('color: var(--ink-3)')
    expect(match![1]).toContain('text-transform: uppercase')
    expect(match![1]).toContain('letter-spacing: 0.08em')
    expect(match![1]).toContain('background: none')
    expect(match![1]).toContain('border: none')
  })

  it('.back-link:hover paints terracotta', () => {
    const match = css.match(/\.back-link:hover\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('color: var(--terracotta)')
  })
})

describe('EntryDetail head + date + meta contract (#26)', () => {
  it('.entry-detail-head is a baseline-aligned flex row with bottom rule', () => {
    const match = css.match(/\.entry-detail-head\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('display: flex')
    expect(match![1]).toContain('align-items: baseline')
    expect(match![1]).toContain('justify-content: space-between')
    expect(match![1]).toContain('padding-bottom: var(--sp-5)')
    expect(match![1]).toContain('border-bottom: 1px solid var(--border)')
  })

  it('.entry-detail-date is large display italic', () => {
    const match = css.match(/\.entry-detail-date\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('font-family: var(--font-display)')
    expect(match![1]).toContain('font-size: 36px')
    expect(match![1]).toContain('font-style: italic')
  })

  it('.entry-detail-meta is mono ink-3 right-aligned', () => {
    const match = css.match(/\.entry-detail-meta\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('font-family: var(--font-mono)')
    expect(match![1]).toContain('font-size: 11px')
    expect(match![1]).toContain('color: var(--ink-3)')
    expect(match![1]).toContain('text-align: right')
  })

  it('.entry-detail-meta .mood-big is block-level terracotta 13px', () => {
    const match = css.match(/\.entry-detail-meta \.mood-big\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('color: var(--terracotta)')
    expect(match![1]).toContain('font-size: 13px')
    expect(match![1]).toContain('display: block')
    expect(match![1]).toContain('margin-bottom: 4px')
  })
})

describe('EntryDetail summary + drop-cap contract (#26)', () => {
  it('.entry-summary is italic display 22px max 56ch', () => {
    const match = css.match(/\.entry-summary\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('font-family: var(--font-display)')
    expect(match![1]).toContain('font-style: italic')
    expect(match![1]).toContain('font-size: 22px')
    expect(match![1]).toContain('line-height: 1.45')
    expect(match![1]).toContain('max-width: 56ch')
  })

  it('.entry-summary::first-letter applies a drop cap', () => {
    const match = css.match(/\.entry-summary::first-letter\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('font-size: 1.4em')
  })
})

describe('EntryDetail occurrence card contract (#26)', () => {
  it('.entry-section-eye is the mono uppercase ink-3 eyebrow', () => {
    const match = css.match(/\.entry-section-eye\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('font-family: var(--font-mono)')
    expect(match![1]).toContain('font-size: 10px')
    expect(match![1]).toContain('color: var(--ink-3)')
    expect(match![1]).toContain('text-transform: uppercase')
    expect(match![1]).toContain('letter-spacing: 0.14em')
  })

  it('.occ-card sits on paper-2 with a bordered rounded shell', () => {
    const match = css.match(/\.occ-card\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('background: var(--paper-2)')
    expect(match![1]).toContain('border: 1px solid var(--border)')
    expect(match![1]).toContain('border-radius: var(--r-md)')
    expect(match![1]).toContain('padding: var(--sp-4)')
  })

  it('.occ-head is a baseline-aligned space-between row', () => {
    const match = css.match(/\.occ-head\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('display: flex')
    expect(match![1]).toContain('justify-content: space-between')
    expect(match![1]).toContain('align-items: baseline')
  })

  it('.occ-name is italic display 18px', () => {
    const match = css.match(/\.occ-name\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('font-family: var(--font-display)')
    expect(match![1]).toContain('font-style: italic')
    expect(match![1]).toContain('font-size: 18px')
  })

  it('.occ-name .glyph is terracotta', () => {
    const match = css.match(/\.occ-name \.glyph\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('color: var(--terracotta)')
  })

  it('.occ-intensity is mono ink-3 11px', () => {
    const match = css.match(/\.occ-intensity\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('font-family: var(--font-mono)')
    expect(match![1]).toContain('font-size: 11px')
    expect(match![1]).toContain('color: var(--ink-3)')
  })

  it('.occ-quads is a 2-column grid with mixed gap', () => {
    const match = css.match(/\.occ-quads\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('display: grid')
    expect(match![1]).toContain('grid-template-columns: 1fr 1fr')
    expect(match![1]).toContain('gap: 12px 24px')
  })

  it('.occ-quad uses ink-2 13px with comfortable line-height', () => {
    const match = css.match(/\.occ-quad\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('font-size: 13px')
    expect(match![1]).toContain('line-height: 1.5')
    expect(match![1]).toContain('color: var(--ink-2)')
  })

  it('.occ-quad-label is the mono uppercase ink-3 sub-eyebrow', () => {
    const match = css.match(/\.occ-quad-label\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('font-family: var(--font-mono)')
    expect(match![1]).toContain('font-size: 10px')
    expect(match![1]).toContain('color: var(--ink-3)')
    expect(match![1]).toContain('text-transform: uppercase')
  })
})

describe('EntryDetail transcript disclosure contract (#26)', () => {
  it('.transcript-wrap is separated by a top rule with sp-5 padding', () => {
    const match = css.match(/\.transcript-wrap\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('border-top: 1px solid var(--border)')
    expect(match![1]).toContain('padding-top: var(--sp-5)')
    expect(match![1]).toContain('margin-top: var(--sp-7)')
  })

  it('.transcript-toggle is the mono uppercase reset-button trigger', () => {
    const match = css.match(/\.transcript-toggle\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('font-family: var(--font-mono)')
    expect(match![1]).toContain('font-size: 11px')
    expect(match![1]).toContain('color: var(--ink-2)')
    expect(match![1]).toContain('text-transform: uppercase')
    expect(match![1]).toContain('background: none')
    expect(match![1]).toContain('border: none')
  })

  it('.transcript-toggle .chev animates its transform', () => {
    const match = css.match(/\.transcript-toggle \.chev\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('transition: transform')
  })

  it('.transcript-toggle.is-open .chev rotates 90deg', () => {
    const match = css.match(/\.transcript-toggle\.is-open \.chev\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('transform: rotate(90deg)')
  })

  it('chevron rotation is disabled under prefers-reduced-motion', () => {
    expect(css).toMatch(/@media\s*\(prefers-reduced-motion:\s*reduce\)/)
    expect(css).toMatch(
      /\.transcript-toggle\s+\.chev\s*\{[^}]*transition:\s*none[^}]*\}/,
    )
  })
})

describe('EntryDetail transcript message contract (#26)', () => {
  it('.t-msg .who is mono uppercase ink-3 fixed 60px column', () => {
    const match = css.match(/\.t-msg \.who\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('font-family: var(--font-mono)')
    expect(match![1]).toContain('font-size: 10px')
    expect(match![1]).toContain('color: var(--ink-3)')
    expect(match![1]).toContain('text-transform: uppercase')
    expect(match![1]).toContain('width: 60px')
    expect(match![1]).toContain('padding-top: 4px')
  })

  it('.t-msg.kindred .who paints terracotta to mark assistant turns', () => {
    const match = css.match(/\.t-msg\.kindred \.who\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('color: var(--terracotta)')
  })

  it('.t-msg .text is body-size ink-2 with comfortable line-height', () => {
    const match = css.match(/\.t-msg \.text\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('font-size: 14.5px')
    expect(match![1]).toContain('color: var(--ink-2)')
    expect(match![1]).toContain('line-height: 1.55')
  })
})
