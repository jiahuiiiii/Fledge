import { useEffect, useState } from "react";
import { api } from "../api/client";
import { stamp } from "./MarketResearch";
import { ResearchAlerts } from "./SentimentPanel";
import IdeaAlertChecks from "./IdeaAlertChecks";
import MoveAlertCard from "./MoveAlertCard";
import { ConditionChange } from "./IdeasAndChanges";
import AlertRating from "./AlertRating";
import "./DailyUpdates.css";

function money(value, exact = false) {
  const number = Number(value);
  if (!exact && number > 0 && number < 0.01) return "under US$0.01";
  return value == null || !Number.isFinite(number)
    ? "Unknown"
    : `US$${number.toLocaleString("en-SG", { minimumFractionDigits: 2, maximumFractionDigits: exact ? 9 : 2 })}`;
}

function noticeAmount(notice) {
  const amount = Number(notice.charged_nano_usd) / 1e9;
  const threshold = Number(notice.threshold_nano_usd) / 1e9;
  return amount > threshold && money(amount) === money(threshold)
    ? `just over ${money(threshold)}`
    : money(amount);
}

function DigestContents({ id, refresh, onOpen, onSource }) {
  const [page, setPage] = useState(0);
  const [retry, setRetry] = useState(0);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let current = true;
    setData(null);
    setError("");
    api
      .dailyDigest(id, page)
      .then((value) => {
        if (current) setData(value);
      })
      .catch((failure) => {
        if (current) setError(failure.message);
      });
    return () => {
      current = false;
    };
  }, [id, page, refresh, retry]);
  if (error)
    return (
      <div role="alert">
        <p>{error}</p>
        <button onClick={() => setRetry((n) => n + 1)}>
          Try reading recap again
        </button>
      </div>
    );
  if (!data || data.id !== id || data.page !== page)
    return <p role="status">Reading saved recap…</p>;
  return (
    <div className="daily-recap-contents">
      <p className="fine">
        {stamp(data.window_start)}–{stamp(data.window_end)}. {data.limitation}
      </p>
      {!data.total && (
        <p>
          No updates were assigned to this recap. This does not establish that
          nothing important happened.
        </p>
      )}
      {data.records.map((record) => (
        <article
          className="daily-recap-record"
          key={`${record.kind}:${record.id}`}
        >
          {record.kind === "company" ? (
            <ResearchAlerts
              alerts={[record.detail]}
              embedded
              readOnly
              onSource={onSource}
              onOpen={onOpen}
            />
          ) : record.kind === "idea" ? (
            <IdeaAlertChecks
              checks={[record.detail]}
              history
              readOnly
              onSource={onSource}
              onOpen={onOpen}
            />
          ) : record.kind === "move" ? (
            <MoveAlertCard alert={record.detail} readOnly onOpen={onOpen} />
          ) : (
            <ConditionChange change={record.detail} onOpen={onOpen} />
          )}
          <AlertRating record={record} />
        </article>
      ))}
      {data.total > data.page_size && (
        <div className="review-pagination">
          <button disabled={!page} onClick={() => setPage((n) => n - 1)}>
            Previous recap updates
          </button>
          <span>Page {page + 1}</span>
          <button
            disabled={(page + 1) * data.page_size >= data.total}
            onClick={() => setPage((n) => n + 1)}
          >
            Next recap updates
          </button>
        </div>
      )}
    </div>
  );
}

function Recap({ digest, refresh, onOpen, onSource }) {
  const [opened, setOpened] = useState(false);
  return (
    <details
      className="daily-recap"
      onToggle={(event) => {
        setOpened(event.currentTarget.open);
      }}
    >
      <summary>
        {stamp(digest.window_end)} · {digest.total}{" "}
        {digest.total === 1 ? "update" : "updates"}
        {digest.preview ? " · Preview" : ""}
      </summary>
      {digest.preview && <p className="fine">Preview · not sent to Telegram</p>}
      {opened && (
        <DigestContents
          id={digest.id}
          refresh={refresh}
          onOpen={onOpen}
          onSource={onSource}
        />
      )}
    </details>
  );
}

export default function DailyUpdates({ refresh = 0, onOpen, onSource }) {
  const [opened, setOpened] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let current = true;
    setError("");
    api
      .dailyUpdates()
      .then((value) => {
        if (current) setData(value);
      })
      .catch((failure) => {
        if (current) setError(failure.message);
      });
    return () => {
      current = false;
    };
  }, [refresh, retry]);
  if (data?.enabled === false) return null;
  const today = data?.today_spend;
  return (
    <details
      className="daily-updates"
      aria-label="Daily recaps and AI spending"
      onToggle={(event) => {
        if (event.target === event.currentTarget)
          setOpened(event.currentTarget.open);
      }}
    >
      <summary>
        Daily recaps{today ? ` · AI today ${money(today.charged_usd)}` : ""}
      </summary>
      {error && (
        <div role="alert">
          <p>{error}</p>
          <button onClick={() => setRetry((n) => n + 1)}>
            Try reading daily updates again
          </button>
        </div>
      )}
      {!data && !error && <p role="status">Reading saved daily updates…</p>}
      {data && opened && (
        <div className="daily-updates-body">
          {data.preparation?.error_message && (
            <p className="warning" role="status">
              {data.preparation.error_message} Next check{" "}
              {stamp(data.preparation.next_check_at)}.
            </p>
          )}
          {today && (
            <section className="daily-spend" aria-label="Today's AI spending">
              <h3>AI spending today</h3>
              <p>
                <strong>{money(today.charged_usd)}</strong> confirmed ·{" "}
                {money(today.pending_max_usd)} maximum awaiting confirmation
              </p>
              <p className="fine">
                {today.day} in Singapore · all AI use in this installation,
                including {money(today.experiment_charged_usd)} for tests.
                Checked {stamp(today.observed_at)}. Unresolved amounts are
                separate from confirmed charges.
              </p>
              <details>
                <summary>Exact spending totals</summary>
                <p>
                  {money(today.charged_usd, true)} confirmed ·{" "}
                  {money(today.pending_max_usd, true)} unresolved maximum.
                </p>
              </details>
              {!!data.spending.length && (
                <details>
                  <summary>Earlier daily spending</summary>
                  {data.spending.map((value) => (
                    <div className="daily-spend-history" key={value.id}>
                      <strong>{value.day}</strong>
                      <p>
                        {money(value.current.charged_usd)} confirmed ·{" "}
                        {money(value.current.pending_max_usd)} maximum awaiting
                        confirmation
                      </p>
                      <p className="fine">
                        Updated {stamp(value.current.observed_at)}. Saved at{" "}
                        {stamp(value.observed_at)}:{" "}
                        {money(Number(value.charged_nano_usd) / 1e9)} confirmed,{" "}
                        {money(Number(value.pending_max_nano_usd) / 1e9)}{" "}
                        unresolved maximum.
                      </p>
                    </div>
                  ))}
                </details>
              )}
            </section>
          )}
          {data.notices.map((notice) => (
            <p className="daily-cost-notice" role="status" key={notice.id}>
              {notice.preview ? "Preview · " : ""}AI spending crossed{" "}
              {money(Number(notice.threshold_nano_usd) / 1e9)} for {notice.day}:{" "}
              {noticeAmount(notice)} confirmed when checked{" "}
              {stamp(notice.created_at)}.
            </p>
          ))}
          {!data.digests.length ? (
            <p className="fine">No daily recap has been prepared yet.</p>
          ) : (
            <section aria-label="Saved daily recaps">
              <h3>Saved daily recaps</h3>
              <p className="fine">
                Medium-priority updates together. Opening a recap does not mark
                its alerts reviewed.
              </p>
              {data.digests.map((digest) => (
                <Recap
                  key={digest.id}
                  digest={digest}
                  refresh={refresh}
                  onOpen={onOpen}
                  onSource={onSource}
                />
              ))}
            </section>
          )}
        </div>
      )}
    </details>
  );
}
