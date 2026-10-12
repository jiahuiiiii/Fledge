export function modelAvailability(status, capability = "enabled") {
  if (!status)
    return {
      blocked: true,
      state: "unknown",
      message: "Checking whether AI analysis is available…",
    };
  if (!status[capability])
    return {
      blocked: true,
      state: "disabled",
      message:
        "AI analysis is switched off for this workspace. Saved research and source updates remain available.",
      detail: "AI is disabled or its connection has not been configured.",
    };
  if (status.budget?.needs_attention > 0)
    return {
      blocked: true,
      state: "attention",
      message:
        "New AI analysis is paused pending a spending review. Saved research and source updates remain available.",
      detail:
        "An earlier AI request ended without a confirmed charge. It needs review before another paid request; no automatic confirmation is running.",
    };
  if (status.budget?.running > 0)
    return {
      blocked: true,
      state: "running",
      message:
        "AI is analysing a request. New sentiment work can wait in the queue; saved research remains available.",
    };
  if (status.budget?.unresolved > 0)
    return {
      blocked: true,
      state: "attention",
      message:
        "New AI analysis is paused pending a spending review. Saved research and source updates remain available.",
      detail:
        "An earlier AI request needs review before another paid request. Saved research remains available.",
    };
  if (Number(status.budget?.remaining_usd) <= 0)
    return {
      blocked: true,
      state: "budget",
      message:
        "The AI spending allowance has been used. Saved research and source updates remain available.",
    };
  return { blocked: false, state: "ready", message: "" };
}
