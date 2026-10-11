// One "Update data" action for the whole company page. Section buttons ask the
// app to open it instead of starting their own separate refreshes.
export const UPDATE_EVENT = "fledge:update-data";
export function requestUpdate() {
  window.dispatchEvent(new CustomEvent(UPDATE_EVENT));
}
