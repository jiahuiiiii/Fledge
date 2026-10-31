import { Responsive } from "react-grid-layout";
import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";
import {
  BREAKPOINTS,
  COLS,
  MARGIN,
  ROW_HEIGHT,
} from "../../lib/workspaceLayout";

// The draggable grid, in its own chunk so pages without widgets (and phones,
// which get the stacked list) never download react-grid-layout. Reading mode
// is static; only edit mode can move or resize. Heights follow content, so the
// only resize handle is the right edge (width).
export default function WidgetGrid({
  width,
  layouts,
  editing,
  onStop,
  children,
}) {
  return (
    <Responsive
      className={`ws-grid${editing ? " editing" : ""}`}
      width={width}
      layouts={layouts}
      breakpoints={BREAKPOINTS}
      cols={COLS}
      rowHeight={ROW_HEIGHT}
      margin={MARGIN}
      containerPadding={[0, 0]}
      compactType="vertical"
      isDraggable={editing}
      isResizable={editing}
      resizeHandles={["e"]}
      draggableHandle=".ws-bar"
      draggableCancel="button"
      onDragStop={onStop}
      onResizeStop={onStop}
    >
      {children}
    </Responsive>
  );
}
