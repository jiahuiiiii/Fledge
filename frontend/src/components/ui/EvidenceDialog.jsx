import Modal from "../Modal";
import SourceChip from "./SourceChip";
import "./ui.css";

// One flat evidence dialog: a list of rows, no boxes inside boxes. A row is
// { id, label, value, meta, quote, href, sourceLabel, date, onOpen }. The
// footer slot holds the one or two actions that belong to the evidence.
export default function EvidenceDialog({
  open,
  onClose,
  title,
  rows = [],
  intro,
  footer,
  details,
  empty = "No saved evidence to show.",
}) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      className="evidence-dialog ui-evidence"
    >
      {intro && <p className="ui-evidence__intro">{intro}</p>}
      {rows.length ? (
        <ul className="ui-evidence__list">
          {rows.map((row, index) => (
            <li key={row.id ?? index} className="ui-evidence__row">
              {(row.label || row.value != null) && (
                <div className="ui-evidence__head">
                  <strong>{row.label}</strong>
                  {row.value != null && <span>{row.value}</span>}
                </div>
              )}
              {row.meta && (
                <small className="ui-evidence__meta">{row.meta}</small>
              )}
              {row.quote && <blockquote>{row.quote}</blockquote>}
              {row.note && (
                <small className="ui-evidence__meta">{row.note}</small>
              )}
              {(row.href || row.onOpen) && (
                <SourceChip
                  label={row.sourceLabel || "Open source"}
                  date={row.date}
                  href={row.href}
                  onOpen={row.onOpen}
                />
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="ui-evidence__intro">{empty}</p>
      )}
      {footer && <div className="ui-evidence__footer">{footer}</div>}
      {details?.length > 0 && (
        <details className="ui-evidence__details">
          <summary>Details</summary>
          <p>{details.join(" · ")}</p>
        </details>
      )}
    </Modal>
  );
}
