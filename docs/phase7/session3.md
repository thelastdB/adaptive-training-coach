# Session 3: Calendar + Cards

## Goal
Build the core weekly view: grid, activity cards, drag-and-drop.

## Tasks (do in order)
1. ActivityCard.tsx — all three variants (default, fixed, stale)
2. EmptySlot.tsx, RestSlot.tsx
3. IntensityBadge.tsx
4. AssessmentBanner.tsx — 4 signals, desktop row / mobile 2×2
5. WeekGrid.tsx — 7-col CSS grid, @dnd-kit integration
6. DayColumn.tsx
7. WeekHeader.tsx + SplitButton integration
8. WeekView.tsx — composes all of the above
9. usePlan.ts hook (TanStack Query)
10. Wire WeekView to GET /plan/current — render real data

## Pixel reference
eigentakt_calendar_reference.html — match exactly.
Mobile behavior: eigentakt_mobile_spec.md.

## Drag-and-drop rules
- Cross-day drop: mark card stale, call PATCH /plan/{weekId}/activity/{day}
- Fixed card: cannot be dragged
- Invalid drop target: --et-amber highlight
- Valid drop target: --et-olive highlight