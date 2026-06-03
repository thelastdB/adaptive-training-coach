import { useState } from 'react'
import { Icon } from '../components/ui/Icons'

type GoalType = 'event' | 'base' | 'return'

interface EventData {
  name: string
  date: string
  sport: string
  distance: string
}

const INITIAL_EVENT: EventData = {
  name: 'Flying Wheels Gran Fondo',
  date: '2026-05-31',
  sport: 'cycling',
  distance: '130 km',
}

const GOAL_LABELS: Record<GoalType, string> = {
  event: 'Target event',
  base: 'Build a base',
  return: 'Return to training',
}

export default function Goals() {
  const [currentGoal, setCurrentGoal] = useState<GoalType>('event')
  const [pendingGoal, setPendingGoal] = useState<GoalType | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [hasEvent, setHasEvent] = useState(true)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [unsaved, setUnsaved] = useState(false)
  const [eventDraft, setEventDraft] = useState<EventData>(INITIAL_EVENT)
  const [savedEvent, setSavedEvent] = useState<EventData>(INITIAL_EVENT)

  function selectGoal(g: GoalType) {
    if (g === currentGoal) return
    setPendingGoal(g)
  }

  function cancelGoalChange() {
    setPendingGoal(null)
  }

  function confirmGoalChange() {
    if (!pendingGoal) return
    setCurrentGoal(pendingGoal)
    setPendingGoal(null)
  }

  function startEdit() {
    setEventDraft(savedEvent)
    setIsEditing(true)
    setUnsaved(false)
    setShowDeleteConfirm(false)
  }

  function cancelEdit() {
    setIsEditing(false)
    setUnsaved(false)
  }

  function saveEdit() {
    setSavedEvent(eventDraft)
    setIsEditing(false)
    setUnsaved(false)
  }

  function executeDelete() {
    setHasEvent(false)
    setShowDeleteConfirm(false)
    setIsEditing(false)
  }

  function confirmAddEvent(e: EventData) {
    setSavedEvent(e)
    setEventDraft(e)
    setHasEvent(true)
  }

  const displayGoal = pendingGoal ?? currentGoal

  return (
    <main className="et-main">
      <div className="et-page-header">
        <span className="et-page-title">Goals</span>
      </div>

      <div className="et-content">

        {/* Primary goal */}
        <div className="et-section">
          <div className="et-section-header">
            <span className="et-section-label">Primary goal</span>
          </div>
          <div className="et-section-divider" />

          <div className="et-goal-grid">
            {(['event', 'base', 'return'] as GoalType[]).map(g => (
              <button
                key={g}
                className={`et-goal-card${displayGoal === g ? ' selected' : ''}`}
                onClick={() => selectGoal(g)}
              >
                <div className="et-goal-icon">
                  {g === 'event' && <Icon name="flag" size="lg" aria-hidden />}
                  {g === 'base' && <Icon name="trending-up" size="lg" aria-hidden />}
                  {g === 'return' && <Icon name="refresh" size="lg" aria-hidden />}
                </div>
                <p className="et-goal-title">{GOAL_LABELS[g]}</p>
                <p className="et-goal-desc">
                  {g === 'event' && 'A specific race, gran fondo, or event on a fixed date.'}
                  {g === 'base' && 'Structured aerobic development without a fixed deadline.'}
                  {g === 'return' && 'Getting back to consistent training after a break.'}
                </p>
              </button>
            ))}
          </div>

          {pendingGoal && (
            <div className="et-confirm-bar">
              <span className="et-confirm-text">
                Change goal to <strong>{GOAL_LABELS[pendingGoal]}</strong>? Your current event will be archived.
              </span>
              <div className="et-confirm-actions">
                <button className="et-btn et-btn-ghost" onClick={cancelGoalChange}>Cancel</button>
                <button className="et-btn et-btn-primary" onClick={confirmGoalChange}>
                  <Icon name="check" size="sm" aria-hidden /> Confirm
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Target event section */}
        {currentGoal === 'event' && hasEvent && (
          <div className="et-section">
            <div className="et-section-header">
              <span className="et-section-label">Target event</span>
            </div>
            <div className="et-section-divider" />

            <div className="et-event-block">
              <div className="et-event-block-header">
                <span className="et-event-block-title">
                  <Icon name="flag" size="sm" aria-hidden />
                  {savedEvent.name}
                  <span className="et-countdown-chip">12 days</span>
                </span>
                {!isEditing && (
                  <div className="et-event-block-actions">
                    <button className="et-btn et-btn-ghost" onClick={startEdit}>
                      <Icon name="edit" size="sm" aria-hidden /> Edit
                    </button>
                    <button className="et-btn et-btn-destructive" onClick={() => setShowDeleteConfirm(true)}>
                      <Icon name="trash" size="sm" aria-hidden />
                    </button>
                  </div>
                )}
              </div>

              {!isEditing ? (
                <div className="et-event-readonly">
                  <div className="et-readonly-field">
                    <span className="et-field-label">Event name</span>
                    <span className="et-readonly-value">{savedEvent.name}</span>
                  </div>
                  <div className="et-readonly-field">
                    <span className="et-field-label">Date</span>
                    <span className="et-readonly-value">May 31, 2026</span>
                    <span className="et-readonly-sub">12 days from today</span>
                  </div>
                  <div className="et-readonly-field">
                    <span className="et-field-label">Sport</span>
                    <span className="et-readonly-value">Cycling</span>
                  </div>
                  <div className="et-readonly-field">
                    <span className="et-field-label">Distance / duration</span>
                    <span className="et-readonly-value">{savedEvent.distance}</span>
                    <span className="et-readonly-sub">approx. 4.5 hr</span>
                  </div>
                </div>
              ) : (
                <>
                  <div className="et-event-form">
                    <div className="et-full">
                      <p className="et-field-label">Event name</p>
                      <input
                        className="et-input"
                        type="text"
                        value={eventDraft.name}
                        placeholder="e.g. Cascade Classic"
                        onChange={e => { setEventDraft(d => ({ ...d, name: e.target.value })); setUnsaved(true) }}
                      />
                    </div>
                    <div>
                      <p className="et-field-label">Date</p>
                      <input
                        className="et-input"
                        type="date"
                        value={eventDraft.date}
                        onChange={e => { setEventDraft(d => ({ ...d, date: e.target.value })); setUnsaved(true) }}
                      />
                    </div>
                    <div>
                      <p className="et-field-label">Sport</p>
                      <div className="et-select-wrap">
                        <select
                          className="et-select"
                          value={eventDraft.sport}
                          onChange={e => { setEventDraft(d => ({ ...d, sport: e.target.value })); setUnsaved(true) }}
                        >
                          <option value="cycling">Cycling</option>
                          <option value="running">Running</option>
                          <option value="triathlon">Triathlon</option>
                          <option value="gravel">Gravel</option>
                          <option value="mtb">Mountain bike</option>
                          <option value="other">Other</option>
                        </select>
                      </div>
                    </div>
                    <div className="et-full">
                      <p className="et-field-label">
                        Distance or duration{' '}
                        <span style={{ color: '#B0ACA6', fontWeight: 400, fontSize: 9, letterSpacing: 0, textTransform: 'none' }}>(optional)</span>
                      </p>
                      <input
                        className="et-input"
                        type="text"
                        value={eventDraft.distance}
                        placeholder="e.g. 130 km, 5 hrs"
                        onChange={e => { setEventDraft(d => ({ ...d, distance: e.target.value })); setUnsaved(true) }}
                      />
                    </div>
                  </div>
                  <div className="et-event-form-footer">
                    {unsaved
                      ? <span className="et-unsaved-note">Unsaved changes</span>
                      : <span />
                    }
                    <div style={{ display: 'flex', gap: 6, marginLeft: 'auto' }}>
                      <button className="et-btn et-btn-ghost" onClick={cancelEdit}>Cancel</button>
                      <button className="et-btn et-btn-primary" onClick={saveEdit}>
                        <Icon name="check" size="sm" aria-hidden /> Save changes
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>

            {showDeleteConfirm && (
              <div className="et-confirm-bar" style={{ background: 'var(--et-red-bg)', borderColor: 'var(--et-red-border)' }}>
                <span className="et-confirm-text">
                  Remove <strong>{savedEvent.name}</strong>? The event will be archived to past events.
                </span>
                <div className="et-confirm-actions">
                  <button className="et-btn et-btn-ghost" onClick={() => setShowDeleteConfirm(false)}>Cancel</button>
                  <button className="et-btn et-btn-destructive-solid" onClick={executeDelete}>
                    <Icon name="trash" size="sm" aria-hidden /> Remove
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Add event section */}
        {currentGoal === 'event' && !hasEvent && (
          <AddEventSection onAdd={confirmAddEvent} />
        )}

        {/* Past events */}
        <div className="et-section">
          <div className="et-section-header">
            <span className="et-section-label">Past events</span>
          </div>
          <div className="et-section-divider" />

          <div className="et-past-table">
            <div className="et-table-header">
              <span className="et-th">Event</span>
              <span className="et-th">Date</span>
              <span className="et-th">Sport</span>
              <span className="et-th">Outcome</span>
            </div>
            {[
              { name: 'Leavenworth Fondo', sub: '~110 km · 4.5 hr', date: 'Sep 14, 2025', sport: 'Cycling', outcome: 'completed' },
              { name: 'STP Day 1', sub: '~210 km · single day', date: 'Jul 12, 2025', sport: 'Cycling', outcome: 'completed' },
              { name: 'Chilly Hilly', sub: '~33 km', date: 'Feb 23, 2025', sport: 'Cycling', outcome: 'modified' },
              { name: 'Seattle Half Marathon', sub: '21.1 km', date: 'Nov 30, 2024', sport: 'Running', outcome: 'dns' },
            ].map(row => (
              <div className="et-table-row" key={row.name}>
                <div className="et-td">
                  {row.name}
                  <div className="et-td-sub">{row.sub}</div>
                </div>
                <div className="et-td et-td-stone">{row.date}</div>
                <div className="et-td et-td-stone">{row.sport}</div>
                <div className="et-td">
                  {row.outcome === 'completed' && (
                    <span className="et-outcome-badge et-outcome-completed">
                      <Icon name="check" size="xs" aria-hidden /> Completed
                    </span>
                  )}
                  {row.outcome === 'modified' && (
                    <span className="et-outcome-badge et-outcome-modified">Modified</span>
                  )}
                  {row.outcome === 'dns' && (
                    <span className="et-outcome-badge et-outcome-dns">DNS</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </main>
  )
}

function AddEventSection({ onAdd }: { onAdd: (e: EventData) => void }) {
  const [showForm, setShowForm] = useState(false)
  const [draft, setDraft] = useState<EventData>({ name: '', date: '', sport: '', distance: '' })

  return (
    <div className="et-section">
      <div className="et-section-header">
        <span className="et-section-label">Target event</span>
      </div>
      <div className="et-section-divider" />

      {!showForm ? (
        <div className="et-no-event">
          <span className="et-no-event-text">No target event set. eigentakt will plan for general progression.</span>
          <button className="et-btn" onClick={() => setShowForm(true)}>
            <Icon name="plus" size="sm" aria-hidden /> Add event
          </button>
        </div>
      ) : (
        <div className="et-event-block" style={{ marginTop: 10 }}>
          <div className="et-event-block-header">
            <span className="et-event-block-title">
              <Icon name="flag" size="sm" aria-hidden /> New target event
            </span>
            <div className="et-event-block-actions">
              <button className="et-btn et-btn-ghost" onClick={() => setShowForm(false)}>Cancel</button>
            </div>
          </div>
          <div className="et-event-form">
            <div className="et-full">
              <p className="et-field-label">Event name</p>
              <input className="et-input" type="text" placeholder="e.g. Cascade Classic"
                value={draft.name} onChange={e => setDraft(d => ({ ...d, name: e.target.value }))} />
            </div>
            <div>
              <p className="et-field-label">Date</p>
              <input className="et-input" type="date"
                value={draft.date} onChange={e => setDraft(d => ({ ...d, date: e.target.value }))} />
            </div>
            <div>
              <p className="et-field-label">Sport</p>
              <div className="et-select-wrap">
                <select className="et-select" value={draft.sport}
                  onChange={e => setDraft(d => ({ ...d, sport: e.target.value }))}>
                  <option value="">Select sport</option>
                  <option value="cycling">Cycling</option>
                  <option value="running">Running</option>
                  <option value="triathlon">Triathlon</option>
                  <option value="gravel">Gravel</option>
                  <option value="mtb">Mountain bike</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </div>
            <div className="et-full">
              <p className="et-field-label">Distance or duration <span style={{ color: '#B0ACA6', fontWeight: 400, fontSize: 9, letterSpacing: 0, textTransform: 'none' }}>(optional)</span></p>
              <input className="et-input" type="text" placeholder="e.g. 130 km, 5 hrs"
                value={draft.distance} onChange={e => setDraft(d => ({ ...d, distance: e.target.value }))} />
            </div>
          </div>
          <div className="et-event-form-footer">
            <span />
            <div style={{ display: 'flex', gap: 6 }}>
              <button className="et-btn et-btn-ghost" onClick={() => setShowForm(false)}>Cancel</button>
              <button className="et-btn et-btn-primary" onClick={() => onAdd(draft)}>
                <Icon name="check" size="sm" aria-hidden /> Add event
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
