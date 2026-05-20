import { Link, useRouterState } from '@tanstack/react-router'
import { Icon } from '../ui/Icons'

export function Sidebar() {
  const { location } = useRouterState()
  const p = location.pathname

  function cls(to: string) {
    return `et-sidebar-icon${p === to || p.startsWith(to + '/') ? ' active' : ''}`
  }

  return (
    <aside className="et-sidebar">
      <div className="et-sidebar-item">
        <Link to="/app/week" className={cls('/app/week')} aria-label="This week">
          <Icon name="calendar-week" size="lg" aria-hidden />
        </Link>
        <span className="et-sidebar-tooltip">This week</span>
      </div>

      <div className="et-sidebar-item">
        <button className="et-sidebar-icon" aria-label="Plan history">
          <Icon name="history" size="lg" aria-hidden />
        </button>
        <span className="et-sidebar-tooltip">Plan history</span>
      </div>

      <div className="et-sidebar-divider" />

      <div className="et-sidebar-item">
        <Link to="/app/goals" className={cls('/app/goals')} aria-label="Goals">
          <Icon name="target" size="lg" aria-hidden />
        </Link>
        <span className="et-sidebar-tooltip">Goals</span>
      </div>

      <div className="et-sidebar-item">
        <Link to="/app/schedule" className={cls('/app/schedule')} aria-label="Weekly template">
          <Icon name="clock" size="lg" aria-hidden />
        </Link>
        <span className="et-sidebar-tooltip">Weekly template</span>
      </div>

      <div className="et-sidebar-item">
        <Link to="/app/profile" className={cls('/app/profile')} aria-label="Profile">
          <Icon name="user" size="lg" aria-hidden />
        </Link>
        <span className="et-sidebar-tooltip">Profile</span>
      </div>

      <div className="et-sidebar-bottom">
        <div className="et-sidebar-divider" />
        <div className="et-sidebar-item">
          <Link to="/app/goals" className="et-sidebar-icon" aria-label="Upcoming events" style={{ position: 'relative' }}>
            <Icon name="flag" size="lg" aria-hidden />
            <span className="et-event-dot" />
          </Link>
          <span className="et-sidebar-tooltip">Flying Wheels · 12 days</span>
        </div>
      </div>
    </aside>
  )
}
