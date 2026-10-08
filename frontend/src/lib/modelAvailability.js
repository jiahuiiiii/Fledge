export function modelAvailability(status, capability = "enabled") {
  if (!status)
    return {
      blocked: true,
      state: "unknown",
      message: "Checking the AI connection…",
    };
  if (!status[capability])
    return {
      blocked: true,
      state: "disabled",
      message:
        "AI is switched off or its API key is not configured. Source loading still works.",
    };
  if (status.budget?.needs_attention > 0)
    return {
      blocked: true,
      state: "attention",
      message:
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
        "An earlier AI request needs review before another paid request. Saved research remains available.",
    };
  if (Number(status.budget?.remaining_usd) <= 0)
    return {
      blocked: true,
      state: "budget",
      message:
        "The AI testing allowance has been used. Source loading and saved research remain available.",
    };
  return { blocked: false, state: "ready", message: "" };
}
