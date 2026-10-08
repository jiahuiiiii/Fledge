import {
  Children,
  isValidElement,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";
import "./Select.css";

const text = (node) =>
  Children.toArray(node)
    .map((part) =>
      isValidElement(part) ? text(part.props.children) : String(part),
    )
    .join("");
const optionsFrom = (children) =>
  Children.toArray(children).flatMap((child) => {
    if (!isValidElement(child)) return [];
    if (child.type === "option")
      return [
        {
          value: String(child.props.value ?? text(child.props.children)),
          label: text(child.props.children),
          disabled: !!child.props.disabled,
        },
      ];
    return optionsFrom(child.props.children);
  });

// Keep native select value/change/form semantics, but own the popup and keyboard
// interaction so macOS never substitutes its system menu for the app's options.
export default function Select({
  children,
  onChange,
  disabled,
  id,
  className = "",
  ...props
}) {
  const generated = useId(),
    listId = `${generated}-options`;
  const control = useRef(null),
    menu = useRef(null),
    search = useRef({ text: "", at: 0 });
  const [open, setOpen] = useState(false),
    [active, setActive] = useState(0),
    [position, setPosition] = useState(null);
  const options = optionsFrom(children);
  const selected = options.findIndex(
    (option) => option.value === String(props.value),
  );
  const enabled = options
    .map((option, index) => (option.disabled ? -1 : index))
    .filter((index) => index >= 0);
  const unavailable = disabled || !enabled.length;
  function close() {
    setOpen(false);
    search.current = { text: "", at: 0 };
  }
  function show() {
    if (unavailable) return;
    setActive(enabled.includes(selected) ? selected : enabled[0]);
    search.current = { text: "", at: 0 };
    setOpen(true);
  }
  function choose(index) {
    const option = options[index];
    if (!option || option.disabled || unavailable) return;
    // A real bubbling change retains form-level approval reset and native form values.
    const element = control.current;
    element.value = option.value;
    element.dispatchEvent(new Event("change", { bubbles: true }));
    close();
    element.focus({ preventScroll: true });
  }
  function positionMenu() {
    if (!control.current) return;
    const rect = control.current.getBoundingClientRect();
    const width = Math.min(Math.max(rect.width, 260), window.innerWidth - 24);
    const below = window.innerHeight - rect.bottom - 12,
      above = rect.top - 12;
    const flip =
      below < Math.min(options.length * 42 + 12, 280) && above > below;
    const maxHeight = Math.max(80, Math.min(320, flip ? above : below));
    setPosition({
      position: "fixed",
      left: Math.max(12, Math.min(rect.left, window.innerWidth - width - 12)),
      width,
      maxHeight,
      ...(flip
        ? { bottom: window.innerHeight - rect.top + 6 }
        : { top: rect.bottom + 6 }),
    });
  }
  useLayoutEffect(() => {
    if (open) positionMenu();
  }, [open, options.length]);
  useLayoutEffect(() => {
    if (!open || !position || !menu.current) return;
    const list = menu.current,
      option = list.querySelector(`[data-index="${active}"]`);
    if (!option) return;
    // Scroll only the option list, never the surrounding research pane.
    const top = option.offsetTop,
      bottom = top + option.offsetHeight;
    if (top < list.scrollTop) list.scrollTop = top;
    else if (bottom > list.scrollTop + list.clientHeight)
      list.scrollTop = bottom - list.clientHeight;
  }, [open, active, position]);
  useEffect(() => {
    if (unavailable) close();
  }, [unavailable]);
  useEffect(() => {
    if (!open) return;
    const outside = (event) => {
      if (
        !control.current?.contains(event.target) &&
        !menu.current?.contains(event.target)
      )
        close();
    };
    const scroll = (event) => {
      if (!menu.current?.contains(event.target)) positionMenu();
    };
    document.addEventListener("pointerdown", outside);
    window.addEventListener("resize", close);
    window.addEventListener("scroll", scroll, true);
    window.addEventListener("blur", close);
    return () => {
      document.removeEventListener("pointerdown", outside);
      window.removeEventListener("resize", close);
      window.removeEventListener("scroll", scroll, true);
      window.removeEventListener("blur", close);
    };
  }, [open]);
  function keyDown(event) {
    if (unavailable) return;
    const key = event.key;
    if (key === "Tab") {
      close();
      return;
    }
    if (key === "Escape" && open) {
      event.preventDefault();
      event.stopPropagation();
      close();
      return;
    }
    if (["ArrowDown", "ArrowUp", "Home", "End"].includes(key)) {
      event.preventDefault();
      if (!open) {
        show();
        if (key === "Home") setActive(enabled[0]);
        if (key === "End") setActive(enabled.at(-1));
        return;
      }
      const current = enabled.indexOf(active);
      setActive(
        key === "Home"
          ? enabled[0]
          : key === "End"
            ? enabled.at(-1)
            : enabled[
                (current + (key === "ArrowDown" ? 1 : -1) + enabled.length) %
                  enabled.length
              ],
      );
    } else if (key === "Enter" || key === " ") {
      event.preventDefault();
      if (open) choose(active);
      else show();
    } else if (
      key.length === 1 &&
      !event.metaKey &&
      !event.ctrlKey &&
      !event.altKey
    ) {
      event.preventDefault();
      const now = Date.now(),
        letter = key.toLocaleLowerCase();
      const query =
        now - search.current.at > 600 ? letter : search.current.text + letter;
      search.current = { text: query, at: now };
      const matchText = [...query].every((value) => value === letter)
        ? letter
        : query;
      const start = open ? active : selected;
      const ordered = [
        ...enabled.filter((index) => index > start),
        ...enabled.filter((index) => index <= start),
      ];
      const match = ordered.find((index) =>
        options[index].label.toLocaleLowerCase().startsWith(matchText),
      );
      if (match != null) {
        setActive(match);
        setOpen(true);
      }
    }
  }
  return (
    <span className={`custom-select ${className}`}>
      <select
        {...props}
        ref={control}
        id={id || generated}
        disabled={unavailable}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listId : undefined}
        aria-activedescendant={open ? `${listId}-${active}` : undefined}
        onPointerDown={(event) => {
          if (!unavailable) {
            event.preventDefault();
            control.current.focus({ preventScroll: true });
          }
        }}
        onMouseDown={(event) => event.preventDefault()}
        onClick={(event) => {
          event.preventDefault();
          if (open) close();
          else show();
        }}
        onKeyDown={keyDown}
        onBlur={(event) => {
          if (!menu.current?.contains(event.relatedTarget)) close();
        }}
        onChange={(event) => {
          onChange?.(event);
          close();
        }}
      >
        {children}
      </select>
      <svg
        className="select-chevron"
        viewBox="0 0 16 16"
        width="16"
        height="16"
        aria-hidden="true"
      >
        <path
          d="m4 6 4 4 4-4"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        />
      </svg>
      {open &&
        position &&
        createPortal(
          <div
            ref={menu}
            id={listId}
            role="listbox"
            aria-label={props["aria-label"] || "Options"}
            className="select-menu"
            style={position}
          >
            {options.map((option, index) => (
              <div
                key={`${option.value}:${index}`}
                id={`${listId}-${index}`}
                role="option"
                aria-selected={index === selected}
                aria-disabled={option.disabled || undefined}
                data-index={index}
                data-value={option.value}
                className={`select-option${index === active ? " active" : ""}`}
                onPointerMove={() => {
                  if (!option.disabled) setActive(index);
                }}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose(index)}
              >
                <span>{option.label}</span>
                <span aria-hidden="true">{index === selected ? "✓" : ""}</span>
              </div>
            ))}
          </div>,
          control.current?.closest("dialog") || document.body,
        )}
    </span>
  );
}
