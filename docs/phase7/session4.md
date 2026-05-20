# Session 4: Shell + Settings Pages

## Tasks (do in order)
1. AppShell.tsx — TopBar, Sidebar (desktop), BottomTabBar (mobile)
2. TanStack Router setup — all routes wired
3. Goals.tsx — pixel match eigentakt_goals_settings.html
4. WeeklyTemplate.tsx — pixel match eigentakt_weekly_template.html
5. Profile.tsx — pixel match eigentakt_profile_settings.html
6. Onboarding.tsx — pixel match eigentakt_onboarding.html
   — runs after /auth/strava/callback if user has no goals set
7. Landing.tsx — port eigentakt_landing.html

## Shell behavior
- Sidebar: 48px, icon-only, tooltip on hover, active state --et-olive
- Mobile ≤768px: hide sidebar, show BottomTabBar
- TopBar: Logo + Sync button + Avatar (links to /app/profile)


Hero image: /design-reference/Hero_Image.png. Use this file directly --
reference it as a relative import in Landing.tsx. Apply filter: saturate(0.7)
per the design reference.