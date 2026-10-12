import { useProfile } from "../lib/profile";
import "./Onboarding.css";

// The tailored part of the home page: built by the server from the user's
// first-login answers and watchlist (GET /api/v1/home). No company is suggested.
export default function PersonalHome({ onAddCompany, onOpenCompany }) {
  const { home } = useProfile();
  if (!home?.profile?.completed) return null;
  const { headline, next_step: step, interests, watchlist } = home;
  const first = watchlist.companies[0];
  const action =
    step.action === "add_company"
      ? ["Add a company", onAddCompany]
      : first
        ? [`Open ${first.symbol}`, () => onOpenCompany(first.id)]
        : null;
  return (
    <section className="personal-home" aria-label="Your home">
      <div>
        <span className="section-label">FOR YOU</span>
        <h2>{headline}</h2>
        <p>{step.label}</p>
        {interests.length > 0 && (
          <p className="fine">
            Your interests: {interests.map((item) => item.label).join(", ")}.
            Search for any company you’re curious about.
          </p>
        )}
      </div>
      <div className="personal-home-side">
        <p className="personal-home-count">
          Watchlist <strong>{watchlist.count}</strong> / {watchlist.limit}
        </p>
        {action && !(step.action === "add_company" && watchlist.full) && (
          <button type="button" className="primary" onClick={action[1]}>
            {action[0]}
          </button>
        )}
      </div>
    </section>
  );
}
