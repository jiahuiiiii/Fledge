export default function FilingResolution({ value, showSource = true }) {
  if (!value) return null;
  const message =
    value.status === "retained"
      ? "These earlier figures still apply: checked against the later amendment."
      : value.status === "amended"
        ? "Figures from the amended report."
        : value.message;
  return (
    <section className="filing-resolution">
      <p>{message}</p>
      {showSource && value.source_url && (
        <a href={value.source_url} target="_blank" rel="noreferrer">
          Figure’s source report ↗
        </a>
      )}
      {value.amendments?.map((amendment, index) => (
        <a
          key={amendment.document_id}
          href={amendment.url}
          target="_blank"
          rel="noreferrer"
        >
          Read amendment{value.amendments.length > 1 ? ` ${index + 1}` : ""} ↗
        </a>
      ))}
    </section>
  );
}
