import { Link, useRouterState } from '@tanstack/react-router'
import { Icon } from '../ui/Icons'

export function BottomTabBar() {
  const { location } = useRouterState()
  const p = location.pathname

  function cls(to: string) {
    return `et-tab-item${p === to || p.startsWith(to + '/') ? ' active' : ''}`
  }

  return (
    <nav className="et-bottom-tab-bar">
      <Link to="/app/week" className={cls('/app/week')}>
        <Icon name="calendar-week" size="lg" aria-hidden />
        <span className="et-tab-label">Week</span>
      </Link>
      <Link to="/app/goals" className={cls('/app/goals')}>
        <Icon name="target" size="lg" aria-hidden />
        <span className="et-tab-label">Goals</span>
      </Link>
      <Link to="/app/schedule" className={cls('/app/schedule')}>
        <Icon name="clock" size="lg" aria-hidden />
        <span className="et-tab-label">Schedule</span>
      </Link>
      <Link to="/app/profile" className={cls('/app/profile')}>
        <Icon name="user" size="lg" aria-hidden />
        <span className="et-tab-label">Profile</span>
      </Link>
    </nav>
  )
}
