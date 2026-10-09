import { useRef, useState, useEffect } from "react";
import { api } from "../api/client";
import Modal from "./Modal";

const day = (value) =>
  new Date(value).toLocaleString("en-GB", {
    timeZone: "UTC",
    timeZoneName: "short",
  });

export default function OriginalFilings({
  instrumentId,
  data,
  busy,
  onRefresh,
}) {
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");
  const [passageLimit, setPassageLimit] = useState(200);
  const generation = useRef(0);
  useEffect(
    () => () => {
      generation.current++;
    },
    [instrumentId],
  );
  async function open(id) {
    const token = ++generation.current;
    setSelected({ loading: true });
    setPassageLimit(200);
    setError("");
    try {
      const result = await api.disclosure(instrumentId, id);
      if (token === generation.current) setSelected(result);
    } catch (failure) {
      if (token === generation.current) {
        setSelected(null);
        setError(failure.message);
      }
    }
  }
  function close() {
    generation.current++;
    setSelected(null);
  }
  return (
    <section
      className="financial-performance original-filings"
      aria-label="Original company filings"
    >
      <div className="financial-heading">
        <div>
          <span className="section-label">ORIGINAL COMPANY INFORMATION</span>
          <h3>Filings & earnings releases</h3>
        </div>
        <button disabled={busy} onClick={onRefresh}>
          Collect original documents
        </button>
      </div>
      <p>
        Business descriptions, risks, financial notes and filed earnings
        releases. Collection makes no AI request.
      </p>
      {data?.message && <p className="financial-coverage">{data.message}</p>}
      {error && <p role="alert">{error}</p>}
      {data?.source_status?.coverage
        ?.filter((item) => item.status !== "available")
        .map((item, i) => (
          <p className="financial-note" key={`${item.slot}-${i}`}>
            {item.slot.replaceAll("_", " ")}: {item.message}
          </p>
        ))}
      {data?.documents?.map((item) => (
        <div className="financial-filing" key={item.id}>
          <div>
            <strong>{item.headline}</strong>
            <p>
              SEC filing accepted {day(item.published_at)} ·{" "}
              {item.passage_count} text passages
            </p>
          </div>
          <button onClick={() => open(item.id)}>Read saved document</button>
        </div>
      ))}
      <Modal
        open={Boolean(selected)}
        onClose={close}
        title={selected?.headline || "Original company document"}
      >
        {selected?.loading ? (
          <p role="status">Loading saved text…</p>
        ) : (
          selected && (
            <>
              <p>
                SEC filing accepted {day(selected.published_at)} · first saved{" "}
                {day(selected.available_at)}
              </p>
              <a href={selected.url} target="_blank" rel="noreferrer">
                Open original SEC document ↗
              </a>
              {selected.data?.limitations?.map((line) => (
                <p className="financial-note" key={line}>
                  {line}
                </p>
              ))}
              <details>
                <summary>Detected sections</summary>
                {selected.data?.sections?.map((section) => (
                  <p key={section.title}>{section.title}</p>
                ))}
              </details>
              <div className="original-filing-text">
                {selected.data?.passages
                  ?.slice(0, passageLimit)
                  .map((passage) => (
                    <p key={passage.id}>{passage.quote}</p>
                  ))}
                {selected.data?.passages?.length > passageLimit && (
                  <button
                    onClick={() => setPassageLimit((limit) => limit + 200)}
                  >
                    Read next 200 passages
                  </button>
                )}
              </div>
            </>
          )
        )}
      </Modal>
    </section>
  );
}
