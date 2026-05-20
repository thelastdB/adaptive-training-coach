# Session 2: React Scaffold + Brand

## Goal
Initialize the React frontend and build all brand/primitive components.

## Constraints
- Vite + React 18 + TypeScript
- No component libraries (no MUI, no Chakra, no shadcn)
- CSS custom properties only — no Tailwind, no CSS-in-JS
- All --et-* tokens must match eigentakt_calendar_reference.html exactly

## Tasks (do in order)
1. Init Vite project in /frontend
2. Install: @tanstack/react-query, @tanstack/react-router,
   zustand, @dnd-kit/core, @dnd-kit/sortable, axios
3. Extract all --et-* CSS variables from reference HTML into src/styles/tokens.css
4. Set up global reset + Google Fonts (Geist, Lora) in src/styles/global.css
5. Create src/lib/api.ts (Axios instance, JWT interceptor)
6. Create src/components/brand/Logo.tsx and Mark.tsx
   — SVG paths must match eigentakt_landing.html exactly
7. Create src/components/ui/Button.tsx, SplitButton.tsx, Dropdown.tsx
8. Confirm: vite dev starts, Logo renders at /

## Reference HTML files
All in /design-reference/:
- eigentakt_calendar_reference.html
- eigentakt_landing.html

The SVG source files are in /design-reference/. Read eigentakt_icon_light.png,
eigentakt_icon_dark.png, eigentakt_lockup_light.png, eigentakt_lockup_dark.png
before building Logo.tsx and Mark.tsx. Use these as the visual reference;
the locked SVG paths are in architecture.md.