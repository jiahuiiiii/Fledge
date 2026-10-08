import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { stamp } from "./MarketResearch";

export default function SocialConversation({ sourceId, onRemoved }) {
  const mounted = useRef(false);
  const requestId = useRef(0);
  const [now, setNow] = useState(Date.now());
  const [data, setData] = useState(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    mounted.current = true;
    const currentRequest = ++requestId.current;
    let live = true;
    api
      .conversation(sourceId)
      .then((value) => {
        if (live && currentRequest === requestId.current) setData(value);
      })
      .catch((e) => {
        if (live && currentRequest === requestId.current) setError(e.message);
      });
    return () => {
      live = false;
      mounted.current = false;
    };
  }, [sourceId]);
  useEffect(() => {
    if (!data?.next_check_at) return;
    const delay = new Date(data.next_check_at).getTime() - Date.now();
    if (delay <= 0) return;
    const timer = setTimeout(() => setNow(Date.now()), delay + 20);
    return () => clearTimeout(timer);
  }, [data?.next_check_at]);
  async function collect() {
    ++requestId.current;
    setBusy(true);
    setError("");
    setData(null);
    try {
      const value = await api.conversation(sourceId, true);
      if (!mounted.current) return;
      if (value.source_removed) {
        onRemoved();
        return;
      }
      setData(value);
    } catch (e) {
      if (mounted.current) setError(e.message);
    } finally {
      if (mounted.current) setBusy(false);
    }
  }
  const result = data?.result;
  const cooling =
    data?.next_check_at && new Date(data.next_check_at).getTime() > now;
  return (
    <section
      className="conversation-context"
      aria-label="Original conversation context"
    >
      <h4>What is this replying to?</h4>
      <p className="fine">
        One parent message or story, using no AI credits. Loading it does not
        change a saved label. A new sentiment analysis can use recently checked
        parents and shows the exact context beside each label.
      </p>
      {data?.checking && (
        <p role="status">A source check was started and has not finished.</p>
      )}
      {data?.completion_missing && (
        <p className="warning" role="status">
          The previous source check did not record completion. Its result is
          unknown.
        </p>
      )}
      {error && (
        <p className="warning" role="alert">
          {error}
        </p>
      )}
      {result && (
        <>
          {result.outcome !== "available" && (
            <p className="warning" role="status">
              {result.explanation}
            </p>
          )}
          {result.outcome !== "available" && (
            <p className="fine">Checked {stamp(result.checked_at)}.</p>
          )}
          {result.outcome === "available" && (
            <>
              <strong>
                {result.parent_type === "story"
                  ? "Parent story headline"
                  : "Parent comment · separate message"}
              </strong>
              {result.parent_type === "story" && <p>{result.title}</p>}
              {result.body && <blockquote>{result.body}</blockquote>}
              <p className="fine">
                Published {stamp(result.published_at)} · checked{" "}
                {stamp(result.checked_at)}. Further replies and linked articles
                are not included.
              </p>
              <a
                className="source-link"
                href={result.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                Open parent discussion ↗
              </a>
            </>
          )}
        </>
      )}
      {data?.can_refresh !== false && (
        <button disabled={busy || data?.checking || cooling} onClick={collect}>
          {busy
            ? "Checking original discussion…"
            : result
              ? "Check original conversation again"
              : "Load original conversation"}
        </button>
      )}
      {data?.can_refresh === false && (
        <p className="fine">
          Collected with this discussion. Use Refresh research to check the
          thread again.
        </p>
      )}
      {cooling && data?.can_refresh !== false && (
        <p className="fine">
          Next source check available {stamp(data.next_check_at)}.
        </p>
      )}
    </section>
  );
}
