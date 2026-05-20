import { createRouter, createRootRoute, createRoute, Outlet, redirect } from '@tanstack/react-router'
import { IconDefs } from './components/ui/Icons'
import { AppShell } from './components/layout/AppShell'
import { WeekView } from './components/week/WeekView'
import Landing from './pages/Landing'
import Onboarding from './pages/Onboarding'
import Goals from './pages/Goals'
import WeeklyTemplate from './pages/WeeklyTemplate'
import Profile from './pages/Profile'

const rootRoute = createRootRoute({
  component: () => (
    <>
      <IconDefs />
      <Outlet />
    </>
  ),
})

const landingRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: Landing,
})

const authCallbackRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/auth/callback',
  component: () => <div style={{ padding: 40, fontFamily: 'inherit' }}>Connecting…</div>,
})

const onboardingRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/onboarding',
  component: Onboarding,
})

const appRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/app',
  component: AppShell,
})

const appIndexRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/',
  beforeLoad: () => { throw redirect({ to: '/app/week' }) },
  component: () => null,
})

const appWeekRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/week',
  component: WeekView,
})

const appGoalsRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/goals',
  component: Goals,
})

const appScheduleRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/schedule',
  component: WeeklyTemplate,
})

const appProfileRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/profile',
  component: Profile,
})

const routeTree = rootRoute.addChildren([
  landingRoute,
  authCallbackRoute,
  onboardingRoute,
  appRoute.addChildren([
    appIndexRoute,
    appWeekRoute,
    appGoalsRoute,
    appScheduleRoute,
    appProfileRoute,
  ]),
])

export const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
