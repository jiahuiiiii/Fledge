import { useProfile } from "../lib/profile";
import { Button } from "./ui";
import { typeName } from "../lib/investorTypes";
import "./Onboarding.css";

// The tailored part of the home page: built by the server from the user's
// first-login answers and watchlist (GET /api/v1/home). No company is suggested
// except the practice company, which is labelled as an example.
export default function PersonalHome({
  onAddCompany,
  onOpenCompany,
  practice,
}) {
  const { home } = useProfile();
  if (!home?.profile) return null;
  const { headline, next_step: step, watchlist, profile } = home;
  // People who skipped the first questions still get a way in, without a nag.
  if (!profile.completed)
    return (
      <section className="personal-home" aria-label="Your home">
        <div className="personal-home-main">
          <h2>Welcome to Fledge</h2>
          <p>Add a company you own, use or want to understand.</p>
        </div>
        <div className="personal-home-actions">
          {practice && (
            <Button
              variant="primary"
              type="button"
              onClick={() => onOpenCompany(practice.id)}
            >
              See an example: {practice.name || practice.symbol}
            </Button>
          )}
          <button type="button" onClick={onAddCompany}>
            Add a company
          </button>
        </div>
        <p className="personal-home-type">
          What kind of investor are you?{" "}
          <button
            type="button"
            className="text-link"
            onClick={() => dispatchEvent(new Event("fledge:retake-quiz"))}
          >
            Find out in 4 questions
          </button>
        </p>
      </section>
    );
  const first = watchlist.companies[0];
  const action =
    step.action === "add_company"
      ? watchlist.full
        ? null
        : [
            profile.goal === "explore" ? "Browse companies" : "Add a company",
            onAddCompany,
          ]
      : first
        ? [`Open ${first.symbol}`, () => onOpenCompany(first.id)]
        : null;
  const type = typeName(profile.investor_type);
  return (
    <section className="personal-home" aria-label="Your home">
      <div className="personal-home-main">
        <h2>{headline}</h2>
        <p>{step.label}</p>
      </div>
      <div className="personal-home-actions">
        {action && (
          <Button variant="primary" onClick={action[1]}>
            {action[0]}
          </Button>
        )}
        {!first && practice && (
          <button type="button" onClick={() => onOpenCompany(practice.id)}>
            See an example: {practice.name || practice.symbol}
          </button>
        )}
      </div>
      <p className="personal-home-type">
        {type ? (
          <>
            Your investor type: <strong>{type}</strong>.{" "}
          </>
        ) : (
          "What kind of investor are you? "
        )}
        <button
          type="button"
          className="text-link"
          onClick={() => dispatchEvent(new Event("fledge:retake-quiz"))}
        >
          {type ? "Retake" : "Find out in 2 questions"}
        </button>
      </p>
    </section>
  );
}
