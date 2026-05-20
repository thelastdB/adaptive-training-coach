import { Link } from '@tanstack/react-router'
import { Logo } from '../brand/Logo'
import { Icon } from '../ui/Icons'

export function TopBar() {
  return (
    <header className="et-topbar">
      <div className="et-topbar-logo">
        <Logo />
      </div>
      <div className="et-topbar-right">
        <button className="et-btn">
          <Icon name="refresh" size="sm" aria-hidden /> Sync
        </button>
        <Link to="/app/profile" style={{ lineHeight: 0 }}>
          <div className="et-avatar">RF</div>
        </Link>
      </div>
    </header>
  )
}
