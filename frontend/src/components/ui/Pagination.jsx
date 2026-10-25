import Button from "./Button";

// Page numbers are one-based here; the data owner keeps its original cursor.
export default function Pagination({
  page,
  totalPages,
  onPrevious,
  onNext,
  previousLabel = "Previous",
  nextLabel = "Next",
  label = "Pages",
  disabled = false,
  className = "",
}) {
  return (
    <nav className={`ui-pagination ${className}`} aria-label={label}>
      <Button
        variant="plain"
        size="sm"
        disabled={disabled || page <= 1}
        onClick={onPrevious}
      >
        {previousLabel}
      </Button>
      <span className="ui-pagination__position">
        Page {page}
        {totalPages != null && ` of ${totalPages}`}
      </span>
      <Button
        variant="plain"
        size="sm"
        disabled={disabled || (totalPages != null && page >= totalPages)}
        onClick={onNext}
      >
        {nextLabel}
      </Button>
    </nav>
  );
}
