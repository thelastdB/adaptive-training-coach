import { useState, useRef } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { Icon } from '../components/ui/Icons'

type GoalType = 'event' | 'base' | 'return'

interface EventData {
  name: string
  date: string
  sport: string
  distance: string
}

interface Commitment {
  id: string
  day: string
  time: string
  duration: string
}

interface State {
  goal: GoalType | null
  event: EventData
  days: { [key: string]: number }
  commitments: Commitment[]
}

const DAYS = [
  { key: 'mon', label: 'Mon' },
  { key: 'tue', label: 'Tue' },
  { key: 'wed', label: 'Wed' },
  { key: 'thu', label: 'Thu' },
  { key: 'fri', label: 'Fri' },
  { key: 'sat', label: 'Sat' },
  { key: 'sun', label: 'Sun' },
]

// Logo mark for the dark panel
const PanelMark = () => (
  <svg width="14" height="20" viewBox="0 0 160 220" fill="none" aria-hidden="true">
    <polygon points="0,220 160,220 104,16 56,16" fill="#4A5C3E"/>
    <polygon points="56,16 104,16 98,0 62,0" fill="#3A4C2E"/>
    <polygon points="36,204 124,204 96,68 64,68" fill="#2C2C2A"/>
    <line x1="80" y1="202" x2="100" y2="76" stroke="#4A5C3E" strokeWidth="6" strokeLinecap="round"/>
    <rect x="94" y="86" width="13" height="13" rx="1" fill="#4A5C3E" transform="rotate(45 100.5 92.5)"/>
  </svg>
)

let commitmentCounter = 0

export default function Onboarding() {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(1)
  const [submitting, setSubmitting] = useState(false)
  const [state, setState] = useState<State>({
    goal: null,
    event: { name: '', date: '', sport: '', distance: '' },
    days: {},
    commitments: [],
  })
  const stepRefs = useRef<{ [key: number]: HTMLDivElement | null }>({})

  // Steps skips step 2 when goal !== event
  function getEffectiveSteps(): number[] {
    if (state.goal && state.goal !== 'event') return [1, 3, 4]
    return [1, 2, 3, 4]
  }

  function getNextStep(): number | null {
    const steps = getEffectiveSteps()
    const idx = steps.indexOf(currentStep)
    return idx < steps.length - 1 ? steps[idx + 1] : null
  }

  function getPrevStep(): number | null {
    const steps = getEffectiveSteps()
    const idx = steps.indexOf(currentStep)
    return idx > 0 ? steps[idx - 1] : null
  }

  function isStepValid(): boolean {
    if (currentStep === 1) return !!state.goal
    if (currentStep === 2) return true
    if (currentStep === 3) return Object.keys(state.days).length >= 2
    return true
  }

  function transition(toStep: number, direction: 'forward' | 'back') {
    const fromEl = stepRefs.current[currentStep]
    const toEl = stepRefs.current[toStep]
    if (!fromEl || !toEl) { setCurrentStep(toStep); return }

    fromEl.classList.remove('active')
    fromEl.classList.add(direction === 'forward' ? 'exit-left' : 'exit-right')
    toEl.classList.remove('enter-right', 'enter-left', 'exit-left', 'exit-right')
    toEl.classList.add(direction === 'forward' ? 'enter-right' : 'enter-left')

    // Force reflow
    void toEl.offsetHeight

    requestAnimationFrame(() => {
      toEl.classList.remove('enter-right', 'enter-left')
      toEl.classList.add('active')
    })

    setTimeout(() => {
      fromEl.classList.remove('exit-left', 'exit-right')
    }, 400)

    setCurrentStep(toStep)
  }

  function goNext() {
    if (!isStepValid()) return
    const next = getNextStep()
    if (next) {
      transition(next, 'forward')
    } else {
      setSubmitting(true)
      setTimeout(() => void navigate({ to: '/app/week' }), 2000)
    }
  }

  function goBack() {
    const prev = getPrevStep()
    if (prev) transition(prev, 'back')
  }

  function toggleDay(key: string) {
    setState(s => {
      const next = { ...s.days }
      if (next[key] !== undefined) delete next[key]
      else next[key] = 60
      return { ...s, days: next }
    })
  }

  function updateDuration(key: string, val: string) {
    setState(s => ({ ...s, days: { ...s.days, [key]: parseInt(val) || 60 } }))
  }

  function addCommitment() {
    commitmentCounter++
    setState(s => ({
      ...s,
      commitments: [...s.commitments, { id: `c${commitmentCounter}`, day: 'mon', time: '07:00', duration: '60' }],
    }))
  }

  function removeCommitment(id: string) {
    setState(s => ({ ...s, commitments: s.commitments.filter(c => c.id !== id) }))
  }

  function updateCommitment(id: string, field: keyof Commitment, value: string) {
    setState(s => ({
      ...s,
      commitments: s.commitments.map(c => c.id === id ? { ...c, [field]: value } : c),
    }))
  }

  const effectiveSteps = getEffectiveSteps()
  const stepIdx = effectiveSteps.indexOf(currentStep)
  const hasPrev = getPrevStep() !== null
  const isLast = getNextStep() === null

  const hintText = (() => {
    if (currentStep === 1 && !state.goal) return 'Select a goal to continue.'
    if (currentStep === 3 && Object.keys(state.days).length < 2) return 'Select at least two training days.'
    return ''
  })()

  const availNote = (() => {
    const count = Object.keys(state.days).length
    if (count === 0) return 'No days selected yet. Select at least two days to continue.'
    if (count === 1) return '1 day selected. Select at least one more.'
    const total = Object.values(state.days).reduce((a, b) => a + b, 0)
    const h = Math.floor(total / 60), m = total % 60
    const t = h > 0 ? (m > 0 ? `${h} hr ${m} min` : `${h} hr`) : `${m} min`
    return `${count} days selected — ${t} of training time per week.`
  })()

  const STEP_INFO = [
    { n: 1, label: 'Your goal',         sub: 'What are you training toward?' },
    { n: 2, label: 'Target event',       sub: 'Name, date, and type.' },
    { n: 3, label: 'Your week',          sub: 'Days and duration available.' },
    { n: 4, label: 'Fixed commitments',  sub: "Recurring times that can't move." },
  ]

  return (
    <div className="et-onboarding">

      {/* Left panel */}
      <aside className="et-panel">
        <div className="et-panel-logo">
          <PanelMark />
          <span className="et-panel-wordmark">eigentakt</span>
        </div>

        <div className="et-panel-strava">
          <div className="et-strava-dot" />
          <p className="et-strava-text">Connected as <span className="et-strava-name">Robin F.</span></p>
        </div>

        <nav className="et-panel-steps">
          {STEP_INFO.map(s => {
            const effIdx = effectiveSteps.indexOf(s.n)
            const isSkipped = effIdx === -1
            if (isSkipped) return null
            const isActive = s.n === currentStep
            const isComplete = effIdx < stepIdx
            return (
              <div
                key={s.n}
                className={`et-panel-step${isActive ? ' active' : ''}${isComplete ? ' complete' : ''}`}
              >
                <div className="et-step-node">{String(effIdx + 1).padStart(2, '0')}</div>
                <div className="et-step-meta">
                  <p className="et-step-label">{s.label}</p>
                  <p className="et-step-sublabel">{s.sub}</p>
                </div>
              </div>
            )
          })}
        </nav>

        <div className="et-panel-bottom">
          <p className="et-panel-tagline">
            eigentakt reads four weeks of Strava data to calibrate starting load. This takes about 30 seconds after setup.
          </p>
        </div>
      </aside>

      {/* Right content */}
      <div className="et-ob-content">

        {/* Top bar */}
        <div className="et-ob-topbar">
          <div className="et-progress-bar">
            {effectiveSteps.map((_, i) => (
              <div
                key={i}
                className={`et-progress-seg${i < stepIdx ? ' done' : ''}${i === stepIdx ? ' active' : ''}`}
              />
            ))}
          </div>
          <span className="et-ob-step-label">Step {stepIdx + 1} of {effectiveSteps.length}</span>
        </div>

        {/* Step viewport */}
        <div className="et-step-viewport">

          {/* Step 1: Goal */}
          <div
            className={`et-step${currentStep === 1 ? ' active' : ' enter-right'}`}
            ref={el => { stepRefs.current[1] = el }}
          >
            <p className="et-step-eyebrow">Your goal</p>
            <h1 className="et-step-title">What are you training toward?</h1>
            <p className="et-step-desc">eigentakt structures your plan around a clear purpose. This shapes load, pacing, and progression.</p>
            <div className="et-ob-goal-grid">
              {([
                { key: 'event' as GoalType, icon: 'flag', title: 'Target event', desc: 'A specific race, gran fondo, or event on a fixed date.' },
                { key: 'base' as GoalType, icon: 'trending-up', title: 'Build a base', desc: 'Structured aerobic development without a fixed deadline.' },
                { key: 'return' as GoalType, icon: 'refresh', title: 'Return to training', desc: 'Getting back to consistent training after a break.' },
              ]).map(g => (
                <button
                  key={g.key}
                  className={`et-ob-goal-card${state.goal === g.key ? ' selected' : ''}`}
                  onClick={() => setState(s => ({ ...s, goal: g.key }))}
                >
                  <div className="et-ob-goal-icon"><Icon name={g.icon} size="lg" aria-hidden /></div>
                  <p className="et-ob-goal-title">{g.title}</p>
                  <p className="et-ob-goal-desc">{g.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Step 2: Event */}
          <div
            className={`et-step${currentStep === 2 ? ' active' : ' enter-right'}`}
            ref={el => { stepRefs.current[2] = el }}
          >
            <p className="et-step-eyebrow">Target event</p>
            <h1 className="et-step-title">Tell us about the event.</h1>
            <p className="et-step-desc">This anchors your plan. eigentakt works backward from the date to calibrate build, peak, and taper phases.</p>
            <div className="et-field-group">
              <div className="et-ob-field">
                <label className="et-ob-label" htmlFor="ob-event-name">Event name</label>
                <input
                  className="et-ob-input"
                  id="ob-event-name"
                  type="text"
                  placeholder="e.g. Flying Wheels, Cascade Classic"
                  value={state.event.name}
                  onChange={e => setState(s => ({ ...s, event: { ...s.event, name: e.target.value } }))}
                />
              </div>
              <div className="et-field-row cols-2">
                <div className="et-ob-field">
                  <label className="et-ob-label" htmlFor="ob-event-date">Date</label>
                  <input
                    className="et-ob-input"
                    id="ob-event-date"
                    type="date"
                    value={state.event.date}
                    onChange={e => setState(s => ({ ...s, event: { ...s.event, date: e.target.value } }))}
                  />
                </div>
                <div className="et-ob-field">
                  <label className="et-ob-label" htmlFor="ob-event-sport">Sport</label>
                  <div className="et-ob-select-wrap">
                    <select
                      className="et-ob-select"
                      id="ob-event-sport"
                      value={state.event.sport}
                      onChange={e => setState(s => ({ ...s, event: { ...s.event, sport: e.target.value } }))}
                    >
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
              </div>
              <div className="et-ob-field">
                <label className="et-ob-label" htmlFor="ob-event-dist">
                  Approximate distance or duration{' '}
                  <span style={{ color: '#B0ACA6', fontWeight: 400 }}>(optional)</span>
                </label>
                <input
                  className="et-ob-input"
                  id="ob-event-dist"
                  type="text"
                  placeholder="e.g. 130 km, 5 hrs"
                  value={state.event.distance}
                  onChange={e => setState(s => ({ ...s, event: { ...s.event, distance: e.target.value } }))}
                />
              </div>
            </div>
          </div>

          {/* Step 3: Availability */}
          <div
            className={`et-step${currentStep === 3 ? ' active' : ' enter-right'}`}
            ref={el => { stepRefs.current[3] = el }}
          >
            <p className="et-step-eyebrow">Your week</p>
            <h1 className="et-step-title">When can you train?</h1>
            <p className="et-step-desc">Select the days you're typically available, then set how long you have. eigentakt will work within this every week.</p>
            <div className="et-ob-week-grid">
              {DAYS.map(d => {
                const isActive = state.days[d.key] !== undefined
                return (
                  <div key={d.key} className={`et-ob-day-toggle${isActive ? ' active' : ''}`}>
                    <button
                      className={`et-ob-day-btn${isActive ? ' active' : ''}`}
                      onClick={() => toggleDay(d.key)}
                      aria-label={d.label}
                      aria-pressed={isActive}
                    >
                      <span className="et-ob-day-initial">{d.label.charAt(0)}</span>
                      <span className="et-ob-day-label">{d.label}</span>
                    </button>
                    <div className="et-ob-day-dur-wrap">
                      <input
                        className="et-ob-duration-input"
                        type="number"
                        min={15}
                        max={360}
                        step={15}
                        value={state.days[d.key] ?? 60}
                        onChange={e => updateDuration(d.key, e.target.value)}
                        aria-label={`Duration for ${d.label}`}
                      />
                      <div className="et-ob-duration-unit">min</div>
                    </div>
                  </div>
                )
              })}
            </div>
            <p className="et-availability-note">{availNote}</p>
          </div>

          {/* Step 4: Commitments */}
          <div
            className={`et-step${currentStep === 4 ? ' active' : ' enter-right'}`}
            ref={el => { stepRefs.current[4] = el }}
          >
            <p className="et-step-eyebrow">Fixed commitments</p>
            <h1 className="et-step-title">What can't move?</h1>
            <p className="et-step-desc">Add any recurring sessions that are fixed — a club ride, coached swim, or weekly long run that eigentakt should plan around rather than replace.</p>

            {state.commitments.length === 0 ? (
              <div className="et-ob-commitment-empty">
                <p>No fixed commitments added. <em>If nothing is fixed, eigentakt has full flexibility.</em></p>
              </div>
            ) : (
              <div className="et-ob-commitment-list">
                <div className="et-ob-commitment-row" style={{ marginBottom: 4 }}>
                  <span className="et-ob-label">Day</span>
                  <span className="et-ob-label">Time</span>
                  <span className="et-ob-label">Duration</span>
                  <span />
                </div>
                {state.commitments.map(c => (
                  <div className="et-ob-commitment-row" key={c.id}>
                    <div className="et-ob-select-wrap">
                      <select
                        className="et-ob-select"
                        style={{ height: 32, fontSize: 12 }}
                        value={c.day}
                        onChange={e => updateCommitment(c.id, 'day', e.target.value)}
                      >
                        {DAYS.map(d => <option key={d.key} value={d.key}>{d.label}</option>)}
                      </select>
                    </div>
                    <input
                      className="et-ob-input"
                      style={{ height: 32, fontSize: 12 }}
                      type="time"
                      value={c.time}
                      onChange={e => updateCommitment(c.id, 'time', e.target.value)}
                    />
                    <div className="et-ob-select-wrap">
                      <select
                        className="et-ob-select"
                        style={{ height: 32, fontSize: 12 }}
                        value={c.duration}
                        onChange={e => updateCommitment(c.id, 'duration', e.target.value)}
                      >
                        <option value="30">30 min</option>
                        <option value="45">45 min</option>
                        <option value="60">1 hr</option>
                        <option value="90">1.5 hr</option>
                        <option value="120">2 hr</option>
                        <option value="180">3 hr</option>
                        <option value="240">4 hr</option>
                      </select>
                    </div>
                    <button className="et-remove-btn" onClick={() => removeCommitment(c.id)} aria-label="Remove">
                      <Icon name="x" size="sm" aria-hidden />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <button className="et-add-commitment" onClick={addCommitment} style={{ marginTop: 12 }}>
              <Icon name="plus" size="sm" aria-hidden /> Add commitment
            </button>
          </div>

        </div>

        {/* Footer */}
        <div className="et-ob-footer">
          <button className="et-footer-back" onClick={goBack} disabled={!hasPrev}>
            <Icon name="arrow-left" size="sm" aria-hidden /> Back
          </button>
          <div className="et-footer-right">
            {hintText && <span className="et-footer-hint">{hintText}</span>}
            <button
              className="et-btn-lg-primary"
              onClick={goNext}
              disabled={!isStepValid() || submitting}
            >
              {submitting
                ? 'Building your plan…'
                : isLast
                  ? <>Build my plan <Icon name="wand" size="md" aria-hidden /></>
                  : <>Continue <Icon name="arrow-right" size="sm" aria-hidden /></>
              }
            </button>
          </div>
        </div>

      </div>
    </div>
  )
}
