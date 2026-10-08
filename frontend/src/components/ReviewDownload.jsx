import { useState } from "react";

export default function ReviewDownload({
  version,
  evaluation,
  comparison,
  eventReview,
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function download() {
    setBusy(true);
    setError("");
    const params = new URLSearchParams();
    if (eventReview) params.set("event_review_id", eventReview.id);
    else if (comparison) params.set("comparison_id", comparison.id);
    else if (evaluation) params.set("evaluation_id", evaluation.id);
    try {
      const response = await fetch(
        `/api/v1/ideas/versions/${version.id}/review-export?${params}`,
        { credentials: "include" },
      );
      if (!response.ok) {
        let message =
          "The research record could not be downloaded. Your saved work is unchanged.";
        try {
          message =
            (await response.json())?.result?.errors?.[0]?.error_message ||
            message;
        } catch {
          /* Retain the fallback message. */
        }
        throw new Error(message);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download =
        response.headers
          .get("content-disposition")
          ?.match(/filename="([^"]+)"/)?.[1] || "thesis-research-record.html";
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="review-download">
      <button className="secondary" disabled={busy} onClick={download}>
        {busy ? "Preparing download…" : "Download research record"}
      </button>
      <p className="fine">
        {eventReview
          ? "This saved event evidence check"
          : comparison
            ? "This saved comparison"
            : evaluation
              ? "This monitoring assessment"
              : "This saved definition"}
        , your reasoning and its source references. Opens as a printable
        webpage. Includes private notes; review before sharing.
      </p>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
