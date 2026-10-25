import { createContext, useContext, useEffect, useRef, useState } from "react";
import "./ui.css";

const TabsContext = createContext(null);

export function Tabs({ value, defaultValue, onValueChange, children }) {
  const [localValue, setLocalValue] = useState(defaultValue);
  return (
    <TabsContext.Provider
      value={{
        value: value === undefined ? localValue : value,
        select: (next) => {
          setLocalValue(next);
          onValueChange?.(next);
        },
      }}
    >
      <div className="ui-tabs">{children}</div>
    </TabsContext.Provider>
  );
}

export function TabsList({
  variant = "line",
  className = "",
  children,
  ...rest
}) {
  return (
    <div
      {...rest}
      role="tablist"
      aria-orientation="horizontal"
      className={`ui-tabs-list ui-tabs-list--${variant} ${className}`}
    >
      {children}
    </div>
  );
}

export function TabsTrigger({
  value,
  children,
  className = "",
  disabled,
  ...rest
}) {
  const tabs = useContext(TabsContext);
  const ref = useRef(null);
  const selected = tabs.value === value;
  useEffect(() => {
    if (!selected || !ref.current) return;
    // Reveal only within the tab strip; switching should not scroll the page.
    const trigger = ref.current,
      list = trigger.parentElement;
    const reveal = () => {
      const button = trigger.getBoundingClientRect(),
        box = list.getBoundingClientRect();
      if (button.left < box.left) list.scrollLeft += button.left - box.left;
      else if (button.right > box.right)
        list.scrollLeft += button.right - box.right;
    };
    reveal();
    const observer = new ResizeObserver(reveal);
    observer.observe(list);
    return () => observer.disconnect();
  }, [selected]);
  return (
    <button
      {...rest}
      ref={ref}
      type="button"
      role="tab"
      disabled={disabled}
      aria-selected={selected}
      tabIndex={selected ? 0 : -1}
      className={`ui-tabs-trigger ${className}`}
      onClick={() => tabs.select(value)}
      onKeyDown={(event) => {
        if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key))
          return;
        event.preventDefault();
        const buttons = [
          ...event.currentTarget.parentElement.querySelectorAll(
            '[role="tab"]:not(:disabled)',
          ),
        ];
        const index = buttons.indexOf(event.currentTarget);
        const rtl = getComputedStyle(event.currentTarget).direction === "rtl";
        const forward = event.key === (rtl ? "ArrowLeft" : "ArrowRight");
        const next =
          event.key === "Home"
            ? 0
            : event.key === "End"
              ? buttons.length - 1
              : (index + (forward ? 1 : -1) + buttons.length) % buttons.length;
        buttons[next].focus({ preventScroll: true });
        buttons[next].click();
      }}
    >
      {children}
    </button>
  );
}
