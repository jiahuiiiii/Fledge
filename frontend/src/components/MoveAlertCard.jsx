import { useEffect, useState } from "react";
import { api } from "../api/client";
import Select from "./Select";
import { day } from "../lib/financialStory";
import "./FinancialEvidence.css";
import { stamp } from "./MarketResearch";
import { causeName, movePercent } from "../lib/moveAlerts";
import "./MoveAlertCard.css";

function SectorChoice({ member }) {
  const [data, setData] = useState(null);
  const [choice, setChoice] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  useEffect(() => {
    let current = true;
    setData(null);
    setError("");
    api
      .priceReferences(member.instrument_id)
      .then((result) => {
        if (!current) return;
        setData(result);
        setChoice(result.sector.symbol || "");
      })
      .catch((e) => {
        if (current) setError(e.message);
      });
    return () => {
      current = false;
    };
  }, [member.instrument_id]);
  async function save() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await api.setPriceReference(member.instrument_id, choice || null);
      setNotice(
        "Sector comparison saved for future checks. This saved alert is unchanged.",
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="move-sector-choice">
      <div>
        {!data && !error && (
          <p role="status">Loading your sector comparison…</p>
        )}
        {error && <p role="alert">{error}</p>}
        {data && (
          <>
            <label>
              Sector comparison for {member.symbol}
              <Select
                value={choice}
                onChange={(e) => setChoice(e.target.value)}
                disabled={busy}
              >
                <option value="">No sector comparison</option>
                {data.choices.map((c) => (
                  <option key={c.symbol} value={c.symbol}>
                    {c.symbol} · {c.name}
                  </option>
                ))}
              </Select>
            </label>
            <button onClick={save} disabled={busy}>
              Save sector comparison
            </button>
            <p className="fine">
              Only your future comparisons use this choice.
            </p>
          </>
        )}
        {notice && <p role="status">{notice}</p>}
      </div>
    </div>
  );
}

function ComparisonSettings({ members }) {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState(members[0].instrument_id);
  const member =
    members.find((m) => m.instrument_id === selected) || members[0];
  return (
    <details
      className="move-comparison-settings"
      onToggle={(e) => setOpen(e.currentTarget.open)}
    >
      <summary>Sector comparison settings</summary>
      <p className="fine">Choose a sector fund for future price checks.</p>
      {open && members.length > 1 && (
        <label>
          Company
          <Select
            aria-label="Sector comparison company"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            {members.map((m) => (
              <option key={m.instrument_id} value={m.instrument_id}>
                {m.symbol}
              </option>
            ))}
          </Select>
        </label>
      )}
      {open && <SectorChoice key={member.instrument_id} member={member} />}
    </details>
  );
}

function PriceDetails({ members }) {
  return (
    <details className="move-price-details">
      <summary>Price details and alert rules</summary>
      <div className="move-price-register">
        {members.map((member) => (
          <section key={member.symbol}>
            <h4>
              {member.symbol} · {movePercent(member.change_percent)}
            </h4>
            <dl>
              <div>
                <dt>Saved price</dt>
                <dd>
                  US${member.price} · previous close US${member.previous_close}
                </dd>
              </div>
              {Object.entries(member.indexes).map(([symbol, ref]) => (
                <div key={symbol}>
                  <dt>{symbol === "QQQ" ? "Nasdaq (QQQ)" : "S&P 500 (SPY)"}</dt>
                  <dd>
                    {movePercent(ref.change_percent)} · gap{" "}
                    {movePercent(ref.gap_points, true)}
                  </dd>
                </div>
              ))}
              <div>
                <dt>Sector comparison</dt>
                <dd>
                  {member.sector
                    ? `${member.sector.symbol} ${movePercent(member.sector.change_percent)} · gap ${movePercent(member.sector.gap_points, true)}`
                    : "Not available for this check"}
                </dd>
              </div>
              <div>
                <dt>Over two sessions</dt>
                <dd>
                  {member.two_sessions
                    ? `${movePercent(member.two_sessions.change_percent)} · from ${day(member.two_sessions.from_session)}`
                    : "Not verified from saved daily prices"}
                </dd>
              </div>
              <div>
                <dt>Price quoted</dt>
                <dd>{stamp(member.quoted_at)}</dd>
              </div>
              <div>
                <dt>Why included</dt>
                <dd>
                  {member.context_only
                    ? "Market context only · did not cross an individual move threshold."
                    : member.reasons
                        .map(
                          (reason) =>
                            ({
                              session_move: `${member.thresholds.session}% session move`,
                              index_gap: `${member.thresholds.relative}-point Nasdaq gap`,
                              two_session_move: `${member.thresholds.two_sessions}% over two sessions`,
                            })[reason],
                        )
                        .join(" · ")}
                </dd>
              </div>
            </dl>
          </section>
        ))}
      </div>
    </details>
  );
}

function ExplanationEvidence({ alert }) {
  const explanation = alert.explanation;
  const sources = new Map(alert.sources.map((s) => [s.id, s]));
  return (
    <section
      className="financial-evidence-card move-explanation"
      aria-label="Explanation and supporting headlines"
    >
      <h4>{causeName[explanation?.cause] || "Why it moved"}</h4>
      {!explanation?.sentences?.length && (
        <p>
          {explanation?.text ||
            "No verified explanation is saved for this move."}
        </p>
      )}
      {(explanation?.sentences || []).map((sentence, i) => (
        <div key={i} className="move-evidence-point">
          <p>{sentence.text}</p>
          {sentence.citations.map((citation) => {
            const source = sources.get(citation.source_id);
            if (!source) return null;
            return (
              <figure key={`${citation.source_id}:${citation.quote}`}>
                <blockquote>{citation.quote}</blockquote>
                <figcaption>
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {source.title} ↗
                  </a>
                  <span>
                    {source.publisher} · {stamp(source.published_at)}
                  </span>
                </figcaption>
              </figure>
            );
          })}
        </div>
      ))}
      {explanation?.notice && <p className="fine">{explanation.notice}</p>}
      {alert.explanation_status === "unfinished" && (
        <p className="fine">
          The explanation is running or unconfirmed. It will not be retried
          automatically.
        </p>
      )}
      <p className="fine">
        Based on saved headlines and excerpts. Other causes may be missing.
      </p>
    </section>
  );
}

export default function MoveAlertCard({
  alert,
  busy = false,
  readOnly = false,
  onReview,
  onOpen,
}) {
  if (alert.withheld)
    return (
      <p className="warning">
        Source access changed. Price details and the explanation are withheld.
      </p>
    );
  const index = alert.members[0]?.indexes.QQQ;
  const context = alert.members
    .filter((m) => m.context_only)
    .map((m) => m.symbol);
  return (
    <section className="move-alert-card" aria-label="Price move evidence">
      <div className="move-evidence-header">
        {alert.preview && (
          <p className="fine">Preview · not sent to Telegram</p>
        )}
        {alert.session_date && (
          <p className="fine">US session {day(alert.session_date)}</p>
        )}
      </div>
      <table className="move-comparison" aria-label="Price move comparison">
        <caption>
          {index
            ? `Nasdaq (QQQ) ${movePercent(index.change_percent)} in this session`
            : "Nasdaq comparison unavailable for this check"}
          <span className="fine">
            A positive gap means a stronger move than Nasdaq; a negative gap
            means weaker.
          </span>
        </caption>
        <thead>
          <tr>
            <th scope="col">Company</th>
            <th scope="col">Move</th>
            <th scope="col">Gap vs Nasdaq</th>
          </tr>
        </thead>
        <tbody>
          {alert.members.map((member) => (
            <tr key={member.symbol}>
              <th scope="row">
                {onOpen ? (
                  <button
                    className="text-button"
                    onClick={() => onOpen(member.instrument_id, "workspace")}
                    aria-label={`Open ${member.symbol} research`}
                  >
                    {member.symbol}
                  </button>
                ) : (
                  member.symbol
                )}
                {member.context_only && (
                  <span className="move-context-label">Context only</span>
                )}
              </th>
              <td>{movePercent(member.change_percent)}</td>
              <td>
                {member.indexes.QQQ
                  ? movePercent(member.indexes.QQQ.gap_points, true)
                  : "Unknown"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {context.length > 0 && (
        <p className="fine">
          {context.join(", ")} are included for comparison; their individual
          moves did not cross an alert threshold.
        </p>
      )}
      <ExplanationEvidence alert={alert} />
      <PriceDetails members={alert.members} />
      {!readOnly && <ComparisonSettings members={alert.members} />}
      {!readOnly && !alert.review_action && (
        <div className="move-review-controls">
          <button
            disabled={busy}
            onClick={() => onReview(alert.id, "reviewed")}
          >
            Mark reviewed
          </button>
          <button
            disabled={busy}
            onClick={() => onReview(alert.id, "unresolved")}
          >
            Leave unresolved
          </button>
        </div>
      )}
    </section>
  );
}
