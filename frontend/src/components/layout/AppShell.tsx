import { Outlet } from '@tanstack/react-router'
import { TopBar } from './TopBar'
import { Sidebar } from './Sidebar'
import { BottomTabBar } from './BottomTabBar'

export function AppShell() {
  return (
    <div className="et-app-shell">
      <TopBar />
      <div className="et-layout">
        <Sidebar />
        <Outlet />
      </div>
      <BottomTabBar />
    </div>
  )
}
