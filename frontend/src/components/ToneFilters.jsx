import { FilterGroup } from "./ui";
export const toneNames = {
  positive: "Positive",
  negative: "Negative",
  mixed: "Mixed",
  neutral: "Neutral",
  unclear: "Unclear",
};

export default function ToneFilters({ selected, onChange, counts, controls }) {
  return (
    <FilterGroup
      label="Filter analysed sources by tone"
      className="sentiment-counts tone-filters"
      controls={controls}
      value={selected}
      onValueChange={(value) => onChange(value === selected ? "all" : value)}
      options={[
        { value: "all", label: "All tones" },
        ...Object.entries(toneNames).map(([value, label]) => ({
          value,
          label,
          count: counts?.[value],
          className: `tone-${value}`,
        })),
      ]}
    />
  );
}
