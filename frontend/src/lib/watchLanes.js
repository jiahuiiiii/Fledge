export function watchLaneLabel(lane) {
  if (lane === "fast") return "News check";
  if (lane === "slow") return "Discussion check";
  return "";
}

export function watchFrequencyLabel(watch) {
  return watch?.lanes_enabled ? "Discussion checks every" : "Check every";
}

export const separateWatchSteps = {
  separate_fast_lane: "Checked separately by news checks",
  separate_slow_lane: "Checked separately by discussion checks",
};
