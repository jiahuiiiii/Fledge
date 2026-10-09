import { useId, useState } from "react";
import Select from "./Select";
import "./RevenueBreakdown.css";

const day = (value) =>
  new Date(value).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
const exact = (value) => {
  if (value == null) return "Unavailable";
  const [whole, fraction] = String(value).split(".");
  return `US$${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}${fraction ? `.${fraction}` : ""}`;
};
const amount = (value) => {
  if (value == null) return "Unavailable";
  const n = Number(value),
    scale = Math.abs(n) >= 1e9 ? 1e9 : Math.abs(n) >= 1e6 ? 1e6 : 1;
  return `US$${(n / scale).toLocaleString("en-GB", { maximumFractionDigits: 2 })}${scale === 1e9 ? "bn" : scale === 1e6 ? "m" : ""}`;
};
const share = (value) =>
  Number(value) > 0 && Number(value) < 0.1
    ? "<0.1%"
    : `${Number(value).toFixed(1)}%`;
const periodKey = (group) => `${group.start}/${group.end}`;
const colours = [
  "#a6c9b2",
  "#91bccc",
  "#b8a6ce",
  "#d1bd91",
  "#c995a3",
  "#a6bd89",
];
const sourceLink = (group, input) =>
  `${group.url}${input?.fact_id ? `#${encodeURIComponent(input.fact_id)}` : ""}`;

function Evidence({ group, row, label = "Inspect figure" }) {
  return (
    <details className="mix-evidence">
      <summary>{label}</summary>
      <p>
        Exact value: {exact(row.value)}. {row.reason}
      </p>
      {row.member && <p>Filing category tag: {row.member}</p>}
      {row.inputs.map((input, index) => (
        <p key={index}>
          <a href={sourceLink(group, input)} target="_blank" rel="noreferrer">
            Original {group.form} figure ↗
          </a>
          <br />
          Displayed {input.display || "missing"}; scale 10^{input.scale}; unit{" "}
          {input.unit || "unknown"}.
          <br />
          {input.concept} · context {input.context_id}
        </p>
      ))}
    </details>
  );
}

export default function RevenueBreakdown({ data }) {
  const id = useId();
  const [kind, setKind] = useState("");
  const [period, setPeriod] = useState("");
  if (!data) return null;
  const groups = data.groups || [];
  const kinds = [...new Set(groups.map((group) => group.kind))];
  const activeKind = kinds.includes(kind) ? kind : kinds[0];
  const periods = groups.filter((group) => group.kind === activeKind);
  const group =
    periods.find((item) => periodKey(item) === period) || periods[0];
  const members = group
    ? [...group.members].sort((a, b) =>
        a.value == null
          ? 1
          : b.value == null
            ? -1
            : Number(b.value) - Number(a.value),
      )
    : [];
  return (
    <section
      className="revenue-mix financial-chart-card"
      aria-labelledby={`${id}-title`}
    >
      <span className="section-label">REPORTED REVENUE BREAKDOWN</span>
      <h2 id={`${id}-title`}>Where revenue comes from</h2>
      <p>
        The company’s own categories, taken from its saved original filings.
      </p>
      {!group ? (
        <p>{data.message}</p>
      ) : (
        <>
          <div className="mix-controls">
            <label htmlFor={`${id}-kind`}>
              View by
              <Select
                id={`${id}-kind`}
                value={activeKind}
                onChange={(event) => setKind(event.target.value)}
              >
                {kinds.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </Select>
            </label>
            <label htmlFor={`${id}-period`}>
              Reporting period
              <Select
                id={`${id}-period`}
                value={periodKey(group)}
                onChange={(event) => setPeriod(event.target.value)}
              >
                {periods.map((item) => (
                  <option key={periodKey(item)} value={periodKey(item)}>
                    {item.period} · {day(item.end)}
                  </option>
                ))}
              </Select>
            </label>
          </div>
          <div
            className="mix-reading"
            key={`${activeKind}/${periodKey(group)}`}
          >
            <div className="mix-total" aria-live="polite">
              <div>
                <span>Company revenue</span>
                <strong>{amount(group.total)}</strong>
              </div>
              <p>
                {group.period}
                <br />
                {day(group.start)} – {day(group.end)}
              </p>
            </div>
            {group.chartable ? (
              <>
                <div className="mix-bar" aria-hidden="true">
                  {members.map((member, index) => (
                    <span
                      key={member.member}
                      style={{
                        width: `${Number(member.percentage)}%`,
                        background: colours[index % colours.length],
                      }}
                    />
                  ))}
                </div>
                <p className="mix-note">
                  The categories add up to the company total. Percentages are
                  rounded.
                </p>
              </>
            ) : (
              <p className="mix-unavailable" role="status">
                {group.reason} The reported amounts are shown individually
                below.
              </p>
            )}
            {activeKind === "Reported geographies" && (
              <p className="mix-note">
                Countries and regions may overlap. Read the filing for how the
                company assigns revenue to each location.
              </p>
            )}
            <ul className="mix-members">
              {members.map((member, index) => (
                <li key={member.member}>
                  <div className="mix-member-line">
                    <span className="mix-name">
                      <i
                        aria-hidden="true"
                        style={{ background: colours[index % colours.length] }}
                      />
                      {member.label}
                    </span>
                    <span className="mix-value">
                      <strong>{amount(member.value)}</strong>
                      {group.chartable && (
                        <span>{share(member.percentage)}</span>
                      )}
                    </span>
                  </div>
                  {group.chartable && (
                    <div className="mix-member-track" aria-hidden="true">
                      <span
                        style={{
                          width: `${Number(member.percentage)}%`,
                          background: colours[index % colours.length],
                        }}
                      />
                    </div>
                  )}
                  <Evidence group={group} row={member} />
                </li>
              ))}
            </ul>
            <Evidence
              group={group}
              row={{ value: group.total, inputs: group.total_inputs }}
              label="Inspect company total"
            />
            <p className="mix-note">
              SEC accepted{" "}
              {new Date(group.accepted_at).toLocaleString("en-GB", {
                timeZone: "UTC",
              })}{" "}
              UTC ·{" "}
              <a href={group.url} target="_blank" rel="noreferrer">
                Read {group.form} ↗
              </a>
            </p>
          </div>
        </>
      )}
      <details className="mix-limits">
        <summary>Coverage &amp; definitions</summary>
        {(data.limitations || []).map((text) => (
          <p key={text}>{text}</p>
        ))}
        {data.gaps?.map((gap) => (
          <p key={gap.document_id}>{gap.reason}</p>
        ))}
      </details>
    </section>
  );
}
