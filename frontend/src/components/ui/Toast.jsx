// Bottom-of-screen messages, built on react-toastify: a countdown bar, pause on
// hover or focus, and automatic dismissal. Mount <ToastHost /> once; call
// showToast(message, { action }) or hideToast(id) from anywhere.
import { ToastContainer, toast, Slide } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import "./toast.css";

export const TOAST_MS = 10000;

function Body({ message, action, closeToast }) {
  return (
    <div className="ui-toast__body">
      <p className="ui-toast__message">{message}</p>
      {action && (
        <button
          type="button"
          className="ui-toast__action"
          onClick={() => {
            action.onClick();
            closeToast?.();
          }}
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

export function showToast(message, { action, id, onClose } = {}) {
  if (!message) return;
  toast(<Body message={message} action={action} />, { toastId: id, onClose });
}

export function hideToast(id) {
  toast.dismiss(id);
}

export default function ToastHost() {
  return (
    <ToastContainer
      position="bottom-center"
      autoClose={TOAST_MS}
      transition={Slide}
      limit={3}
      closeOnClick={false}
      pauseOnHover
      pauseOnFocusLoss={false}
      newestOnTop
      theme="dark"
      className="ui-toast-host"
      toastClassName="ui-toast"
      progressClassName="ui-toast__progress"
    />
  );
}
