import Badge from "./Badge";
import Button from "./Button";

// Single-choice filters are pressed buttons, not navigation tabs. Counts are
// optional: an unknown count stays absent. Labels remain readable at 320 px.
export default function FilterGroup({
  label,
  options,
  value,
  onValueChange,
  controls,
  className = "",
  itemClassName = "",
}) {
  return (
    <div
      className={`ui-filter-group ${className}`}
      role="group"
      aria-label={label}
    >
      {options.map((option) => (
        <Button
          key={option.value}
          variant="plain"
          size="sm"
          className={`${itemClassName} ${option.className || ""} ${value === option.value ? "active" : ""}`}
          aria-label={option.ariaLabel}
          title={option.title}
          aria-pressed={value === option.value}
          aria-controls={controls}
          disabled={option.disabled}
          icon={option.icon}
          onClick={() => onValueChange(option.value)}
        >
          {option.label}
          {option.count != null && <Badge>{option.count}</Badge>}
        </Button>
      ))}
    </div>
  );
}
