// Keep the native checkbox for keyboard, form and assistive-technology behaviour.
export default function Checkbox(props) {
  return (
    <span className="custom-checkbox">
      <input {...props} type="checkbox" />
      <svg viewBox="0 0 20 20" aria-hidden="true">
        <path d="m5 10 3.2 3.2L15 6.5" />
      </svg>
    </span>
  );
}
