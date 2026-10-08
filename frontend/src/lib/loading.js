// Keep a visible cold-load placeholder readable instead of flashing for one frame.
// No delay on errors or already-rendered/background reads; no request retries.
export async function readableLoad(request, minimumMs = 280) {
  const started = performance.now();
  const value = await request;
  const remaining = minimumMs - (performance.now() - started);
  if (remaining > 0)
    await new Promise((resolve) => setTimeout(resolve, remaining));
  return value;
}
