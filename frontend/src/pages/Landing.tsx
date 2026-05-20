import { Link } from '@tanstack/react-router'
import heroImg from '../../../design-reference/Hero_Image.png'

const Mark = () => (
  <svg width="28" height="28" viewBox="0 0 256 256" fill="none" aria-hidden="true">
    <path d="M128 38L192 220H64L128 38Z" fill="#171715"/>
    <path d="M132 62L158 206H110L132 62Z" fill="#F3F1EB"/>
  </svg>
)

export default function Landing() {
  return (
    <div style={{ background: '#F3F1EB', minHeight: '100vh', color: '#171715' }}>
      <nav className="et-nav">
        <div className="et-logo">
          <Mark />
          <span className="et-wordmark">eigentakt</span>
        </div>
      </nav>

      <main>
        <section className="et-hero">
          <div className="et-hero-left">
            <p className="et-eyebrow">your rhythm</p>
            <h1 className="et-h1">Training<br />that fits<br />your life.</h1>
            <p className="et-body">
              eigentakt connects to your Strava data and builds a weekly training
              plan around your schedule, fitness, and goals — then adapts when
              things change.
            </p>
            <div>
              <Link to="/onboarding" className="et-cta">Connect with Strava →</Link>
            </div>
          </div>
          <div className="et-hero-right">
            <img
              className="et-hero-img"
              src={heroImg}
              alt="athlete lacing shoes on steps in early morning light"
            />
          </div>
        </section>

        <section className="et-features">
          <div className="et-feature">
            <p className="et-feature-title">Built around your goals</p>
            <p className="et-feature-body">
              Whether you're training for a specific event, building a base, or
              getting back into a rhythm — eigentakt plans toward what matters
              to you.
            </p>
          </div>
          <div className="et-feature">
            <p className="et-feature-title">Fits your week</p>
            <p className="et-feature-body">
              Tell it which days you have, for how long, and what's fixed. It
              accounts for weather, too — so your plan reflects the week you're
              actually facing.
            </p>
          </div>
          <div className="et-feature">
            <p className="et-feature-title">Built from your data</p>
            <p className="et-feature-body">
              eigentakt reads your Strava history — rides, runs, everything —
              and uses it to calibrate load, recovery, and progression to where
              you actually are.
            </p>
          </div>
        </section>

        <section className="et-how">
          <p className="et-section-label">How it works</p>
          <div className="et-steps">
            <div>
              <p className="et-step-num">01</p>
              <div className="et-step-divider" />
              <p className="et-step-title">Connect Strava</p>
              <p className="et-step-body">eigentakt reads your activity history — rides, runs, everything.</p>
            </div>
            <div>
              <p className="et-step-num">02</p>
              <div className="et-step-divider" />
              <p className="et-step-title">Set your week</p>
              <p className="et-step-body">Tell us which days you can train and for how long. Add any fixed commitments.</p>
            </div>
            <div>
              <p className="et-step-num">03</p>
              <div className="et-step-divider" />
              <p className="et-step-title">Get your plan</p>
              <p className="et-step-body">A structured weekly plan, specific to you. Move activities around, edit what doesn't work.</p>
            </div>
            <div>
              <p className="et-step-num">04</p>
              <div className="et-step-divider" />
              <p className="et-step-title">Evaluate and refine</p>
              <p className="et-step-body">Make changes and get instant feedback. Flags where something's off — weather, load, recovery.</p>
            </div>
          </div>
        </section>
      </main>

      <footer className="et-landing-footer">
        <p className="et-footer-copy">© 2026 eigentakt</p>
        <p className="et-footer-copy">eigentakt.app</p>
      </footer>
    </div>
  )
}
