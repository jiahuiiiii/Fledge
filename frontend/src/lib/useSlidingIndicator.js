import { useLayoutEffect, useState } from "react";

// Keeps two CSS variables (--indicator-x, --indicator-w) on `ref` in step with
// the active item, so a single underline can slide between items. Returns
// `ready` once the first position is set, so it appears in place on load
// instead of sliding in from the corner. Only transform/width animate.
export function useSlidingIndicator(ref, selector, dependency, inset = 0) {
  const [ready, setReady] = useState(false);
  useLayoutEffect(() => {
    const list = ref.current;
    if (!list) return undefined;
    const measure = () => {
      const active = list.querySelector(selector);
      list.style.setProperty("--indicator-x", `${active ? active.offsetLeft + inset : 0}px`);
      list.style.setProperty("--indicator-w", `${active ? Math.max(0, active.offsetWidth - inset * 2) : 0}px`);
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(list);
    const frame = requestAnimationFrame(() => setReady(true));
    return () => {
      observer.disconnect();
      cancelAnimationFrame(frame);
    };
  }, [ref, selector, dependency, inset]);
  return ready;
}
