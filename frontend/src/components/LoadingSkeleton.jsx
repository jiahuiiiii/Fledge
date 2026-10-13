export default function LoadingSkeleton({
  label = "Loading saved research…",
  rows = 3,
  variant = "cards",
}) {
  return (
    <div className={`loading-skeleton skeleton-${variant}`} aria-busy="true">
      <p className="sr-only" role="status">
        {label}
      </p>
      <div aria-hidden="true">
        {variant === "workspace" && (
          <div className="skeleton-quote">
            <span className="skeleton-line short" />
            <span className="skeleton-line medium" />
            <span className="skeleton-line short" />
          </div>
        )}
        {variant === "financials" && (
          <>
            <span className="skeleton-line short skeleton-toggle" />
            <div className="skeleton-tiles">
              {[0, 1, 2].map((index) => (
                <div className="skeleton-tile" key={index}>
                  <span className="skeleton-line medium" />
                  <span className="skeleton-line short" />
                  <span className="skeleton-line medium" />
                </div>
              ))}
            </div>
          </>
        )}
        {["chart", "workspace", "financials"].includes(variant) && (
          <div className="skeleton-chart-frame">
            <div className="skeleton-chart-toolbar">
              <span className="skeleton-line short" />
              <span className="skeleton-line medium" />
            </div>
            <div className="skeleton-plot" />
            <span className="skeleton-line medium" />
          </div>
        )}
        {variant === "idea" && (
          <>
            <span className="skeleton-line short" />
            <span className="skeleton-line" />
            <span className="skeleton-line medium" />
          </>
        )}
        {variant !== "chart" &&
          Array.from(
            {
              length:
                variant === "idea" ? 2 : variant === "financials" ? 1 : rows,
            },
            (_, index) => (
              <div className="skeleton-card" key={index}>
                <span className="skeleton-line short" />
                <span className="skeleton-line" />
                <span className="skeleton-line medium" />
              </div>
            ),
          )}
      </div>
    </div>
  );
}
