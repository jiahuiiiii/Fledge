import { formatTimestamp } from "../lib/dateTime";
import PriceChange from "./PriceChange";

const money = (value) =>
  Number(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

// Pre-market / after-hours price, shown small under the closing price.
export default function ExtendedPrice({ line }) {
  return (
    <span className="quote-extended">
      <span className="quote-extended-price">{money(line.price)}</span>
      <PriceChange movement={line.movement} />
      <span className="quote-extended-when">
        <span className="quote-session">{line.label}</span> ·{" "}
        {formatTimestamp(line.quoted_at)}
      </span>
    </span>
  );
}
