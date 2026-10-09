import { SourceLabel } from "./SourceFilters";

export default function AllSourceSummary({ analysis, count }) {
  return (
    <div className="all-source-summary">
      <div className="sentiment-summary">
        <strong>All sources</strong>
        <span>{count} selected sources · newest first</span>
      </div>
      <div className="source-summary-list" aria-label="Tone by source">
        {["news", "reddit", "hackernews", "x"].map((scope) => {
          const sample =
            scope === "news"
              ? analysis.summary?.news
              : analysis.summary?.social_platforms?.[scope] ||
                (scope === "reddit" ? analysis.summary?.social : null);
          return (
            <div key={scope}>
              <SourceLabel scope={scope} />
              <strong>
                {sample?.selected ? sample.tone : "No selected texts"}
              </strong>
              {!!sample?.selected && (
                <span className="fine">
                  {sample.relevant} relevant of {sample.selected} selected
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
