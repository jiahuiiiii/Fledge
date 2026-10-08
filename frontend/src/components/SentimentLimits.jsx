export default function SentimentLimits({ value, label }) {
  if (!value?.notice) return null;
  return (
    <details className="secondary-details source-limit" data-source-limit>
      <summary>Some sources were omitted · inspect limits</summary>
      <p>
        {label ? `${label}: ` : ""}
        {value.notice}
      </p>
    </details>
  );
}
