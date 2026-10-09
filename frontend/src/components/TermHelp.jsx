import { useState } from "react";
import Modal from "./Modal";
import { financialTerms } from "../lib/companion";
import "./Companion.css";

export default function TermHelp({ term }) {
  const [open, setOpen] = useState(false);
  const definition = financialTerms[term];
  if (!definition) return null;
  const [title, meaning, check] = definition;
  return (
    <span className="term-help">
      <button
        type="button"
        className="term-help-button"
        aria-label={`Explain ${title}`}
        aria-haspopup="dialog"
        onClick={() => setOpen(true)}
      >
        <span aria-hidden="true">?</span>
      </button>
      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title={title}
        className="term-dialog"
      >
        <div className="companion-dialog-body">
          <p>{meaning}</p>
          <h3>When you read this figure</h3>
          <p>{check}</p>
        </div>
      </Modal>
    </span>
  );
}
