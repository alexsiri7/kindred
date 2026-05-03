import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const css = readFileSync(resolve(__dirname, '../index.css'), 'utf8')

const tokenValue = (name: string): string | null => {
  const match = css.match(new RegExp(`${name}\\s*:\\s*([^;]+);`))
  return match ? match[1].trim() : null
}

describe('design tokens (issue #21 contract)', () => {
  it.each([
    ['--terracotta', '#7C7AB5'],
    ['--terracotta-2', '#5F5D96'],
    ['--terracotta-3', '#DEDCEF'],
    ['--slate', '#4A3D5C'],
  ])('%s resolves to %s', (token, expected) => {
    expect(tokenValue(token)?.toUpperCase()).toBe(expected.toUpperCase())
  })

  it('--accent points at --terracotta (not a literal)', () => {
    expect(tokenValue('--accent')).toBe('var(--terracotta)')
  })

  it('--link points at --slate (not a literal)', () => {
    expect(tokenValue('--link')).toBe('var(--slate)')
  })

  it('declares exactly one :root block (cascade is single-sourced)', () => {
    const matches = css.match(/:root\s*\{/g) ?? []
    expect(matches.length).toBe(1)
  })

  it('contains no discarded terracotta literals', () => {
    const discarded = ['#D97757', '#C15D3D', '#F2C7B5', '#2B3A67', '#E8A33D', '#6B8E5A', '217,119,87']
    for (const literal of discarded) {
      expect(css).not.toContain(literal)
    }
  })

  it('every periwinkle hover-tint surface uses the same rgba tuple', () => {
    const periwinkleAlpha = css.match(/rgba\(124,\s*122,\s*181,\s*0\.04\)/g) ?? []
    expect(periwinkleAlpha.length).toBeGreaterThanOrEqual(4)
  })
})
