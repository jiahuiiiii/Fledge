import "./FledgeLoader.css";

// The Fledge fledgling: hops on its branch while work runs, and gives a little
// flap and a happy face when it is done. Decorative only; callers announce
// progress in text. Still under reduced motion.
export default function FledgeLoader({ done = false, size = 132 }) {
  return (
    <svg
      className={`fledge-loader${done ? " is-done" : ""}`}
      width={size}
      height={(size * 96) / 132}
      viewBox="0 0 132 96"
      aria-hidden="true"
      focusable="false"
    >
      <g className="fledge-loader__sparks">
        <path d="M98 30 l9 -9 m-6 0 h6 v6" />
        <path d="M108 46 l6 -6 m-4 0 h4 v4" />
      </g>
      <path
        className="fledge-loader__branch"
        d="M8 84 C 40 80, 80 86, 124 80"
      />
      <path
        className="fledge-loader__leaf"
        d="M112 81 c 4 -8 12 -9 14 -8 c -2 6 -8 10 -14 8 z"
      />
      <ellipse className="fledge-loader__shadow" cx="62" cy="82" rx="16" ry="2.5" />
      <g className="fledge-loader__bird">
        <path className="fledge-loader__feet" d="M56 74 v6 m-3 0 h6 M66 74 v6 m-3 0 h6" />
        <path className="fledge-loader__tail" d="M42 62 L30 56 L34 66 Z" />
        <ellipse className="fledge-loader__body" cx="60" cy="58" rx="22" ry="19" />
        <ellipse className="fledge-loader__belly" cx="65" cy="64" rx="12" ry="10" />
        <path
          className="fledge-loader__tuft"
          d="M58 40 c -2 -6 2 -9 5 -7 c -3 1 -3 4 -1 6"
        />
        <g className="fledge-loader__wing">
          <path d="M46 56 c 2 -9 14 -10 18 -2 c -3 8 -13 11 -18 2 z" />
        </g>
        <circle className="fledge-loader__cheek" cx="73" cy="58" r="2.6" />
        <g className="fledge-loader__eye">
          <circle cx="70" cy="50" r="2.8" />
          <circle className="fledge-loader__glint" cx="71" cy="49" r="0.9" />
        </g>
        <path className="fledge-loader__happy" d="M66.5 51 q 3.5 -4 7 0" />
        <path className="fledge-loader__beak" d="M80 52 l7 2.5 l-7 2.5 z" />
      </g>
    </svg>
  );
}
