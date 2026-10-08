const stamp = (value) =>
  value
    ? new Date(value).toLocaleString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "UTC",
      }) + " UTC"
    : "Date unavailable";

const relations = {
  supports: "May support your reasoning",
  challenges: "May challenge your reasoning",
  context: "Background context",
  unclear: "Connection unresolved",
};

// Only inspect the selected assessment's immutable source membership. A later
// correction in the workspace must never replace an earlier review's source.
export default function IdeaEvidenceReview({
  evaluation,
  previous,
  version,
  documents,
  change,
  onSource,
  review,
  onCompare,
  busy = false,
  error,
  unavailableReason,
  compact = false,
  onOpen,
  draft = false,
  showReasoning = true,
  savedComparison = false,
}) {
  const ids = [...new Set(evaluation.manifest.document_ids)];
  const allowed = new Set(ids);
  const before = new Set(previous?.manifest.document_ids || []);
  const catalogue = new Map(documents.map((d) => [d.id, d]));
  const superseded = new Set(
    ids.map((id) => catalogue.get(id)?.supersedes_id).filter(Boolean),
  );
  const active = evaluation.manifest.active_document_id;
  const currentIds = ids.filter((id) =>
    catalogue.get(id)?.kind === "sec-calculation" && active
      ? id === active
      : !superseded.has(id),
  );
  const changedIds = previous
    ? ids.filter((id) => !before.has(id))
    : currentIds;
  if (
    previous &&
    active &&
    allowed.has(active) &&
    active !== previous.manifest.active_document_id &&
    !changedIds.includes(active)
  ) {
    changedIds.push(active);
  }
  const selected = changedIds.sort((a, b) => {
    const left = catalogue.get(a),
      right = catalogue.get(b);
    return (right?.published_at || "").localeCompare(left?.published_at || "");
  });
  const initial = !previous;
  const heading = savedComparison
    ? "Evidence for this saved comparison"
    : draft
      ? "Evidence for your saved idea"
      : initial
        ? "Evidence for this assessment"
        : "What changed in the evidence";
  const emptyText =
    change?.kind === "reporting"
      ? "Review the reporting period you expected and the figures available at this assessment. A date transition does not fetch evidence or prove that the company filed late."
      : change?.kind === "expiry"
        ? "No new source was received. A saved reporting-age limit changed the numerical assessment."
        : change?.kind === "coverage"
          ? "No new source version was added. Source coverage changed; newer evidence may be missing."
          : "No new source version was added at this assessment.";

  function sourceCard(id) {
    const source = catalogue.get(id);
    const replaced = source?.supersedes_id;
    const hasEarlier = replaced && allowed.has(replaced);
    const label = hasEarlier
      ? "CORRECTED SOURCE"
      : previous && before.has(id)
        ? id === active && active !== previous.manifest.active_document_id
          ? "SOURCE SELECTED AGAIN"
          : "PREVIOUSLY AVAILABLE EVIDENCE"
        : savedComparison
          ? "SOURCE SUPPLIED TO THIS COMPARISON"
          : initial
            ? "AVAILABLE EVIDENCE"
            : "ADDED SINCE PREVIOUS ASSESSMENT";
    return (
      <article className="idea-evidence-source" key={id}>
        <span className="section-label">{label}</span>
        <h4>{source?.title || "Source unavailable"}</h4>
        {source ? (
          <>
            <p className="evidence-source-meta">
              {source.source} ·{" "}
              {source.kind === "news"
                ? "Provider headline / snippet"
                : source.kind === "recorded"
                  ? "Authored fictional source"
                  : "Filing calculation"}
            </p>
            <p className="evidence-source-meta">
              Published {stamp(source.published_at)}
              <br />
              Available in this workspace {stamp(source.available_at)}
            </p>
            <div className="evidence-source-actions">
              <button className="text-button" onClick={() => onSource(id)}>
                Inspect this source ↗
              </button>
              {hasEarlier && (
                <button
                  className="text-button"
                  onClick={() => onSource(replaced)}
                >
                  Compare earlier version ↗
                </button>
              )}
            </div>
          </>
        ) : (
          <p className="fine">
            The historical reference is retained, but its content cannot be
            opened here.
          </p>
        )}
      </article>
    );
  }

  if (compact)
    return (
      <section
        className="idea-evidence-compact"
        aria-label="Evidence review summary"
      >
        <span className="section-label">{heading}</span>
        <p>
          {selected.length
            ? `${selected.length} source version${selected.length === 1 ? "" : "s"} ${initial ? "available" : "added or selected"} at this assessment.`
            : emptyText}
        </p>
        {onOpen && (
          <button className="text-button" onClick={onOpen}>
            Compare evidence with my idea ↗
          </button>
        )}
      </section>
    );

  return (
    <section
      className="idea-evidence-review"
      aria-label="Evidence and saved reasoning"
    >
      <div className="evidence-review-heading">
        <span className="section-label">
          SOURCE-LINKED REVIEW · REVISION {version.revision}
        </span>
        <h3>{heading}</h3>
        <p className="fine">
          Evidence cutoff {stamp(evaluation.manifest.cutoff)}
          {savedComparison
            ? ` · Comparison saved ${stamp(review.created_at)}`
            : previous
              ? ` · Compared with ${stamp(previous.manifest.cutoff)}`
              : draft
                ? " · Current saved-source snapshot"
                : " · Initial assessment"}
        </p>
      </div>
      {showReasoning && (
        <div className="evidence-reasoning-anchor">
          <span className="section-label">
            {draft
              ? "YOUR SAVED REASONING"
              : "YOUR SAVED REASONING AT THIS ASSESSMENT"}
          </span>
          <p>
            {version.reasoning || "No reasoning was recorded in this revision."}
          </p>
        </div>
      )}
      {selected.length ? (
        <div className="idea-evidence-sources">
          {selected.slice(0, 3).map(sourceCard)}
          {selected.length > 3 && (
            <details className="evidence-more">
              <summary>
                {selected.length - 3} more source versions{" "}
                {savedComparison
                  ? "supplied to this comparison"
                  : initial
                    ? "available at this assessment"
                    : "in this change"}
              </summary>
              {selected.slice(3).map(sourceCard)}
            </details>
          )}
        </div>
      ) : (
        <p className="evidence-no-change">{emptyText}</p>
      )}
      {savedComparison && review.omitted_source_count > 0 && (
        <p className="fine">
          {review.omitted_source_count} other eligible source versions were not
          supplied to this comparison.
        </p>
      )}
      {!initial && (
        <details className="evidence-more">
          <summary>
            All current evidence at this assessment ({currentIds.length} source
            versions)
          </summary>
          {currentIds.map(sourceCard)}
        </details>
      )}
      <div className="reasoning-comparison">
        <h3>Does this affect your reasoning?</h3>
        <p className="fine">
          {savedComparison
            ? "This is the saved interpretation of the reasoning above and the listed sources at their original cutoff. Reopening it does not generate a new comparison."
            : draft
              ? "A draft needs no numerical condition. Compare the available evidence with what you believe before deciding what to monitor."
              : version.events?.length
                ? "The conditions below check your chosen figures and event criteria. An event interpretation is not independent verification or an investment verdict."
                : "The numerical checks below test only your chosen figures. They do not establish whether your written investment idea is supported."}
        </p>
        {review ? (
          <>
            <span className="section-label interpretation-label">
              AI INTERPRETATION · SAVED REVISION {version.revision}
            </span>
            <div className="reasoning-review-points">
              {(review.points || []).map((point, index) => (
                <article
                  className={`reasoning-review-point ${point.relation || "unclear"}`}
                  key={index}
                >
                  <strong>
                    {relations[point.relation] || "Connection unresolved"}
                  </strong>
                  {point.reasoning_quote && (
                    <blockquote>“{point.reasoning_quote}”</blockquote>
                  )}
                  <p>{point.text}</p>
                  <div className="evidence-source-actions">
                    {(point.citations || []).map((citation, i) => (
                      <button
                        key={i}
                        className="text-button"
                        disabled={
                          !allowed.has(citation.source_id) ||
                          !catalogue.has(citation.source_id)
                        }
                        title={citation.quote}
                        onClick={() => onSource(citation.source_id)}
                      >
                        {catalogue.get(citation.source_id)?.source || "Source"}{" "}
                        {i + 1} ↗
                      </button>
                    ))}
                  </div>
                </article>
              ))}
            </div>
            <p className="fine">
              {review.limitation ||
                "AI interpretation may miss context. Inspect the sources and make your own reassessment; your saved idea and numerical conditions are unchanged."}
            </p>
          </>
        ) : onCompare ? (
          <>
            <button
              className="secondary"
              disabled={
                busy || !!unavailableReason || !version.reasoning?.trim()
              }
              onClick={onCompare}
            >
              {busy
                ? "Comparing the saved idea…"
                : "Compare with my saved idea"}
            </button>
            <p className="fine">
              Optional AI interpretation of this saved reasoning and these exact
              sources. It does not edit your idea or change the numerical
              results.
            </p>
          </>
        ) : (
          <p className="fine">
            Inspect a source, compare it with the reasoning above, then mark
            reviewed or leave unresolved.
          </p>
        )}
        {unavailableReason && !review && (
          <p className="fine" role="status">
            {unavailableReason}
          </p>
        )}
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
      </div>
    </section>
  );
}
