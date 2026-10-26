import "./ui.css";

// A stack of Disclosures with one tight gap, so collapsed sections read as a
// single list instead of loose blocks.
export default function DisclosureGroup({ className = "", children, ...rest }) {
  return (
    <div className={`ui-disclosure-group ${className}`} {...rest}>
      {children}
    </div>
  );
}
