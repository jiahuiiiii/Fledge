export default function MetaRow({ children, className = "", ...rest }) {
  return (
    <div className={`ui-meta-row ${className}`} {...rest}>
      {children}
    </div>
  );
}
