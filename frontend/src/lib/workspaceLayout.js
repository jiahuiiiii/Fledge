// Pure layout helpers for the arrangeable overview and home pages. The widget
// registry (components/workspace/widgets.js) is the single source of default
// positions; these functions merge a saved layout with it and apply the
// keyboard moves. No React, so they are tested with node --test.

export const COLS = { lg: 12, md: 10, sm: 6 };
// Breakpoints are on the board's own width (sidebars change it), not the window.
export const BREAKPOINTS = { lg: 1100, md: 860, sm: 0 };
export const ROW_HEIGHT = 2;
export const MARGIN = [16, 16];
// Below this window width (phones, small tablets) widgets stack in one column.
export const STACK_BELOW = 768;
// A board narrower than this also stacks, even on a wide window.
export const STACK_BOARD_BELOW = 600;
// Kept in step with MAX_H / MAX_Y in thesis/workspace_layouts.py. Rows are
// ROW_HEIGHT + MARGIN[1] = 18 px, so 2,000 rows is about 36,000 px.
export const MAX_ROWS = 2000;
export const MAX_Y = 20000;

// Strictly wider than the breakpoint, as react-grid-layout decides it, so the
// board and the grid always agree on which layout is showing.
export const breakpointFor = (width) =>
  width > BREAKPOINTS.lg ? "lg" : width > BREAKPOINTS.md ? "md" : "sm";

const whole = (value, low, high) =>
  Number.isInteger(value) && value >= low && value <= high;

function valid(item, bp) {
  const cols = COLS[bp];
  return (
    item &&
    typeof item.i === "string" &&
    whole(item.w, 1, cols) &&
    whole(item.x, 0, cols - 1) &&
    item.x + item.w <= cols &&
    whole(item.y, 0, MAX_Y) &&
    whole(item.h, 1, MAX_ROWS)
  );
}

export const defaultLayout = (spec, bp) =>
  spec.map((w) => ({ i: w.id, ...w.default[bp] }));

// Merge what the server returned with the registry: unknown or broken items are
// dropped and widgets added since the save appear at their default width, below
// everything already placed (optional ones hidden). Never throws; a missing
// save gives the defaults.
export function reconcile(spec, saved) {
  const ids = new Set(spec.map((w) => w.id));
  const layouts = {};
  const savedAt = [];
  for (const bp of Object.keys(COLS)) {
    const stored = Array.isArray(saved?.[bp]) ? saved[bp] : null;
    if (!stored) {
      layouts[bp] = defaultLayout(spec, bp);
      continue;
    }
    savedAt.push(bp);
    const seen = new Set();
    const kept = stored.filter((item) => {
      if (!valid(item, bp) || !ids.has(item.i) || seen.has(item.i))
        return false;
      seen.add(item.i);
      return true;
    });
    let bottom = Math.max(0, ...kept.map((item) => item.y + item.h));
    for (const w of spec) {
      if (seen.has(w.id)) continue;
      const place = w.default[bp];
      kept.push({ i: w.id, ...place, y: bottom });
      bottom += place.h;
    }
    layouts[bp] = kept.map(({ i, x, y, w, h }) => ({ i, x, y, w, h }));
  }
  // Optional widgets start hidden (listed under "Sections you can add") until
  // the user adds one. A save made before an optional widget existed doesn't
  // mention it, so it stays hidden there too; once saved, the hidden list
  // records the choice either way.
  const mentioned = new Set(
    savedAt.flatMap((bp) => saved[bp].map((item) => item?.i)),
  );
  const hidden = [
    ...new Set([
      ...(saved?.hidden || []).filter((id) => ids.has(id)),
      ...spec
        .filter((w) => w.optional && !mentioned.has(w.id))
        .map((w) => w.id),
    ]),
  ];
  return { layouts, hidden, savedAt };
}

// Grid rows that hold a widget of this many pixels (rows plus the gaps between).
export const rowsFor = (px) =>
  Math.min(
    MAX_ROWS,
    Math.max(1, Math.ceil((px + MARGIN[1]) / (ROW_HEIGHT + MARGIN[1]))),
  );

// Heights follow content so nothing is cut off; only width is chosen by hand.
export const fitHeights = (layout, heights) =>
  layout.map((item) =>
    heights[item.i] > 0 ? { ...item, h: rowsFor(heights[item.i]) } : item,
  );

// Reading order: top to bottom, then left to right.
export const ordered = (layout) =>
  [...layout].sort((a, b) => a.y - b.y || a.x - b.x);

// Keyboard move: swap places with the previous (-1) or next (+1) widget in
// reading order. The grid then compacts, so the two trade positions.
export function moveItem(layout, id, direction, cols, skip = []) {
  const order = ordered(layout).filter((item) => !skip.includes(item.i));
  const index = order.findIndex((item) => item.i === id);
  const other = order[index + direction];
  if (index < 0 || !other) return layout;
  const mine = order[index];
  return layout.map((item) => {
    if (item.i === mine.i)
      return {
        ...item,
        x: Math.min(other.x, cols - item.w),
        y: other.y,
      };
    if (item.i === other.i)
      return {
        ...item,
        x: Math.min(mine.x, cols - item.w),
        y: mine.y,
      };
    return item;
  });
}

// Keyboard resize: change width by whole columns, staying on the page.
export function resizeItem(layout, id, delta, cols, minW = 1) {
  return layout.map((item) => {
    if (item.i !== id) return item;
    const w = Math.max(Math.min(minW, cols), Math.min(cols, item.w + delta));
    return { ...item, w, x: Math.min(item.x, cols - w) };
  });
}

// The body sent to PUT /layouts/{page}: only widths the user arranged.
export function saveBody(state) {
  const body = { hidden: state.hidden };
  for (const bp of state.savedAt) body[bp] = state.layouts[bp];
  return body;
}

// Widgets this page can offer right now: the right detail mode (Beginner
// "explain" / Pro "data") and, if the widget asks, the page's context.
export const offered = (spec, mode, context) =>
  spec.filter(
    (w) => (!w.modes || w.modes.includes(mode)) && (!w.when || w.when(context)),
  );
