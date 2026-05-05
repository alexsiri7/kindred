import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const css = readFileSync(resolve(__dirname, '../index.css'), 'utf8')

const reducedMotionBlocks = (): string => {
  const matches = [
    ...css.matchAll(
      /@media\s*\(\s*prefers-reduced-motion:\s*reduce\s*\)\s*\{([\s\S]*?)\n\}/g,
    ),
  ]
  expect(matches.length).toBeGreaterThan(0)
  return matches.map((m) => m[1]).join('\n')
}

describe('Landing reduced-motion contract (#32)', () => {
  it('contains a prefers-reduced-motion: reduce media block', () => {
    expect(css).toMatch(/@media\s*\(\s*prefers-reduced-motion:\s*reduce\s*\)/)
  })

  it.each([
    ['.hero-orbit svg', /animation:\s*none/],
    ['.entry-peek-1, .entry-peek-2', /transform:\s*none/],
    ['.step', /transition:\s*none/],
    ['.step:hover', /transform:\s*none/],
    ['.msg, .tool-call', /animation-name:\s*msgInFade/],
  ])('strips animation for %s in reduced-motion', (selector, expected) => {
    const blocks = reducedMotionBlocks()
    expect(blocks).toContain(selector)
    expect(blocks).toMatch(expected)
  })
})

describe('EndCap star texture contract (#32)', () => {
  it('.endcap::before sets pointer-events: none so it does not eat CTA clicks', () => {
    const match = css.match(/\.endcap::before\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('pointer-events: none')
  })

  it('.endcap::before paints the star texture as a repeating background', () => {
    const match = css.match(/\.endcap::before\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toMatch(/background-image:\s*url\(['"]?\/texture-stars\.svg/)
    expect(match![1]).toMatch(/background-repeat:\s*repeat/)
  })
})
