import { useState } from "react";
import { Button } from "./ui";

// Long reasoning stays readable: a few lines first, the rest on request.
const LONG = 240;

export default function IdeaReasoning({ text, empty }) {
  const [open, setOpen] = useState(false);
  const value = (text || "").trim();
  if (!value) return <p className="idea-reasoning empty">{empty}</p>;
  const long = value.length > LONG;
  return (
    <div className="idea-reasoning-block">
      <p
        className={`idea-reasoning ${long && !open ? "clamped" : ""}`}
        id="idea-reasoning-text"
      >
        {value}
      </p>
      {long && (
        <Button
          variant="plain"
          size="sm"
          aria-expanded={open}
          aria-controls="idea-reasoning-text"
          onClick={() => setOpen(!open)}
        >
          {open ? "Show less" : "Show more"}
        </Button>
      )}
    </div>
  );
}
