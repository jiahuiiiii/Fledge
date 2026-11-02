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
  if (status.key_rejected)
    return {
      blocked: true,
      state: "key_rejected",
      message:
        "The AI provider rejected the API key. Put a valid key in the .env file; AI analysis is paused until then. Saved research stays available.",
    };
  if (status.budget?.running > 0)
    return {
      blocked: true,
      state: "running",
      message:
        "AI is analysing a request. New sentiment work can wait in the queue; saved research remains available.",
    };
  return { blocked: false, state: "ready", message: "" };
}
