import { useEffect, useId, useRef, useState } from "react";
import "./ui.css";

// A search box with a floating list. The list is positioned over the page, so
// typing never resizes the box it sits in. options: { value, label, hint }.
export default function Combobox({
  label,
  options = [],
  onSelect,
  placeholder = "Search",
  emptyText = "No matches",
  disabled = false,
  filter = true,
  onQueryChange,
  className = "",
}) {
  const id = useId();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const root = useRef(null);
  const needle = query.trim().toLowerCase();
  // filter={false}: the caller already searched (for example on the server).
  const shown = options
    .filter(
      (o) =>
        !filter ||
        !needle ||
        `${o.label} ${o.hint || ""}`.toLowerCase().includes(needle),
    )
    .slice(0, 8);
  const listed = open && (filter || needle);
  useEffect(() => {
    const close = (e) => {
      if (!root.current?.contains(e.target)) setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);
  const choose = (option) => {
    if (!option) return;
    onSelect(option.value);
    setQuery("");
    setOpen(false);
  };
  return (
    <div className={`ui-combobox ${className}`} ref={root}>
      <input
        type="text"
        role="combobox"
        aria-label={label}
        aria-expanded={!!listed}
        aria-controls={`${id}-list`}
        aria-autocomplete="list"
        aria-activedescendant={
          listed && shown[active] ? `${id}-${active}` : undefined
        }
        autoComplete="off"
        disabled={disabled}
        placeholder={placeholder}
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          onQueryChange?.(e.target.value);
          setActive(0);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setOpen(true);
            setActive((a) => Math.min(a + 1, shown.length - 1));
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setActive((a) => Math.max(a - 1, 0));
          } else if (e.key === "Enter" && listed) {
            e.preventDefault();
            choose(shown[active]);
          } else if (e.key === "Escape") setOpen(false);
        }}
      />
      {listed && (
        <ul id={`${id}-list`} role="listbox" className="ui-combobox__list">
          {shown.length ? (
            shown.map((o, i) => (
              <li
                key={o.value}
                id={`${id}-${i}`}
                role="option"
                aria-selected={i === active}
                className={i === active ? "active" : ""}
                onPointerDown={(e) => {
                  e.preventDefault();
                  choose(o);
                }}
              >
                <span>{o.label}</span>
                {o.hint && <small>{o.hint}</small>}
              </li>
            ))
          ) : (
            <li
              className="empty"
              role="option"
              aria-disabled="true"
              aria-selected="false"
            >
              {emptyText}
            </li>
          )}
        </ul>
      )}
    </div>
  );
}
