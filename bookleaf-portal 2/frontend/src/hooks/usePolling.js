import { useEffect, useRef } from "react";

// Calls fn now and every `ms`, pausing while the tab is hidden. Near-real-time without WebSockets.
export function usePolling(fn, ms = 5000, deps = []) {
  const saved = useRef(fn);
  saved.current = fn;
  useEffect(() => {
    let stop = false;
    const tick = () => { if (!stop && !document.hidden) saved.current(); };
    tick();
    const id = setInterval(tick, ms);
    document.addEventListener("visibilitychange", tick);
    return () => { stop = true; clearInterval(id); document.removeEventListener("visibilitychange", tick); };
  }, [ms, ...deps]); // eslint-disable-line react-hooks/exhaustive-deps
}
