import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Toggle } from '../Toggle'

describe('Toggle', () => {
  it('renders with class "toggle" (no "on") when checked={false}', () => {
    render(<Toggle checked={false} onChange={() => {}} label="Notify me" />)
    const label = screen.getByText('Notify me').closest('label')
    expect(label).toHaveClass('toggle')
    expect(label).not.toHaveClass('on')
  })

  it('renders with class "toggle on" when checked={true}', () => {
    render(<Toggle checked={true} onChange={() => {}} label="Notify me" />)
    const label = screen.getByText('Notify me').closest('label')
    expect(label).toHaveClass('toggle', 'on')
  })

  it('renders the label text inside .toggle-label', () => {
    render(<Toggle checked={false} onChange={() => {}} label="Save transcripts" />)
    const labelSpan = screen.getByText('Save transcripts')
    expect(labelSpan).toHaveClass('toggle-label')
  })

  it('calls onChange(true) when clicked while unchecked', () => {
    const onChange = vi.fn()
    render(<Toggle checked={false} onChange={onChange} label="Toggle me" />)
    fireEvent.click(screen.getByText('Toggle me').closest('label')!)
    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith(true)
  })

  it('calls onChange(false) when clicked while checked', () => {
    const onChange = vi.fn()
    render(<Toggle checked={true} onChange={onChange} label="Toggle me" />)
    fireEvent.click(screen.getByText('Toggle me').closest('label')!)
    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith(false)
  })
})
