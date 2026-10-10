import "./ReadingNotes.css";

export default function ReadingNotes({
  title = "About this reading",
  differentSources = false,
  stale = false,
  earlierMethod = false,
  omitted = 0,
  children,
  className = "",
}) {
  const status = [
    differentSources && "Different sources",
    stale && "Sources over a day old",
    earlierMethod && "Earlier analysis",
    omitted > 0 && `${omitted} ${omitted === 1 ? "topic" : "topics"} left out`,
  ].filter(Boolean);
  return (
    <details className={`reading-notes ${className}`}>
      <summary>
        <span className="reading-notes-label">
          {title}
          {!!status.length && <span> · {status.join(" · ")}</span>}
        </span>
      </summary>
      <div>
        {differentSources && (
          <p>
            This reading uses a different selection of sources from the current
            view.
          </p>
        )}
        {stale && (
          <p>
            These sources were collected more than a day ago. Later developments
            may be missing.
          </p>
        )}
        {earlierMethod && (
          <p>
            This reading was made before the latest improvements to the
            analysis. Its original findings are unchanged.
          </p>
        )}
        {omitted > 0 && (
          <p>
            {omitted} suggested {omitted === 1 ? "topic was" : "topics were"}{" "}
            left out because the evidence check could not support{" "}
            {omitted === 1 ? "it" : "them"}. The original sources are still
            available.
          </p>
        )}
        {children}
      </div>
    </details>
  );
}
