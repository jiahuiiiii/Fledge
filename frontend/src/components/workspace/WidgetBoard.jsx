import {
  Component,
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { api } from "../../api/client";
import { Button, GridIcon, PlusIcon, Skeleton } from "../ui";
import {
  COLS,
  STACK_BELOW,
  STACK_BOARD_BELOW,
  breakpointFor,
  fitHeights,
  moveItem,
  offered,
  ordered,
  reconcile,
  resizeItem,
  saveBody,
} from "../../lib/workspaceLayout";
import { WIDGETS } from "./widgets";
import { useWorkspace } from "./WorkspaceContext";
import { useProfile } from "../../lib/profile";
import "./workspace.css";

const WidgetGrid = lazy(() => import("./WidgetGrid"));

// The last saved arrangement per page, shared by every board of that page so
// switching companies does not read it again. Reads are deduplicated. It
// belongs to one account: signing in as another clears it (and a read still
// in flight from before is ignored), so one account's layout is never shown
// to, or saved over, another's.
const savedLayouts = new Map();
const reading = new Map();
let generation = 0;
export function forgetSavedLayouts() {
  generation += 1;
  savedLayouts.clear();
  reading.clear();
}
function readLayout(page) {
  if (savedLayouts.has(page)) return Promise.resolve(savedLayouts.get(page));
  if (!reading.has(page)) {
    const asked = generation;
    reading.set(
      page,
      api
        .layout(page)
        .then((result) => {
          if (asked !== generation) throw new Error("Account changed.");
          // A change made while this read was in flight is newer; keep it.
          if (!savedLayouts.has(page)) savedLayouts.set(page, result);
          return savedLayouts.get(page);
        })
        .finally(() => {
          if (asked === generation) reading.delete(page);
        }),
    );
  }
  return reading.get(page);
}

const pick = ({ i, x, y, w, h }) => ({ i, x, y, w, h });

function useNarrowWindow() {
  const query = `(max-width: ${STACK_BELOW - 1}px)`;
  const [narrow, setNarrow] = useState(() => matchMedia(query).matches);
  useEffect(() => {
    const list = matchMedia(query);
    const change = () => setNarrow(list.matches);
    list.addEventListener("change", change);
    return () => list.removeEventListener("change", change);
  }, [query]);
  return narrow;
}

class WidgetBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="ws-error" role="alert">
        <p>{this.props.title} couldn’t be shown.</p>
        <Button size="sm" onClick={() => this.setState({ failed: false })}>
          Try again
        </Button>
      </div>
    );
  }
}

function WidgetFrame({ widget, editing, canResize, onHeight, onTool }) {
  const ref = useRef(null);
  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return;
    const measure = () =>
      onHeight(widget.id, Math.ceil(element.getBoundingClientRect().height));
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [widget.id, onHeight]);
  const Widget = widget.component;
  const tool = (action, label, text) => (
    <button
      type="button"
      data-action={action}
      aria-label={`${label} ${widget.title}`}
      title={`${label} ${widget.title}`}
      onClick={() => onTool(widget.id, action)}
    >
      {text}
    </button>
  );
  return (
    <div
      ref={ref}
      className={`ws-frame${editing ? " editing" : ""}`}
      data-widget={widget.id}
      role={editing ? "group" : undefined}
      aria-label={editing ? widget.title : undefined}
    >
      {editing && (
        <div className="ws-bar">
          <span className="ws-grip" aria-hidden="true">
            ⠿
          </span>
          <strong>{widget.title}</strong>
          <span className="ws-tools">
            {tool("earlier", "Move earlier:", "↑")}
            {tool("later", "Move later:", "↓")}
            {canResize && tool("narrower", "Make narrower:", "−")}
            {canResize && tool("wider", "Make wider:", "+")}
            {tool("hide", "Hide", "Hide")}
          </span>
        </div>
      )}
      {/* While arranging, the content can't be clicked or focused, so a drag
          never opens a link and Tab goes through the arrange controls. */}
      <div className="ws-body" inert={editing ? "" : undefined}>
        <WidgetBoundary title={widget.title}>
          <Suspense
            fallback={<Skeleton label={`Loading ${widget.title}…`} rows={2} />}
          >
            <Widget />
          </Suspense>
        </WidgetBoundary>
      </div>
    </div>
  );
}

// An arrangeable page. Reading mode never moves anything; "Arrange" turns on
// dragging, width changes, keyboard moves, hiding and reset. The arrangement is
// saved per account and screen width, half a second after each change settles.
export default function WidgetBoard({ page }) {
  const spec = WIDGETS[page];
  const [state, setState] = useState(() =>
    reconcile(spec, savedLayouts.get(page) ?? null),
  );
  const [editing, setEditing] = useState(false);
  const [heights, setHeights] = useState({});
  const [width, setWidth] = useState(0);
  const [saveError, setSaveError] = useState(false);
  const [announcement, setAnnouncement] = useState("");
  const narrow = useNarrowWindow();
  const board = useRef(null);
  const refocus = useRef(null);
  const timer = useRef(null);
  const unsaved = useRef(null);
  const touched = useRef(false);
  const saving = useRef(Promise.resolve());

  useEffect(() => {
    let active = true;
    readLayout(page)
      .then((result) => {
        if (active && !touched.current) setState(reconcile(spec, result));
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [page, spec]);

  useLayoutEffect(() => {
    const element = board.current;
    if (!element) return;
    const measure = () =>
      setWidth(Math.round(element.getBoundingClientRect().width));
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const flush = useCallback(() => {
    clearTimeout(timer.current);
    const body = unsaved.current;
    unsaved.current = null;
    if (!body) return;
    // Saves go out one after another, so an older one never lands last.
    saving.current = saving.current
      .then(() => api.saveLayout(page, body))
      .then(
        (result) => {
          savedLayouts.set(page, result);
          setSaveError(false);
        },
        (failure) => setSaveError(failure?.message || true),
      );
  }, [page]);
  // Leaving the page within the half second still saves.
  useEffect(() => flush, [flush]);

  const commit = (next) => {
    touched.current = true;
    setState(next);
    const body = saveBody(next);
    savedLayouts.set(page, body);
    unsaved.current = body;
    clearTimeout(timer.current);
    timer.current = setTimeout(flush, 500);
  };

  const onHeight = useCallback(
    (id, px) =>
      setHeights((previous) =>
        previous[id] === px ? previous : { ...previous, [id]: px },
      ),
    [],
  );

  const stack = narrow || (width > 0 && width < STACK_BOARD_BELOW);
  const bp = stack ? "sm" : breakpointFor(width);
  // Pro-only widgets in Beginner, or ones that don't apply to this company
  // (practice companies have no real prices or filings), are left out
  // entirely: not shown and not offered. Their saved places are kept.
  const workspace = useWorkspace();
  const { mode } = useProfile();
  const available = offered(spec, mode, workspace);
  const absent = spec.filter((w) => !available.includes(w)).map((w) => w.id);
  const skipped = [...state.hidden, ...absent];
  const visible = available.filter((w) => !state.hidden.includes(w.id));
  const hiddenWidgets = available.filter((w) => state.hidden.includes(w.id));
  const byId = Object.fromEntries(spec.map((w) => [w.id, w]));

  const arranged = (layouts) => ({
    ...state,
    layouts,
    savedAt: [...new Set([...state.savedAt, bp])],
  });

  const onTool = (id, action) => {
    const title = byId[id].title;
    const layout = state.layouts[bp];
    if (action === "hide") {
      commit({
        ...arranged(state.layouts),
        hidden: [...state.hidden, id],
      });
      setAnnouncement(`${title} hidden. Add it back from the list above.`);
      requestAnimationFrame(() =>
        board.current?.querySelector(".ws-done")?.focus(),
      );
      return;
    }
    const next =
      action === "earlier" || action === "later"
        ? moveItem(layout, id, action === "earlier" ? -1 : 1, COLS[bp], skipped)
        : resizeItem(
            layout,
            id,
            action === "wider" ? 1 : -1,
            COLS[bp],
            byId[id].minW,
          );
    if (next === layout) return;
    commit(arranged({ ...state.layouts, [bp]: next }));
    refocus.current = [id, action];
    setAnnouncement(
      {
        earlier: `${title} moved earlier.`,
        later: `${title} moved later.`,
        wider: `${title} made wider.`,
        narrower: `${title} made narrower.`,
      }[action],
    );
  };
  // Keep focus on the control that was used, even if the widget moved.
  useEffect(() => {
    if (!refocus.current) return;
    const [id, action] = refocus.current;
    refocus.current = null;
    board.current
      ?.querySelector(`[data-widget="${id}"] [data-action="${action}"]`)
      ?.focus();
  });

  const show = (id) => {
    commit({
      ...arranged(state.layouts),
      hidden: state.hidden.filter((h) => h !== id),
    });
    setAnnouncement(`${byId[id].title} added back.`);
  };

  const reset = () => {
    clearTimeout(timer.current);
    unsaved.current = null;
    touched.current = true;
    setState(reconcile(spec, null));
    savedLayouts.set(page, null);
    // After any save already on its way, so the old layout can't come back.
    saving.current = saving.current
      .then(() => api.resetLayout(page))
      .then(
        (result) => {
          savedLayouts.set(page, result);
          setSaveError(false);
        },
        (failure) => setSaveError(failure?.message || true),
      );
    setAnnouncement("Back to the original arrangement.");
  };

  const onStop = (layout) => {
    const known = new Set(visible.map((w) => w.id));
    const moved = layout.filter((item) => known.has(item.i)).map(pick);
    // Hidden widgets keep their last place for when they are added back.
    const kept = state.layouts[bp].filter((item) => !known.has(item.i));
    commit(arranged({ ...state.layouts, [bp]: [...moved, ...kept] }));
  };

  const frame = (w) => (
    <WidgetFrame
      key={w.id}
      widget={w}
      editing={editing}
      canResize={!stack}
      onHeight={onHeight}
      onTool={onTool}
    />
  );
  const inOrder = (layout) =>
    ordered(layout)
      .map((item) => byId[item.i])
      .filter((w) => w && !skipped.includes(w.id));
  const stacked = (
    <div className="ws-stack">{inOrder(state.layouts.sm).map(frame)}</div>
  );
  const gridLayouts = Object.fromEntries(
    Object.entries(state.layouts).map(([key, layout]) => {
      const shown = layout
        .filter((item) => !skipped.includes(item.i))
        .map((item) => ({
          ...item,
          minW: Math.min(byId[item.i].minW, COLS[key]),
        }));
      return [key, key === bp ? fitHeights(shown, heights) : shown];
    }),
  );

  return (
    <div
      className={`ws-board${editing ? " editing" : ""}`}
      data-page={page}
      ref={board}
    >
      <div className="ws-toolbar">
        {editing ? (
          <>
            <p className="ws-hint">
              {stack
                ? "Use the arrows to change the order, or hide a section."
                : "Drag a section by its top bar, or drag its right edge to change its width. The buttons on each bar do the same from the keyboard."}
            </p>
            {hiddenWidgets.length > 0 && (
              <div
                className="ws-catalog"
                role="group"
                aria-label="Sections you can add"
              >
                <span className="ws-catalog-label">Add:</span>
                {hiddenWidgets.map((w) => (
                  <Button
                    key={w.id}
                    size="sm"
                    icon={<PlusIcon />}
                    onClick={() => show(w.id)}
                  >
                    {w.title}
                  </Button>
                ))}
              </div>
            )}
            <span className="ws-actions">
              <Button size="sm" variant="tertiary" onClick={reset}>
                Reset to default
              </Button>
              <Button
                size="sm"
                variant="primary"
                className="ws-done"
                onClick={() => {
                  flush();
                  setEditing(false);
                }}
              >
                Done
              </Button>
            </span>
          </>
        ) : (
          <Button
            size="sm"
            variant="plain"
            icon={<GridIcon />}
            className="ws-arrange"
            onClick={() => setEditing(true)}
          >
            Arrange
          </Button>
        )}
        {saveError && (
          <small className="ws-save-error" role="alert">
            Your arrangement couldn’t be saved
            {typeof saveError === "string"
              ? ` (${saveError.replace(/\.$/, "")})`
              : ""}
            , so it may reset when you reload.
          </small>
        )}
        <span className="sr-only" role="status">
          {announcement}
        </span>
      </div>
      {!visible.length ? (
        <p className="ws-empty">
          Every section is hidden. Choose Arrange to add some back.
        </p>
      ) : stack || !width ? (
        stacked
      ) : (
        <Suspense fallback={stacked}>
          <WidgetGrid
            width={width}
            layouts={gridLayouts}
            editing={editing}
            onStop={onStop}
          >
            {visible.map((w) => (
              <div key={w.id} className="ws-item">
                {frame(w)}
              </div>
            ))}
          </WidgetGrid>
        </Suspense>
      )}
    </div>
  );
}
