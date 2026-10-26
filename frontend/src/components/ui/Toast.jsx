// A short message at the bottom of the screen. It counts down on a thin bar,
// pauses while hovered or focused, and goes away by itself; Undo and close stay
// available until then. The countdown is a CSS animation, so no timers leak.
export default function Toast({ message, action, onDismiss, duration = 15000, id }) {
  if (!message) return null;
  return (
    <div className="ui-toast-region">
      <div className="ui-toast" role="status" aria-atomic="true" key={id ?? message}>
        <p className="ui-toast__message">{message}</p>
        {action && (
          <button type="button" className="ui-toast__action" onClick={action.onClick}>
            {action.label}
          </button>
        )}
        <button type="button" className="ui-toast__close" aria-label="Dismiss" onClick={onDismiss}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" aria-hidden="true">
            <path d="m6 6 12 12M18 6 6 18" />
          </svg>
        </button>
        <span
          className="ui-toast__timer"
          aria-hidden="true"
          style={{ animationDuration: `${duration}ms` }}
          onAnimationEnd={onDismiss}
        />
      </div>
    </div>
  );
}
