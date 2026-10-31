import "./ui.css";

// A small chart with the latest figure beside it. points is an array of
// numbers or null; null breaks the line, never plots as zero. Click opens the
// evidence the caller supplies.
export default function TrendTile({
  title,
  value,
  caption,
  points = [],
  onOpen,
  tone = "info",
  className = "",
}) {
  const known = points.filter((p) => p != null && Number.isFinite(p));
  const w = 120,
    h = 44;
  let path = "";
  if (known.length > 1) {
    const lo = Math.min(...known),
      hi = Math.max(...known),
      span = hi - lo || 1;
    let pen = false;
    points.forEach((p, i) => {
      if (p == null || !Number.isFinite(p)) {
        pen = false;
        return;
      }
      const x = (i / (points.length - 1)) * w;
      const y = h - 4 - ((p - lo) / span) * (h - 8);
      path += `${pen ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`;
      pen = true;
    });
  }
  const Tag = onOpen ? "button" : "div";
  return (
    <Tag
      className={`ui-trend-tile ui-trend-tile--${tone} ${className}`}
      {...(onOpen ? { type: "button", onClick: onOpen } : {})}
    >
      <svg
        viewBox={`0 0 ${w} ${h}`}
        role="img"
        aria-label={`${title} trend`}
        preserveAspectRatio="none"
      >
        {path ? (
          <path
            d={path}
            fill="none"
            strokeWidth="2"
            vectorEffect="non-scaling-stroke"
          />
        ) : (
          <text x="0" y="26">
            No history
          </text>
        )}
      </svg>
      <span className="ui-trend-tile__text">
        <small>{title}</small>
        <strong>{value ?? "Not available"}</strong>
        {caption && <small>{caption}</small>}
      </span>
    </Tag>
  );
}
