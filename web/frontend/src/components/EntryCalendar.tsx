import { useState } from 'react'
import { type EntrySummary } from '../api/client'

/** Returns a local-time ISO date string "YYYY-MM-DD" without UTC shift. */
function toLocalISO(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const DOW = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']

interface Props {
  entries: EntrySummary[]
  selected: string | null
  onSelect: (date: string | null) => void
}

export function EntryCalendar({ entries, selected, onSelect }: Props) {
  const today = new Date()
  const todayStr = toLocalISO(today)

  const [view, setView] = useState<{ year: number; month: number }>(() => ({
    year: today.getFullYear(),
    month: today.getMonth(),
  }))

  // Set of dates that have entries, restricted to the viewed month
  const entryDates = new Set(entries.map((e) => e.date))

  // First day of month and how many days in month
  const firstOfMonth = new Date(view.year, view.month, 1)
  const daysInMonth = new Date(view.year, view.month + 1, 0).getDate()
  const startDow = firstOfMonth.getDay() // 0 = Sunday

  const monthName = firstOfMonth.toLocaleDateString('en-US', { month: 'long' })
  const yearStr = String(view.year)

  // Count entries in viewed month
  const monthPrefix = `${view.year}-${String(view.month + 1).padStart(2, '0')}`
  const countThisMonth = entries.filter((e) => e.date.startsWith(monthPrefix)).length

  function prevMonth() {
    setView(({ year, month }) => {
      if (month === 0) return { year: year - 1, month: 11 }
      return { year, month: month - 1 }
    })
  }

  function nextMonth() {
    setView(({ year, month }) => {
      if (month === 11) return { year: year + 1, month: 0 }
      return { year, month: month + 1 }
    })
  }

  function goToday() {
    setView({ year: today.getFullYear(), month: today.getMonth() })
    onSelect(todayStr)
  }

  function handleDayClick(dateStr: string) {
    if (selected === dateStr) {
      onSelect(null)
    } else {
      onSelect(dateStr)
    }
  }

  // Build cells: leading empty cells + day cells
  const cells: Array<{ type: 'empty'; key: string } | { type: 'day'; day: number; dateStr: string }> = []

  for (let i = 0; i < startDow; i++) {
    cells.push({ type: 'empty', key: `empty-${i}` })
  }
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${monthPrefix}-${String(d).padStart(2, '0')}`
    cells.push({ type: 'day', day: d, dateStr })
  }

  return (
    <div className="cal">
      <div className="cal-eye">
        <span className="glyph">◈</span> Calendar
      </div>

      <div className="cal-head">
        <div className="cal-title">
          <span className="cal-month">{monthName}</span>
          <span className="cal-year">{yearStr}</span>
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          <button className="cal-arrow" onClick={prevMonth} aria-label="Previous month">‹</button>
          <button className="cal-arrow" onClick={nextMonth} aria-label="Next month">›</button>
        </div>
      </div>

      <div className="cal-grid">
        {DOW.map((dow) => (
          <div key={dow} className="cal-dow">{dow}</div>
        ))}
        {cells.map((cell) => {
          if (cell.type === 'empty') {
            return <div key={cell.key} className="cal-cell is-empty" />
          }
          const { day, dateStr } = cell
          const hasEntry = entryDates.has(dateStr)
          const isToday = dateStr === todayStr
          const isSelected = dateStr === selected

          const classes = [
            'cal-cell',
            hasEntry ? 'has-entry' : '',
            isToday ? 'is-today' : '',
            isSelected ? 'is-selected' : '',
          ]
            .filter(Boolean)
            .join(' ')

          return (
            <button
              key={dateStr}
              className={classes}
              onClick={() => handleDayClick(dateStr)}
              aria-label={dateStr}
              aria-pressed={isSelected}
            >
              <span className="cal-num">{day}</span>
              {hasEntry && <span className="cal-mark" />}
            </button>
          )
        })}
      </div>

      <div className="cal-foot">
        <div className="cal-legend">
          <span className="lg">
            <span className="sw" />
            Entry
          </span>
          <span className="lg lg-today">
            <span className="sw" />
            Today
          </span>
        </div>
        <div className="cal-foot-meta">
          <span>{countThisMonth} this month</span>
          <span>
            <button className="cal-link" onClick={goToday}>Today</button>
            {selected !== null && (
              <button className="cal-link" onClick={() => onSelect(null)}>Clear</button>
            )}
          </span>
        </div>
      </div>
    </div>
  )
}
