# eigentakt — Mobile Calendar Layout Spec

## Breakpoint
Apply at `max-width: 768px`.

## Layout changes

**Grid**: reflow from `repeat(7, 1fr)` to a single column. Each day is a full-width row.

**Day header**: switch from centered column header to a horizontal inline label. Show day name and date on one line, left-aligned. Example: `Mon 19` with today highlighted in `--et-olive`.

**Sidebar**: hide. Replace with a bottom tab bar (4 items max: This week, Goals, Weekly template, Profile). 48px tall, bone background, `0.5px` top border. Icons centered, active state uses `--et-olive`.

**Top bar**: unchanged. Keep mark + wordmark + avatar. Drop the Sync button on narrow viewports if space is tight.

**Assessment banner**: stack the 4 signals vertically at `2 per row` using a 2-column grid, rather than the 4-column horizontal layout.

**Header week nav**: keep as-is. The Generate split button can collapse to icon-only (`wand` icon, no label) below 480px.

**Cards**: full width, same anatomy. No changes to card internals.

**Empty slot**: same dashed border, same "Add or Generate" affordance, min-height 56px.

**Rest slot**: same quiet label, min-height 36px.

**Drag-and-drop**: on mobile, use tap-hold (pointer events / touch events) instead of HTML5 drag API. Compatible/incompatible highlight states are the same. Drop target is the day row rather than a column.

## Scroll behavior
The grid area scrolls vertically. Top bar and bottom tab bar are fixed. Assessment banner scrolls with content.

## Reference files
- `eigentakt_calendar_reference.html` — all tokens, card states, and component markup
- `eigentakt_brand_system.md` — color tokens, typography, motion direction
- `eigentakt_calendar_v2.html` — current desktop implementation baseline
