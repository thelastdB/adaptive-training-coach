import { useState } from 'react'
import { Icon } from '../components/ui/Icons'

type Unit = 'metric' | 'imperial'

export default function Profile() {
  const [showDisconnect, setShowDisconnect] = useState(false)
  const [showDelete, setShowDelete] = useState(false)
  const [unit, setUnit] = useState<Unit>('metric')

  const zones = [
    { num: 1, label: 'Recovery',  bar: 40,  range: '100–114 bpm', cls: 'z1' },
    { num: 2, label: 'Endurance', bar: 55,  range: '115–133 bpm', cls: 'z2' },
    { num: 3, label: 'Tempo',     bar: 68,  range: '134–152 bpm', cls: 'z3' },
    { num: 4, label: 'Threshold', bar: 82,  range: '153–171 bpm', cls: 'z4' },
    { num: 5, label: 'VO₂ max',   bar: 100, range: '172+ bpm',    cls: 'z5' },
  ]

  return (
    <main className="et-main">
      <div className="et-page-header">
        <span className="et-page-title">Profile</span>
      </div>

      <div className="et-content">

        {/* Strava */}
        <div className="et-section" style={{ maxWidth: 560 }}>
          <div className="et-section-header">
            <span className="et-section-label">Strava</span>
          </div>
          <div className="et-section-divider" />

          <div className="et-connection-card">
            <div className="et-connection-body">
              <div className="et-connection-identity">
                <div className="et-strava-avatar">RF</div>
                <div>
                  <div className="et-connection-name">Ryan Finley</div>
                  <div className="et-connection-meta">
                    <span className="et-connection-badge">
                      <Icon name="circle-check" size="xs" aria-hidden /> Connected
                    </span>
                    <span>strava.com/athletes/ryan</span>
                  </div>
                </div>
              </div>
              {!showDisconnect && (
                <button className="et-btn et-btn-ghost" onClick={() => setShowDisconnect(true)}>
                  <Icon name="unlink" size="sm" aria-hidden /> Disconnect
                </button>
              )}
            </div>

            {showDisconnect && (
              <div className="et-disconnect-confirm">
                <span className="et-disconnect-confirm-text">
                  Disconnecting will pause activity sync. HR zones and planned workouts will not be affected.{' '}
                  <strong>Reconnect at any time.</strong>
                </span>
                <div className="et-confirm-actions">
                  <button className="et-btn et-btn-ghost" onClick={() => setShowDisconnect(false)}>Cancel</button>
                  <button className="et-btn et-btn-destructive-solid" onClick={() => setShowDisconnect(false)}>
                    <Icon name="unlink" size="sm" aria-hidden /> Disconnect
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Heart rate zones */}
        <div className="et-section" style={{ maxWidth: 560 }}>
          <div className="et-section-header">
            <span className="et-section-label">Heart rate zones</span>
          </div>
          <div className="et-section-divider" />

          <div className="et-zones-block">
            <div className="et-zones-note">
              <Icon name="refresh" size="sm" aria-hidden />
              Sourced from Strava. Updates automatically when Strava recalculates.
            </div>
            {zones.map(z => (
              <div className="et-zone-row" key={z.num}>
                <span className="et-zone-num">{z.num}</span>
                <span className="et-zone-label">{z.label}</span>
                <div className="et-zone-bar-wrap">
                  <div className={`et-zone-bar ${z.cls}`} style={{ width: `${z.bar}%` }} />
                </div>
                <span className="et-zone-range">{z.range}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Units */}
        <div className="et-section" style={{ maxWidth: 560 }}>
          <div className="et-section-header">
            <span className="et-section-label">Units</span>
          </div>
          <div className="et-section-divider" />

          <div className="et-units-row">
            <div>
              <div className="et-units-label">Distance and elevation</div>
              <div className="et-units-sub">Affects all distances, speed, and elevation display</div>
            </div>
            <div className="et-segmented" role="group" aria-label="Unit preference">
              <button
                className={`et-seg-btn${unit === 'metric' ? ' active' : ''}`}
                onClick={() => setUnit('metric')}
              >
                Metric
              </button>
              <button
                className={`et-seg-btn${unit === 'imperial' ? ' active' : ''}`}
                onClick={() => setUnit('imperial')}
              >
                Imperial
              </button>
            </div>
          </div>
        </div>

        {/* Account */}
        <div className="et-section" style={{ maxWidth: 560 }}>
          <div className="et-section-header">
            <span className="et-section-label">Account</span>
          </div>
          <div className="et-section-divider" />

          <div className="et-account-block">
            <div className="et-account-row">
              <div>
                <div className="et-account-row-label">Sign out</div>
                <div className="et-account-row-sub">finley.ryan@icloud.com</div>
              </div>
              <button className="et-btn">
                <Icon name="logout" size="sm" aria-hidden /> Sign out
              </button>
            </div>

            <div className="et-account-row danger">
              <div>
                <div className="et-account-row-label">Delete account</div>
                <div className="et-account-row-sub">Permanently removes all data. Cannot be undone.</div>
              </div>
              {!showDelete && (
                <button className="et-btn et-btn-destructive" onClick={() => setShowDelete(true)}>
                  <Icon name="trash" size="sm" aria-hidden /> Delete account
                </button>
              )}
            </div>

            {showDelete && (
              <div className="et-delete-confirm">
                <p className="et-delete-warning">
                  This will permanently delete your account, all training history, plans, and settings.{' '}
                  <strong>This cannot be undone.</strong> Your Strava data will not be affected.
                </p>
                <div className="et-delete-actions">
                  <button className="et-btn et-btn-ghost" onClick={() => setShowDelete(false)}>Cancel</button>
                  <button className="et-btn et-btn-destructive-solid">
                    <Icon name="trash" size="sm" aria-hidden /> Yes, delete my account
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

      </div>
    </main>
  )
}
