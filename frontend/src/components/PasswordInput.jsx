import { useState } from "react";
import "./PasswordInput.css";

// A password box with a Show/Hide button. Takes the same props as an input.
export default function PasswordInput({ className = "", ...rest }) {
  const [shown, setShown] = useState(false);
  return (
    <span className="password-input">
      <input
        {...rest}
        type={shown ? "text" : "password"}
        className={className}
      />
      <button
        type="button"
        className="password-input__toggle"
        aria-pressed={shown}
        aria-label={shown ? "Hide password" : "Show password"}
        onClick={() => setShown((value) => !value)}
      >
        {shown ? "Hide" : "Show"}
      </button>
    </span>
  );
}
