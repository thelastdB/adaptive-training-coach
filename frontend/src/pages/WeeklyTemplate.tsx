import { useState, useCallback, useEffect } from 'react'
import { Icon } from '../components/ui/Icons'
import { useSchedule, useSaveSchedule } from '../hooks/useSchedule'
import type { WeeklySchedule } from '../types/schedule'

interface Commitment {
  id: string
  activity: string
  day: string
  time: string
  duration: string
}

interface DayState {
  [key: string]: number
}

const DAYS = [
  { key: 'mon', label: 'Mon', initial: 'M' },
  { key: 'tue', label: 'Tue', initial: 'T' },
  { key: 'wed', label: 'Wed', initial: 'W' },
  { key: 'thu', label: 'Thu', initial: 'T' },
  { key: 'fri', label: 'Fri', initial: 'F' },
  { key: 'sat', label: 'Sat', initial: 'S' },
  { key: 'sun', label: 'Sun', initial: 'S' },
]

const ACTIVITY_OPTIONS = ['Cycling', 'Run', 'Swim', 'Yoga', 'Strength', 'Other']
const DURATION_OPTIONS = [
  { value: '30', label: '30 min' },
  { value: '45', label: '45 min' },
  { value: '60', label: '1 hr' },
  { value: '90', label: '1.5 hr' },
  { value: '120', label: '2 hr' },
  { value: '150', label: '2.5 hr' },
  { value: '180', label: '3 hr' },
  { value: '240', label: '4 hr' },
]

function formatDur(mins: number): string {
  const h = Math.floor(mins / 60)
  const m = mins % 60
  if (h === 0) return `${m}m`
  if (m === 0) return `${h}h`
  return `${h}h${m}`
}

// Convert server WeeklySchedule → local state shapes
function serverToLocal(data: WeeklySchedule): { days: DayState; commitments: Commitment[] } {
  const days: DayState = {}
  for (const [key, val] of Object.entries(data.days)) {
    if (val.enabled) days[key] = val.duration_minutes
  }
  const commitments: Commitment[] = data.fixed_commitments.map((c, i) => ({
    id: `c${i}`,
    activity: c.label,
    day: c.day,
    time: c.time,
    duration: String(c.duration_minutes),
  }))
  return { days, commitments }
}

// Convert local state → server WeeklySchedule body
function localToServer(days: DayState, commitments: Commitment[]): WeeklySchedule {
  const serverDays: WeeklySchedule['days'] = {}
  for (const d of DAYS) {
    serverDays[d.key] = {
      enabled: days[d.key] !== undefined,
      duration_minutes: days[d.key] ?? 60,
    }
  }
  return {
    days: serverDays,
    fixed_commitments: commitments.map(c => ({
      label: c.activity,
      day: c.day,
      time: c.time,
      duration_minutes: Number(c.duration),
    })),
  }
}

let commitmentCounter = 100

export default function WeeklyTemplate() {
  const { data: serverData, isLoading } = useSchedule()
  const saveSchedule = useSaveSchedule()

  const [days, setDays] = useState<DayState>({})
  const [commitments, setCommitments] = useState<Commitment[]>([])
  const [dirty, setDirty] = useState(false)
  const [savedFlash, setSavedFlash] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  // Populate local state from server data on first load (and after save invalidation)
  useEffect(() => {
    if (serverData && !dirty) {
      const { days: d, commitments: c } = serverToLocal(serverData)
      setDays(d)
      setCommitments(c)
    }
  }, [serverData, dirty])

  function toggleDay(key: string) {
    setDays(prev => {
      const next = { ...prev }
      if (next[key] !== undefined) delete next[key]
      else next[key] = 60
      return next
    })
    setDirty(true)
  }

  function adjustDur(key: string, delta: number) {
    setDays(prev => {
      if (prev[key] === undefined) return prev
      return { ...prev, [key]: Math.max(15, Math.min(360, prev[key] + delta)) }
    })
    setDirty(true)
  }

  const activeDays = Object.keys(days)
  const totalMins = Object.values(days).reduce((a, b) => a + b, 0)
  const summaryText = (() => {
    if (activeDays.length === 0) return 'Select at least two days to set a training template.'
    if (activeDays.length === 1) return '1 day selected. Select at least one more.'
    const h = Math.floor(totalMins / 60), m = totalMins % 60
    const time = m > 0 ? `${h} hr ${m} min` : `${h} hr`
    return `${activeDays.length} days — ${time} of training time per week.`
  })()

  function addCommitment() {
    commitmentCounter++
    setCommitments(prev => [...prev, {
      id: `c${commitmentCounter}`,
      activity: 'Cycling',
      day: 'sat',
      time: '07:00',
      duration: '60',
    }])
    setDirty(true)
  }

  const updateCommitment = useCallback((id: string, field: keyof Commitment, value: string) => {
    setCommitments(prev => prev.map(c => c.id === id ? { ...c, [field]: value } : c))
    setDirty(true)
  }, [])

  function removeCommitment(id: string) {
    setCommitments(prev => prev.filter(c => c.id !== id))
    setDirty(true)
  }

  function discard() {
    if (serverData) {
      const { days: d, commitments: c } = serverToLocal(serverData)
      setDays(d)
      setCommitments(c)
    }
    setDirty(false)
    setSaveError(null)
  }

  function save() {
    setSaveError(null)
    saveSchedule.mutate(localToServer(days, commitments), {
      onSuccess: () => {
        setDirty(false)
        setSavedFlash(true)
        setTimeout(() => setSavedFlash(false), 1400)
      },
      onError: (err: unknown) => {
        const msg = err instanceof Error ? err.message : 'Save failed'
        setSaveError(msg)
      },
    })
  }

  if (isLoading) {
    return (
      <main className="et-main">
        <div className="et-page-header">
          <span className="et-page-title">Weekly Template</span>
        </div>
        <div className="et-content" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--et-stone)', fontSize: 13 }}>
          Loading…
        </div>
      </main>
    )
  }

  return (
    <main className="et-main" style={{ position: 'relative' }}>
      <div className="et-page-header">
        <span className="et-page-title">Weekly Template</span>
      </div>

      <div className="et-content" style={{ paddingBottom: 80 }}>

        {/* Template note */}
        <div className="et-template-note">
          <Icon name="info-circle" size="md" style={{ color: 'var(--et-stone)', flexShrink: 0, marginTop: 1 }} aria-hidden />
          <p className="et-template-note-text">
            This is your default week. eigentakt uses it as a starting point and adapts around schedule
            changes, fatigue, and proximity to your target event. Weeks with unusual constraints won't
            be forced to match it exactly.
          </p>
        </div>

        {/* Weekly availability */}
        <div className="et-section">
          <div className="et-section-header">
            <span className="et-section-label">Weekly availability</span>
          </div>
          <div className="et-section-divider" />

          <div className="et-day-grid">
            {DAYS.map(d => {
              const isActive = days[d.key] !== undefined
              const dur = days[d.key] ?? 60
              return (
                <div key={d.key} className={`et-tpl-day-col${isActive ? ' active' : ''}`}>
                  <button
                    className={`et-day-btn${isActive ? ' active' : ''}`}
                    onClick={() => toggleDay(d.key)}
                    aria-pressed={isActive}
                    aria-label={d.label}
                  >
                    <span className="et-day-initial">{d.initial}</span>
                    <span className="et-day-name-label">{d.label}</span>
                  </button>
                  <div className="et-day-dur">
                    <div className="et-dur-stepper">
                      <div className="et-dur-display">{formatDur(dur)}</div>
                      <div className="et-dur-unit">hr</div>
                      <div className="et-dur-btns">
                        <button className="et-dur-btn" onClick={() => adjustDur(d.key, -15)} aria-label="Decrease">−</button>
                        <button className="et-dur-btn" onClick={() => adjustDur(d.key, 15)} aria-label="Increase">+</button>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          <div className="et-week-summary">
            <p className="et-week-summary-text">
              {activeDays.length >= 2
                ? <><strong>{activeDays.length} days</strong> — {summaryText.split('— ')[1]}</>
                : summaryText
              }
            </p>
          </div>
        </div>

        {/* Fixed commitments */}
        <div className="et-section">
          <div className="et-section-header">
            <span className="et-section-label">Fixed commitments</span>
          </div>
          <div className="et-section-divider" />

          <div className="et-commitments-wrap">
            {commitments.length === 0 ? (
              <div className="et-commitments-empty">
                <span className="et-commitments-empty-text">
                  No fixed commitments. eigentakt has full flexibility each week.
                </span>
                <button className="et-btn" onClick={addCommitment}>
                  <Icon name="plus" size="sm" aria-hidden /> Add
                </button>
              </div>
            ) : (
              <>
                <div className="et-commitment-table">
                  <div className="et-commitment-thead">
                    <span className="et-th">Activity</span>
                    <span className="et-th">Day</span>
                    <span className="et-th">Time</span>
                    <span className="et-th">Duration</span>
                    <span className="et-th" />
                    <span />
                  </div>
                  {commitments.map(c => (
                    <CommitmentRow
                      key={c.id}
                      commitment={c}
                      onChange={updateCommitment}
                      onRemove={removeCommitment}
                    />
                  ))}
                </div>
                <button className="et-add-commitment" onClick={addCommitment}>
                  <Icon name="plus" size="sm" aria-hidden /> Add commitment
                </button>
              </>
            )}
          </div>

          {commitments.length > 0 && (
            <p className="et-commitment-note">
              Fixed commitments are locked in your plan each week. eigentakt plans around them rather than replacing them.
            </p>
          )}
        </div>
      </div>

      {/* Save bar */}
      <div className={`et-save-bar${dirty ? ' visible' : ''}`}>
        <span className="et-save-bar-text">
          {saveError
            ? <span style={{ color: 'var(--et-red)' }}>{saveError}</span>
            : <strong>Unsaved changes</strong>
          }
        </span>
        <div className="et-save-bar-actions">
          {savedFlash && (
            <span className="et-saved-flash visible">
              <Icon name="check" size="sm" style={{ color: '#8FCC6A' }} aria-hidden /> Saved
            </span>
          )}
          <button className="et-save-discard" onClick={discard}>Discard</button>
          <button
            className="et-save-btn"
            onClick={save}
            disabled={saveSchedule.isPending}
          >
            <Icon name="check" size="sm" aria-hidden />
            {saveSchedule.isPending ? 'Saving…' : 'Save template'}
          </button>
        </div>
      </div>
    </main>
  )
}

interface CommitmentRowProps {
  commitment: Commitment
  onChange: (id: string, field: keyof Commitment, value: string) => void
  onRemove: (id: string) => void
}

function CommitmentRow({ commitment: c, onChange, onRemove }: CommitmentRowProps) {
  return (
    <div className="et-commitment-row">
      <div className="et-inline-select-wrap">
        <select
          className="et-inline-select"
          value={c.activity}
          onChange={e => onChange(c.id, 'activity', e.target.value)}
        >
          {ACTIVITY_OPTIONS.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
      </div>
      <div className="et-inline-select-wrap">
        <select
          className="et-inline-select"
          value={c.day}
          onChange={e => onChange(c.id, 'day', e.target.value)}
        >
          {DAYS.map(d => <option key={d.key} value={d.key}>{d.label}</option>)}
        </select>
      </div>
      <input
        className="et-inline-input"
        type="time"
        value={c.time}
        onChange={e => onChange(c.id, 'time', e.target.value)}
      />
      <div className="et-inline-select-wrap">
        <select
          className="et-inline-select"
          value={c.duration}
          onChange={e => onChange(c.id, 'duration', e.target.value)}
        >
          {DURATION_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>
      <div className="et-lock-badge">
        <Icon name="lock" size="xs" aria-hidden /> Fixed
      </div>
      <button className="et-remove-btn" onClick={() => onRemove(c.id)} aria-label="Remove">
        <Icon name="x" size="sm" aria-hidden />
      </button>
    </div>
  )
}
