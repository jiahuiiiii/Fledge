import ResearchLoading, {
  ResearchProgressToggle,
} from "./components/ResearchLoading";
import {
  useWorkspaceLayout,
  WorkspaceSidebar,
} from "./components/WorkspaceControls";
import { modelAvailability } from "./lib/modelAvailability";
import EmptyWorkspace from "./components/EmptyWorkspace";
import CompanyAvatar from "./components/CompanyAvatar";
import CompanySidebar, { CompanyAddButton } from "./components/CompanySidebar";
import Checkbox from "./components/Checkbox";
import CompanyDialog from "./components/CompanyDialog";
import { companyName } from "./lib/companyIdentity";
import LoadingSkeleton from "./components/LoadingSkeleton";
import RemovalNotice from "./components/RemovalNotice";
import RetainedView from "./components/RetainedView";
import { readableLoad } from "./lib/loading";
import { preferPriceRead } from "./lib/priceRefresh";
import {
  hiddenCompaniesKey,
  parseHiddenCompanies,
} from "./lib/companyVisibility";
import Select from "./components/Select";
import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api/client";
import { roleLabel, resultLabel } from "./lib/conditionRoles";
import { revisionPayload } from "./lib/kestrelDiff";
import Modal from "./components/Modal";
import SourceConnections from "./components/SourceConnections";
import PriceChart from "./components/PriceChart";
import ResearchQuestion from "./components/ResearchQuestion";
import QuestionSelector, {
  questionDefaults,
} from "./components/QuestionSelector";
import HistoricalPrices from "./components/HistoricalPrices";
import MarketResearch, { MarketQuote } from "./components/MarketResearch";
import SentimentPanel from "./components/SentimentPanel";
import ResearchNavigation, {
  ResearchSectionHeader,
} from "./components/ResearchNavigation";
import SocialConversation from "./components/SocialConversation";
import UpdateInbox from "./components/UpdateInbox";
import TelegramSettings from "./components/TelegramSettings";
import IdeasAndChanges from "./components/IdeasAndChanges";
import FilingDetails from "./components/FilingDetails";
import FinancialPerformance from "./components/FinancialPerformance";
import OriginalFilings from "./components/OriginalFilings";
const FinancialsPage = lazy(() => import("./components/FinancialsPage"));
const SectorPosition = lazy(() => import("./components/SectorPosition"));
const CompanyOverview = lazy(() => import("./components/CompanyOverview"));
const AllHistory = lazy(() =>
  import("./components/CompanyOverview").then((module) => ({
    default: module.AllHistory,
  })),
);
import BusinessPanel from "./components/BusinessPanel";
import CompanySnapshot from "./components/CompanySnapshot";
import CompanionGuide, { ExplorationPrompt } from "./components/CompanionGuide";
import AccountGate from "./components/AccountGate";
import FilingWatch from "./components/FilingWatch";
import ValuationPanel from "./components/ValuationPanel";
import IdeaAlertChecks from "./components/IdeaAlertChecks";
const ReviewDigest = lazy(() => import("./components/ReviewDigest"));
import HistoryPanel from "./components/HistoryPanel";
import EventAssessment, {
  EventEditor,
  EventDefinitions,
} from "./components/EventConditions";
import ProposalPanel from "./components/ProposalPanel";
import { combineSuggestions } from "./lib/proposals";
import ReviewDownload from "./components/ReviewDownload";
import ReportingAge, { ageLabel } from "./components/ReportingAge";
import IdeaEvidenceReview from "./components/IdeaEvidenceReview";
import ReportExpectationEditor, {
  ReportExpectationText,
} from "./components/ReportExpectation";

const FmpPanel = lazy(() => import("./components/FmpPanel"));
const OutlookPage = lazy(() => import("./components/OutlookPage"));

const metrics = {
  revenue_growth: "Revenue growth",
  operating_margin: "Operating margin",
};
const questionDefault = questionDefaults[0];
const date = (value) =>
  new Date(value).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
const newCondition = (period_type = "quarter") => ({
  role: "required",
  period_type,
  max_report_age_days: "",
  expected_period_end: "",
  expected_report_by: "",
  id: crypto.randomUUID(),
  metric: "revenue_growth",
  operator: ">=",
  value: "",
});
const formFor = (version, question) => ({
  revision: version?.revision || 0,
  question: version?.question || question,
  reasoning: version?.reasoning || "",
  events: (version?.events || []).map(
    ({
      condition_id,
      description,
      evidence_requirement,
      role,
      window_start,
      deadline,
      date_basis,
      repeat_months,
      repeat_count,
    }) => ({
      condition_id,
      description,
      evidence_requirement,
      role,
      date_basis: date_basis || "report_publication",
      repeat_months: repeat_months || 0,
      repeat_count: repeat_count || 1,
      window_start: window_start || "",
      deadline: deadline || "",
    }),
  ),
  conditions:
    version?.conditions.map((c) => ({
      id: c.condition_id,
      metric: c.metric,
      role: c.role || "required",
      period_type: c.period_type || "quarter",
      max_report_age_days: c.max_report_age_days ?? "",
      expected_period_end: c.expected_period_end || "",
      expected_report_by: c.expected_report_by || "",
      operator: c.operator,
      value: c.threshold == null ? "" : String(c.threshold),
    })) || [],
});
function Icon({ name, ...props }) {
  const paths = {
    workspace: "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
    idea: "M9 18h6 M10 21h4 M8 14a7 7 0 1 1 8 0l-1 3H9z",
    history: "M3 11a9 9 0 1 1 2 7 M3 4v7h7 M12 7v5l4 2",
    arrow: "M5 12h14 M14 7l5 5-5 5",
    source: "M14 3h7v7 M21 3l-9 9 M10 3H3v18h18v-7",
    check: "M5 12l4 4L19 6",
    plus: "M12 5v14 M5 12h14",
    pulse: "M2 12h5l3-7 4 14 3-7h5",
  };
  return (
    <svg
      width="19"
      height="19"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      <path d={paths[name] || paths.workspace} />
    </svg>
  );
}
const defaultCompany = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
function readDestination() {
  const params = new URLSearchParams(location.search);
  const view = params.get("view");
  return {
    id: params.get("company") || "",
    view: [
      "workspace",
      "idea",
      "ideas",
      "updates",
      "history",
      "review",
    ].includes(view)
      ? view === "history"
        ? params.get("company")
          ? "idea"
          : "ideas"
        : view
      : "workspace",
    evaluation:
      params.get("evaluation") || (view === "history" ? "history" : null),
  };
}
export default function App() {
  return (
    <AccountGate>
      {(session, signOut) => (
        <ResearchApp
          key={session.account_id}
          session={session}
          signOut={signOut}
        />
      )}
    </AccountGate>
  );
}
function ResearchApp({ signOut, session }) {
  const companyVisibilityKey = `${hiddenCompaniesKey}:${session.account_id || "local"}`;
  const [destination, setDestination] = useState(readDestination);
  const [inboxState, setInboxState] = useState({
    review: "pending",
    page: 0,
    cutoff: "",
  });
  const [hiddenCompanies, setHiddenCompanies] = useState(() => {
    try {
      return parseHiddenCompanies(
        localStorage.getItem(companyVisibilityKey) ??
          (session.is_installation_owner
            ? localStorage.getItem(hiddenCompaniesKey)
            : null),
      );
    } catch {
      return [];
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem(
        companyVisibilityKey,
        JSON.stringify(hiddenCompanies),
      );
    } catch {
      /* Keep in-memory controls usable when browser storage is unavailable. */
    }
  }, [hiddenCompanies, companyVisibilityKey]);
  useEffect(() => {
    const restore = () => {
      setDestination(readDestination());
      setInboxState((state) => ({ ...state, page: 0, cutoff: "" }));
    };
    addEventListener("popstate", restore);
    return () => removeEventListener("popstate", restore);
  }, []);
  function choose(id, view = "workspace", evaluation = null) {
    if (view === "history") {
      view = id ? "idea" : "ideas";
      evaluation ||= "history";
    }
    const params = new URLSearchParams({ company: id, view });
    if (evaluation) params.set("evaluation", evaluation);
    history.replaceState(null, "", `?${params}`);
    if (id !== destination.id)
      setInboxState((state) => ({ ...state, page: 0, cutoff: "" }));
    setDestination({ id, view, evaluation });
  }
  return (
    <CompanyWorkspace
      signOut={signOut}
      instrumentId={destination.id || defaultCompany}
      selectedCompanyId={destination.id}
      onWorkspaceReset={(resetSelection) => {
        setHiddenCompanies([]);
        if (resetSelection) choose("");
      }}
      inboxFilters={{ ...inboxState, company: destination.id }}
      onInboxFiltersChange={(change) => {
        const current = { ...inboxState, company: destination.id };
        const next = typeof change === "function" ? change(current) : change;
        const { company, ...filters } = next;
        setInboxState(filters);
        if (company !== destination.id) choose(company, destination.view);
      }}
      initialView={destination.view}
      initialEvaluation={destination.evaluation}
      onChoose={choose}
      hiddenCompanies={hiddenCompanies}
      onHideCompany={(id) =>
        setHiddenCompanies((ids) => [...new Set([...ids, id])])
      }
      onRestoreCompany={(id) =>
        setHiddenCompanies((ids) => ids.filter((value) => value !== id))
      }
    />
  );
}
function CompanyWorkspace({
  signOut,
  instrumentId,
  selectedCompanyId,
  onWorkspaceReset,
  inboxFilters,
  onInboxFiltersChange,
  initialView,
  initialEvaluation,
  onChoose,
  hiddenCompanies,
  onHideCompany,
  onRestoreCompany,
}) {
  const mainPane = useRef(null);
  const [layout, toggleLayout] = useWorkspaceLayout();
  const progressFocusRequested = useRef(false);
  function toggleProgress() {
    progressFocusRequested.current = true;
    toggleLayout("progressHidden");
  }
  useEffect(() => {
    if (!progressFocusRequested.current) return;
    progressFocusRequested.current = false;
    document
      .querySelector(
        layout.progressHidden ? ".progress-restore" : ".collapse-progress",
      )
      ?.focus({ preventScroll: true });
  }, [layout.progressHidden]);
  // Keep the shell alive. A scope token fences late responses, including A → B → A.
  const scope = useMemo(
    () => ({ instrumentId, selectedCompanyId }),
    [instrumentId, selectedCompanyId],
  );
  const activeScope = useRef(scope);
  activeScope.current = scope;
  const [loadedScope, setLoadedScope] = useState(null);
  const [loadError, setLoadError] = useState("");
  const companyLoading = loadedScope !== scope;
  const [removedCompany, setRemovedCompany] = useState(null);
  const view = initialView;
  const ideaSidebarAvailable = !!selectedCompanyId && view === "workspace";
  const ideaSidebarHidden = true;
  const [researchOpen, setResearchOpen] = useState(false);
  const [exploration, setExploration] = useState(null);
  useEffect(() => setExploration(null), [scope]);
  useEffect(() => {
    if (!exploration) return;
    if (exploration.topic && !exploration.recorded) return;
    const frame = requestAnimationFrame(() => {
      document.getElementById(`research-tab-${exploration.section}`)?.focus();
      mainPane.current?.scrollTo(0, 0);
    });
    return () => cancelAnimationFrame(frame);
  }, [exploration]);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [updatesOpen, setUpdatesOpen] = useState(false);
  const [priceChartOpen, setPriceChartOpen] = useState(false);
  useEffect(() => {
    mainPane.current?.scrollTo(0, 0);
  }, [view, initialEvaluation, scope]);
  const setView = (next) => onChoose(selectedCompanyId, next);
  const [data, setData] = useState(null),
    [priceRead, setPriceRead] = useState(null),
    [panelRead, setPanelRead] = useState(null),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [tab, setTab] = useState("business"),
    [question, setQuestion] = useState(questionDefault);
  const [source, setSource] = useState(null),
    [editor, setEditor] = useState(null),
    [approved, setApproved] = useState(false),
    [formError, setFormError] = useState(""),
    [conflict, setConflict] = useState(null),
    [proposalIds, setProposalIds] = useState([]),
    [proposalStale, setProposalStale] = useState(false),
    [modelStatus, setModelStatus] = useState(null),
    [companySearch, setCompanySearch] = useState(""),
    [addingCompany, setAddingCompany] = useState(false);
  const [loadingRun, setLoadingRun] = useState(null);
  const [loadingError, setLoadingError] = useState("");
  const lastLoadingRevision = useRef(null);
  async function startLoading(options = {}) {
    const token = scope;
    setLoadingError("");
    try {
      const run = await api.startResearchLoading(instrumentId, options);
      if (activeScope.current === token) setLoadingRun(run);
    } catch (e) {
      if (activeScope.current === token) setLoadingError(e.message);
    }
  }
  useEffect(() => {
    setLoadingRun(null);
    setLoadingError("");
    lastLoadingRevision.current = null;
  }, [scope]);
  useEffect(() => {
    if (
      companyLoading ||
      !selectedCompanyId ||
      !data?.instrument ||
      data.instrument.mode === "recorded"
    )
      return;
    startLoading({ initial: true });
    let stopped = false,
      reading = false;
    const timer = setInterval(async () => {
      if (stopped || reading || document.hidden) return;
      reading = true;
      try {
        const [run, status] = await Promise.all([
          api.researchLoading(instrumentId),
          api.modelStatus(),
        ]);
        if (stopped || activeScope.current !== scope) return;
        setModelStatus(status);
        setLoadingRun(run);
        setLoadingError("");
        const revision = JSON.stringify(run?.steps.map((s) => s.status));
        if (revision !== lastLoadingRevision.current) {
          lastLoadingRevision.current = revision;
          await refresh();
        }
      } catch (e) {
        if (!stopped && activeScope.current === scope)
          setLoadingError(
            "Cannot reach the local app. Progress will reconnect when it is running.",
          );
      } finally {
        reading = false;
      }
    }, 1500);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, [scope, companyLoading, !!data?.instrument, selectedCompanyId]);
  function chooseCompany(id) {
    onChoose(id, !id && view === "idea" ? "workspace" : view);
  }
  async function readCompany() {
    const [next, model] = await Promise.all([
      api.workspace(instrumentId),
      api.modelStatus().catch(() => null),
    ]);
    if (next.empty) return { next, model, prices: null, panel: null };
    const settle = (request) =>
      request.then(
        (data) => ({ data, error: "" }),
        (error) => ({ data: null, error: error.message }),
      );
    const [prices, panel] = await Promise.all([
      selectedCompanyId && next.instrument.mode !== "recorded"
        ? settle(api.priceHistory(instrumentId))
        : null,
      selectedCompanyId && tab === "expectations"
        ? settle(api.expectationHistory(instrumentId))
        : selectedCompanyId && tab === "valuation"
          ? settle(api.valuationContext(instrumentId))
          : null,
    ]);
    return { next, prices, model, panel: panel && { ...panel, tab } };
  }
  async function refresh() {
    const { next, prices, model, panel } = await readableLoad(
      readCompany(),
      companyLoading ? 280 : 0,
    );
    if (activeScope.current === scope) {
      setData(next);
      setPriceRead((old) => preferPriceRead(old, prices));
      setPanelRead(panel);
      setModelStatus(model);
      if (loadedScope !== scope)
        setQuestion(
          next.question_library?.selected_question ||
            next.versions[0]?.question ||
            next.research_action?.question ||
            questionDefault,
        );
      setLoadedScope(scope);
      setLoadError("");
    }
    return next;
  }
  function retryWorkspace() {
    setLoadError("");
    refresh().catch((e) => {
      if (activeScope.current === scope) setLoadError(e.message);
    });
  }
  useEffect(() => {
    let active = true;
    setLoadError("");
    setError("");
    setNotice("");
    setBusy(false);
    setSource(null);
    setResearchOpen(false);
    setSourcesOpen(false);
    setUpdatesOpen(false);
    setPriceChartOpen(false);
    setEditor(null);
    setApproved(false);
    setFormError("");
    setConflict(null);
    setProposalIds([]);
    setProposalStale(false);
    setAddingCompany(false);
    setModelStatus(null);
    api
      .session()
      .then(() => (active ? readableLoad(readCompany()) : null))
      .then((packet) => {
        if (active && packet && activeScope.current === scope) {
          const { next: d, prices, model, panel } = packet;
          setData(d);
          setPriceRead(prices);
          setPanelRead(panel);
          setModelStatus(model);
          setLoadedScope(scope);
          setQuestion(
            d.question_library?.selected_question ||
              d.versions[0]?.question ||
              d.research_action?.question ||
              questionDefault,
          );
        }
      })
      .catch(
        (e) =>
          active && activeScope.current === scope && setLoadError(e.message),
      );
    return () => {
      active = false;
    };
  }, [scope]);
  useEffect(() => {
    if (!data?.workspace_reset_at) return;
    const key = "thesis.workspace-reset";
    try {
      if (localStorage.getItem(key) !== data.workspace_reset_at) {
        localStorage.setItem(key, data.workspace_reset_at);
        onWorkspaceReset(data.empty);
      }
    } catch {
      /* Private browsing still supports the empty workspace. */
    }
  }, [data?.workspace_reset_at]);
  const pending = data?.pending_work;
  useEffect(() => {
    if (!data || companyLoading) return;
    const refreshVisible = () => {
      if (!document.hidden)
        refresh().catch((e) => {
          if (activeScope.current === scope) setError(e.message);
        });
    };
    const id = setInterval(refreshVisible, pending ? 700 : 30000);
    window.addEventListener("focus", refreshVisible);
    return () => {
      clearInterval(id);
      window.removeEventListener("focus", refreshVisible);
    };
  }, [pending, !!data, companyLoading, scope, tab]);
  async function act(fn, message) {
    setBusy(true);
    setError("");
    try {
      await fn();
      if (activeScope.current !== scope) return;
      await refresh();
      if (message && activeScope.current === scope) setNotice(message);
    } catch (e) {
      if (activeScope.current !== scope) return;
      setError(e.message);
      await refresh().catch(() => {});
    } finally {
      if (activeScope.current !== scope) return;
      setBusy(false);
      api
        .modelStatus()
        .then((value) => activeScope.current === scope && setModelStatus(value))
        .catch(() => setModelStatus(null));
    }
  }
  if (!data)
    return (
      <div
        data-view={view}
        data-companies-hidden={!!layout.companiesHidden}
        data-idea-hidden={ideaSidebarHidden}
        className={`app-shell${view === "updates" ? " inbox-view" : ""}${view === "ideas" ? " ideas-view" : ""}${!selectedCompanyId ? " all-companies-view" : ""}`}
      >
        <header className="topbar">
          <a className="brand" href="#workspace">
            fledge<span>↗</span>
          </a>
          <nav aria-label="Workspace navigation">
            {[
              ["workspace", "Workspace"],
              ["ideas", "My ideas"],
              ["updates", "Updates"],
            ].map(([key, label]) => (
              <button
                key={key}
                className={view === key ? "active" : ""}
                aria-current={
                  view === key || (view === "idea" && key === "ideas")
                    ? "page"
                    : undefined
                }
                onClick={() => setView(key)}
              >
                {label}
              </button>
            ))}
          </nav>
          <div className="topbar-tools">
            <TelegramSettings />
            {signOut}
          </div>
        </header>
        <div className="workspace-grid">
          <CompanySidebar
            loading
            collapsed={!!layout.companiesHidden}
            onToggle={() => toggleLayout("companiesHidden")}
          />
          <main className="main-workspace" id="workspace">
            {loadError ? (
              <div className="workspace-load-error" role="alert">
                <h2>Research could not be loaded</h2>
                <p>{loadError}</p>
                <button onClick={retryWorkspace}>Try again</button>
                <button onClick={() => onChoose("")}>Open all companies</button>
              </div>
            ) : (
              <LoadingSkeleton
                variant={view === "workspace" ? "workspace" : "cards"}
              />
            )}
          </main>
          <WorkspaceSidebar
            id="idea-sidebar"
            className="idea-panel"
            aria-label="Current idea"
            hidden={ideaSidebarHidden}
          >
            <LoadingSkeleton rows={2} label="Loading saved idea…" />
          </WorkspaceSidebar>
        </div>
      </div>
    );
  if (data.empty)
    return (
      <EmptyWorkspace
        view={view}
        onChoose={(...args) => {
          if (activeScope.current === scope) onChoose(...args);
        }}
      />
    );
  const visibleCompanies = data.catalogue.filter(
    (company) => !hiddenCompanies.includes(company.id),
  );
  const hiddenCatalogue = data.catalogue.filter((company) =>
    hiddenCompanies.includes(company.id),
  );
  function removeCompany(company) {
    onHideCompany(company.id);
    setRemovedCompany(company);
  }
  const displayInstrument = companyLoading
    ? data.catalogue.find((company) => company.id === instrumentId) || {
        name: "Company research",
        symbol: "",
        sector: "",
      }
    : data.instrument;
  const isRecorded = displayInstrument.mode === "recorded";
  const filing = data.filing_calculations?.find(
    (f) =>
      f.document_version_id ===
      (data.active_document_id || data.documents.at(-1)?.id),
  );
  const displayNumber = (value) =>
    Number(value).toLocaleString("en-GB", { maximumFractionDigits: 2 });
  const current = data.versions[0],
    evaluation = current?.evaluations[0],
    allEvals = data.versions.flatMap((v) =>
      v.evaluations.map((e) => ({ ...e, version: v })),
    );
  const latest = (metric) =>
    data.fundamentals?.find((f) => f.metric === metric) || {
      metric,
      value: null,
      period: data.demo.period,
      status: "unavailable",
      reason: "No compatible observation",
      document_version_id: null,
    };
  const doc = (id) => data.documents.find((d) => d.id === id);
  const openSource = (id) => {
    const found =
      doc(id) ||
      data.sentiment?.sources?.find((s) => s.id === id) ||
      data.sentiment_inputs?.sources?.find((s) => s.id === id);
    if (found) setSource(found);
  };
  const openEditor = () => {
    setProposalIds([]);
    setProposalStale(false);
    setEditor(formFor(current, question));
    setApproved(false);
    setFormError("");
    setConflict(null);
  };
  async function save(status) {
    if (conflict) {
      setFormError("Resolve the saved-versus-draft comparison before saving.");
      return;
    }
    setBusy(true);
    setFormError("");
    try {
      const draft =
        status === "draft" && !proposalIds.length
          ? {
              ...editor,
              conditions: editor.conditions.filter(
                (c) => String(c.value ?? "").trim() !== "",
              ),
            }
          : editor;
      const definition = {
        ...revisionPayload(draft, status),
        instrument_id: instrumentId,
      };
      if (proposalIds.length)
        await api.approveSuggestions(proposalIds, definition);
      else await api.save(definition, instrumentId);
      if (activeScope.current !== scope) return;
      await refresh();
      if (activeScope.current !== scope) return;
      setEditor(null);
      setNotice(
        status === "monitoring"
          ? isRecorded
            ? "Your monitoring definition is saved. Checking the recorded evidence."
            : "Your monitoring definition is saved. Checking the available filing evidence."
          : status === "archived"
            ? "Idea archived. Monitoring is off; your history is preserved."
            : "Draft saved. Monitoring is off.",
      );
    } catch (e) {
      if (activeScope.current !== scope) return;
      setFormError(e.message);
      if (e.status === 409) {
        setApproved(false);
        if (proposalIds.length) {
          setProposalStale(true);
          await refresh().catch(() => {});
          return;
        }
        try {
          const next = await refresh();
          if (activeScope.current === scope) setConflict(next.versions[0]);
        } catch (refreshError) {
          if (activeScope.current === scope) setFormError(refreshError.message);
        }
      }
    } finally {
      if (activeScope.current === scope) setBusy(false);
    }
  }
  const newUpdates = data.changes.some(
    (c) => c.evaluation_id === evaluation?.id && !c.review_action,
  );
  const latestChange = data.changes.find(
    (c) => c.evaluation_id === evaluation?.id,
  );
  const checkingCurrent = data.jobs.some(
    (j) =>
      j.version_id === current?.id && ["pending", "running"].includes(j.status),
  );
  const brief = data.briefs[question] || data.briefs[questionDefault];
  function eventPanel(
    version,
    evaluation = null,
    savedReview = null,
    historical = false,
  ) {
    const snapshot = evaluation?.manifest.snapshot_id || data.snapshot_id;
    const review =
      savedReview ||
      version.event_reviews?.find((r) =>
        evaluation
          ? r.id === evaluation.manifest.event_review_id
          : r.snapshot_id === snapshot && r.applied_to_monitoring !== false,
      );
    return (
      <EventAssessment
        key={version.id}
        version={version}
        evaluation={evaluation}
        review={review}
        documents={data.documents}
        onSource={openSource}
        busy={busy}
        onCheck={
          !historical &&
          version.id === current?.id &&
          (!review || version.events?.some((e) => e.repeat_months))
            ? (periods) =>
                act(
                  () => api.checkEvents(version.id, snapshot, periods),
                  "Event evidence check saved. Current monitoring uses only its matching window; earlier-window checks are in History.",
                )
            : undefined
        }
        unavailableReason={
          modelAvailability(modelStatus, "comparison_enabled").message || null
        }
      />
    );
  }
  function resultsPanel(e, v, history = false, compact = false) {
    const linkedChange = data.changes.find((c) => c.evaluation_id === e.id);
    const previous = linkedChange
      ? v.evaluations.find(
          (other) => other.id === linkedChange.previous_evaluation_id,
        )
      : v.evaluations[
          v.evaluations.findIndex((other) => other.id === e.id) + 1
        ];
    return (
      <>
        <IdeaEvidenceReview
          evaluation={e}
          previous={previous}
          version={v}
          documents={data.documents}
          change={linkedChange}
          onSource={openSource}
          review={v.evidence_reviews?.find((r) => r.evaluation_id === e.id)}
          onCompare={
            !e.manifest.snapshot_id
              ? undefined
              : () =>
                  act(
                    () =>
                      api.compareEvidence(v.id, e.manifest.snapshot_id, e.id),
                    "Evidence comparison saved for this revision.",
                  )
          }
          busy={busy}
          error={error}
          unavailableReason={
            modelAvailability(modelStatus, "comparison_enabled").message || null
          }
          compact={compact}
          showReasoning={!history}
          onOpen={() => onChoose(instrumentId, "history", e.id)}
        />
        {!compact && eventPanel(v, e, null, history)}
        <p className="numeric-scope-note">
          {v.events?.length ? (
            <>
              <strong>Monitoring assessment</strong> · Checks your approved
              conditions. Event interpretations and numerical results remain
              separate; neither establishes your investment reasoning.
            </>
          ) : (
            <>
              <strong>Numerical conditions</strong> · These results check your
              selected figures, not your written reasoning.
            </>
          )}
        </p>
        <div className="assessment-heading">
          <span className={`status ${e.outcome}`}>
            {e.outcome === "met"
              ? v.conditions.some((c) => c.role === "risk")
                ? "Requirements met; no selected risk flags"
                : "All conditions met"
              : e.outcome === "not_met"
                ? "Your idea needs a review"
                : "Evidence is incomplete"}
          </span>
          <small>
            {v.conditions.length ? e.manifest.period : "Event criteria"}
          </small>
        </div>
        {e.freshness === "stale" && (
          <div className="warning">
            Sources unavailable or too old at this assessment. These are the
            last recorded figures; newer evidence may be missing.
          </div>
        )}
        {e.freshness === "unknown" && (
          <div className="warning">
            Coverage is not confirmed at this assessment. At least one expected
            source has no successful check.
          </div>
        )}
        {e.disagreement && (
          <div className="warning">
            Sources disagree. Conflicting observations stay unknown.
          </div>
        )}
        {e.results.map((r) => {
          const age = Array.isArray(e.manifest.expiry)
            ? e.manifest.expiry.find((a) => a.condition_id === r.condition_id)
            : null;
          const observation = data.observations.find(
              (o) => o.id === r.observation_id,
            ),
            prev = previous?.results.find(
              (p) => p.condition_id === r.condition_id,
            );
          return (
            <div className="condition-result" key={r.condition_id}>
              <div className="row">
                <strong>
                  {roleLabel(r)} · {metrics[r.metric]}
                </strong>
                <span className={`result-icon ${r.outcome}`}>
                  {r.outcome === "met"
                    ? "✓"
                    : r.outcome === "not_met"
                      ? "↘"
                      : "?"}
                </span>
              </div>
              {!r.withheld && (
                <ReportExpectationText
                  condition={r}
                  state={e.manifest.report_expectations?.find(
                    (a) => a.condition_id === r.condition_id,
                  )}
                />
              )}
              {age?.state === "expired" && (
                <p className="attention">
                  Last reported · outside your age limit
                </p>
              )}
              <div className="condition-values">
                <b>
                  {r.observed_value == null
                    ? "—"
                    : `${displayNumber(r.observed_value)}%`}
                </b>
                <span>
                  {r.operator === ">=" ? "at least" : "at most"} {r.threshold}%
                </span>
              </div>
              {prev && (
                <small>
                  Previously{" "}
                  {prev.observed_value == null
                    ? "unknown"
                    : displayNumber(prev.observed_value)}
                  {prev.observed_value != null ? "%" : ""} ·{" "}
                  {previous.manifest.period}
                </small>
              )}
              <p className="fine">
                {ageLabel(r)}
                {age?.expires_at
                  ? ` · ${age.state === "expired" ? "Expired" : "Expires"} ${age.expires_at.slice(0, 10)} at 00:00 UTC`
                  : ""}
              </p>
              {(r.outcome === "unknown" || r.role === "risk") && (
                <p className="fine">{r.explanation}</p>
              )}
              <div className="row">
                <small>
                  {age?.state === "expired"
                    ? "Too old to assess"
                    : resultLabel(r)}{" "}
                  · {r.period_type === "annual" ? "annual" : "quarterly"}
                </small>
                {observation && (
                  <button
                    className="text-button"
                    onClick={() => openSource(observation.document_version_id)}
                  >
                    Source <Icon name="source" width="12" />
                  </button>
                )}
              </div>
            </div>
          );
        })}
        <p className="fine">
          {v.conditions.length > 0 &&
            "Reported figures within each condition’s annual or quarterly scope. Display values are rounded. "}
          Conditions describe your research criteria, not an investment
          recommendation.
        </p>
        <div className="review-actions">
          {e.review_action ? (
            <span className="reviewed">
              <Icon name="check" />{" "}
              {e.review_action === "reviewed"
                ? "Marked reviewed"
                : "Left unresolved"}{" "}
              · {date(e.reviewed_at)}
            </span>
          ) : (
            <>
              <button
                className="secondary"
                disabled={busy}
                onClick={() =>
                  act(
                    () => api.review(e.id, "reviewed"),
                    "Review recorded. The assessment is unchanged.",
                  )
                }
              >
                <Icon name="check" /> Mark reviewed
              </button>
              <button
                className="text-button"
                disabled={busy}
                onClick={() =>
                  act(
                    () => api.review(e.id, "unresolved"),
                    "Recorded as unresolved.",
                  )
                }
              >
                Leave unresolved
              </button>
            </>
          )}
        </div>
        <small className="fine">
          Reviewing records your attention; it does not endorse the idea.
        </small>
        {history && (
          <details className="audit">
            <summary>Evidence available at this assessment</summary>
            <p>
              Source cutoff: {date(e.manifest.cutoff)} · Assessed:{" "}
              {e.manifest.assessed_at || e.manifest.cutoff} · {e.manifest.mode}
            </p>
            {e.manifest.document_ids.map((id) => (
              <button
                className="source-link"
                key={id}
                onClick={() => openSource(id)}
              >
                {doc(id)?.title || "Source unavailable"}{" "}
                <Icon name="source" width="12" />
              </button>
            ))}
            <small>
              {e.manifest.document_ids.length} source versions ·{" "}
              {e.manifest.observation_ids.length} observations ·{" "}
              {e.manifest.evaluator}
            </small>
          </details>
        )}
      </>
    );
  }
  function renderFinancialReports() {
    return (
      <div className="financial-reports-panel">
        {" "}
        {!isRecorded && (
          <details className="financials-reported-details">
            <summary>All reported figures</summary>
            <FinancialPerformance
              key={data.instrument.id}
              data={data.performance}
            />
          </details>
        )}
        {!isRecorded && (
          <h3 className="financials-sources-heading">Filings &amp; checks</h3>
        )}
        {!isRecorded && (
          <OriginalFilings
            key={`original-${data.instrument.id}`}
            instrumentId={data.instrument.id}
            data={data.disclosures}
            busy={busy}
            onRefresh={() =>
              act(
                () => api.refreshDisclosures(data.instrument.id),
                "Original company documents checked.",
              )
            }
          />
        )}
        {!isRecorded && (
          <FilingWatch
            key={`watch-${data.instrument.id}`}
            instrumentId={data.instrument.id}
            watch={data.filing_watch}
            configured={data.sec_status?.configured}
            busy={busy}
            onChange={(enabled) =>
              act(
                () => api.filingWatch(data.instrument.id, enabled),
                enabled
                  ? "Daily filing checks enabled. The first check is queued."
                  : "Future filing checks stopped. An active check may finish.",
              )
            }
          />
        )}
        {!isRecorded && (
          <h3 className="monitoring-inputs-heading">
            Current monitoring inputs
          </h3>
        )}
        <div className="metrics-table">
          <div className="table-heading">
            <span>REPORTED METRIC</span>
            <span>LATEST</span>
            <span>PERIOD</span>
          </div>
          {Object.keys(metrics).map((key) => {
            const f = latest(key);
            return (
              <button
                className="metric-row"
                key={key}
                disabled={!f.document_version_id}
                onClick={() =>
                  f.document_version_id && openSource(f.document_version_id)
                }
              >
                <span>
                  {metrics[key]}
                  {f.reason && <small>{f.reason}</small>}
                  <small>
                    {key === "revenue_growth"
                      ? "Revenue change versus the comparable period last year"
                      : "Operating income as a share of revenue"}
                  </small>
                </span>
                <strong>
                  {f.value == null ? "—" : `${displayNumber(f.value)}%`}
                </strong>
                <span>
                  {f.period}{" "}
                  {f.document_version_id && <Icon name="source" width="12" />}
                </span>
              </button>
            );
          })}
        </div>
        <FilingDetails filing={filing} />
        <div className="unknown-row">
          <span>i</span>
          <p>
            {data.demo.period_type === "annual"
              ? "These metrics use an annual reporting period."
              : "These metrics use a quarterly reporting period."}{" "}
            Growth and margin use reported inputs; SEC ratios are calculated in
            the app. Guidance is an expectation, not an observed result. Read
            forecasts separately in Outlook.
          </p>
        </div>
      </div>
    );
  }
  function renderIdeaHistory() {
    return (
      <>
        <HistoryPanel
          key={initialEvaluation || "history"}
          onIdeas={() => setView("ideas")}
          hasChecks={
            !!data.idea_alerts?.some(
              (check) => check.instrument_id === instrumentId,
            )
          }
          versions={data.versions}
          initialRecord={
            initialEvaluation === "history" ? null : initialEvaluation
          }
          renderEvaluation={resultsPanel}
          renderEventReview={(review, version) =>
            eventPanel(version, null, review, true)
          }
          renderComparison={(review, version) => (
            <IdeaEvidenceReview
              evaluation={{
                id: review.evaluation_id,
                manifest: {
                  snapshot_id: review.snapshot_id,
                  document_ids: review.source_ids,
                  cutoff: review.cutoff,
                },
              }}
              version={version}
              documents={data.documents}
              onSource={openSource}
              review={review}
              savedComparison
              showReasoning={false}
            />
          )}
        />
        <IdeaAlertChecks
          checks={data.idea_alerts}
          instrumentId={instrumentId}
          hideEmpty
          history
          busy={busy}
          onSource={setSource}
          onOpen={onChoose}
          onReview={(id, action) =>
            act(
              () => api.reviewIdeaAlert(id, action),
              "Private alert review recorded.",
            )
          }
        />
      </>
    );
  }
  return (
    <div
      data-view={view}
      data-companies-hidden={!!layout.companiesHidden}
      data-idea-hidden={ideaSidebarHidden}
      className={`app-shell${view === "updates" ? " inbox-view" : ""}${view === "ideas" ? " ideas-view" : ""}${!selectedCompanyId ? " all-companies-view" : ""}`}
    >
      <header className="topbar">
        <a
          href="#workspace"
          className="brand"
          onClick={(e) => {
            e.preventDefault();
            setView("workspace");
          }}
        >
          fledge<span>↗</span>
        </a>
        <nav aria-label="Workspace navigation">
          {[
            ["workspace", "Workspace"],
            ["ideas", "My ideas"],
            ["updates", "Updates"],
          ].map(([key, label]) => (
            <button
              key={key}
              className={
                view === key ||
                (view === "idea" && key === "ideas") ||
                (view === "review" && key === "updates")
                  ? "active"
                  : ""
              }
              aria-current={
                view === key || (view === "idea" && key === "ideas")
                  ? "page"
                  : undefined
              }
              onClick={() => setView(key)}
            >
              {label}
              {key === "updates" &&
                (data.review_schedule?.unseen_count > 0 ||
                  data.changes.some((c) => !c.review_action) ||
                  data.research_alerts?.some((a) => !a.review_action) ||
                  data.idea_alerts?.some(
                    (a) => a.published && !a.review_action,
                  )) && <i className="dot" />}
            </button>
          ))}
        </nav>
        <div className="topbar-tools">
          <TelegramSettings />
          {signOut}
        </div>
      </header>
      <RemovalNotice
        company={removedCompany}
        onUndo={() => {
          if (!removedCompany) return;
          onRestoreCompany(removedCompany.id);
          setRemovedCompany(null);
        }}
        onDismiss={() => setRemovedCompany(null)}
      />
      {!companyLoading && isRecorded && selectedCompanyId && (
        <div className="demo-bar">
          <div>
            <span className="demo-tag">FICTIONAL DEMO</span>
            <span>{data.demo.label}</span>
            <span className="muted">{date(data.demo.as_of)}</span>
          </div>
          <button
            disabled={busy || data.demo.complete}
            onClick={() =>
              act(
                () => api.advance(data.demo.stage, instrumentId),
                "Recorded development loaded.",
              )
            }
            aria-label="Load next recorded development"
          >
            {data.demo.complete ? "Scenario complete" : "Next development"}{" "}
            <Icon name="arrow" width="16" />
          </button>
        </div>
      )}
      {error && !companyLoading && (
        <div className="global-message error" role="alert">
          {error}
          <button onClick={() => act(refresh, "Workspace refreshed.")}>
            Refresh
          </button>
        </div>
      )}
      {notice && !companyLoading && (
        <div className="global-message" role="status">
          {notice}
          <button aria-label="Dismiss update" onClick={() => setNotice("")}>
            ×
          </button>
        </div>
      )}
      <label className="mobile-company-picker">
        Company
        <Select
          aria-label="Company"
          value={selectedCompanyId}
          disabled={busy}
          onChange={(e) => chooseCompany(e.target.value)}
        >
          <option value="">All companies</option>
          {selectedCompanyId && hiddenCompanies.includes(selectedCompanyId) && (
            <option value={instrumentId}>
              {displayInstrument.symbol} · open research
            </option>
          )}
          {visibleCompanies.map((c) => (
            <option key={c.id} value={c.id}>
              {c.symbol} · {companyName(c)}
            </option>
          ))}
        </Select>
        <CompanyAddButton
          className="mobile-add-company"
          onClick={() => setAddingCompany(true)}
        />
      </label>
      <div className="workspace-grid">
        <CompanySidebar
          companies={visibleCompanies}
          selectedCompanyId={selectedCompanyId}
          collapsed={!!layout.companiesHidden}
          onToggle={() => toggleLayout("companiesHidden")}
          search={companySearch}
          onSearch={setCompanySearch}
          onChoose={chooseCompany}
          onRemove={removeCompany}
          onAdd={() => setAddingCompany(true)}
          busy={busy}
        />
        <main
          className="main-workspace"
          id="workspace"
          ref={mainPane}
          aria-label="Company research"
          aria-busy={companyLoading && !loadError}
          tabIndex={0}
        >
          <header className="company-header">
            <CompanyAvatar company={displayInstrument} />
            <div>
              <div className="row">
                <h1 title={displayInstrument.name}>
                  {companyName(displayInstrument)}
                </h1>
                <span className="ticker">{displayInstrument.symbol}</span>
              </div>
              <p>
                {isRecorded
                  ? "Fictional company"
                  : displayInstrument.sector &&
                      displayInstrument.sector !== "Not yet classified"
                    ? displayInstrument.sector
                    : "Company research"}
              </p>
            </div>
            {!companyLoading && !isRecorded && (
              <MarketQuote
                market={data.market}
                history={priceRead?.data}
                compact
              />
            )}
            <div className="company-actions">
              {view === "workspace" && (
                <button
                  className="primary"
                  disabled={companyLoading}
                  onClick={() => setResearchOpen(true)}
                  aria-label="Ask a question"
                  title="Ask a question"
                >
                  <span className="company-action-icon">
                    <Icon name="idea" />
                  </span>
                  <span className="company-action-label">Ask a question</span>
                </button>
              )}
              <button
                className="quick-save"
                disabled={companyLoading}
                onClick={() => setSourcesOpen(true)}
                aria-label="Data & sources"
                title="Data & sources"
              >
                <span className="company-action-icon">
                  <Icon name="source" />
                </span>
                <span className="company-action-label">Data &amp; sources</span>
              </button>
              {!isRecorded && (
                <button
                  className="research-updates-trigger"
                  disabled={companyLoading}
                  onClick={() => setUpdatesOpen(true)}
                  aria-label="Research updates"
                  title={
                    loadingRun?.active
                      ? "Research updates · working"
                      : "Research updates"
                  }
                  aria-haspopup="dialog"
                >
                  <Icon name="pulse" />
                  <span className="company-action-label company-action-full">
                    Research updates
                  </span>
                  <span className="company-action-short">Status</span>
                  {loadingRun?.active && (
                    <span className="research-updates-dot" aria-hidden="true" />
                  )}
                </button>
              )}
            </div>
          </header>
          {companyLoading ? (
            loadError ? (
              <div className="workspace-load-error" role="alert">
                <h2>Research could not be loaded</h2>
                <p>{loadError}</p>
                <button onClick={retryWorkspace}>Try again</button>
              </div>
            ) : (
              <LoadingSkeleton
                variant={view === "workspace" ? "workspace" : "cards"}
                label={`Loading ${displayInstrument.symbol || "company"} research…`}
              />
            )
          ) : (
            <>
              <RetainedView
                active={!!selectedCompanyId && view === "workspace"}
              >
                <>
                  <div className="research-browser">
                    <ResearchNavigation
                      selected={tab}
                      onChange={setTab}
                      recorded={isRecorded}
                    />
                    <section
                      className="research-content"
                      role="tabpanel"
                      id="research-panel"
                      aria-labelledby={`research-tab-${tab}`}
                    >
                      <ResearchSectionHeader
                        selected={tab}
                      ></ResearchSectionHeader>
                      <ExplorationPrompt
                        question={
                          exploration?.section === tab ? exploration : null
                        }
                        recorded={isRecorded}
                        onDone={() => setExploration(null)}
                        onReasoning={() => {
                          openEditor();
                          if (!current)
                            setEditor({
                              ...formFor(null, exploration.question),
                              question: exploration.question,
                            });
                        }}
                      />
                      <RetainedView active={tab === "evidence"}>
                        <>
                          {!isRecorded && (
                            <MarketResearch
                              question={question}
                              data={data}
                              busy={busy}
                              modelStatus={modelStatus}
                              onSource={openSource}
                              onGenerate={() =>
                                act(
                                  () => api.marketBrief(instrumentId),
                                  "Your source-linked briefing is ready.",
                                )
                              }
                            />
                          )}

                          {isRecorded && (
                            <details className="research-context" open>
                              <summary>Research context</summary>
                              <div className="radar-intro">
                                <span className="section-label">
                                  THE STORY SO FAR
                                </span>
                                <p>{brief.text}</p>
                                <div className="brief-citations">
                                  {brief.evidence_ids.map((id, i) => (
                                    <button
                                      key={id}
                                      className="source-link"
                                      onClick={() => openSource(id)}
                                    >
                                      Source {i + 1} ↗
                                    </button>
                                  ))}
                                </div>
                                <details className="brief-unknowns">
                                  <summary>
                                    What these sources cannot establish
                                  </summary>
                                  <ul>
                                    {brief.unknowns.map((text) => (
                                      <li key={text}>{text}</li>
                                    ))}
                                  </ul>
                                </details>
                              </div>
                            </details>
                          )}
                          {!isRecorded && (
                            <SentimentPanel
                              key={instrumentId}
                              onThemeSource={setSource}
                              onThemesChange={async () => {
                                const status = await api.modelStatus();
                                if (activeScope.current === scope)
                                  setModelStatus(status);
                              }}
                              onCoverage={() => setSourcesOpen(true)}
                              data={data}
                              busy={busy}
                              modelStatus={modelStatus}
                              onSource={openSource}
                              onCheckIdea={(purpose) =>
                                act(
                                  () =>
                                    api.ideaAlertCheck(
                                      instrumentId,
                                      data.sentiment.id,
                                      current.id,
                                      purpose,
                                    ),
                                  "Check saved in History. Potential connections also appear in Updates.",
                                )
                              }
                              loadingRun={loadingRun}
                              onAnalyze={(days) =>
                                startLoading({
                                  analyze: true,
                                  lookback_days: days,
                                })
                              }
                              onWatch={(
                                enabled,
                                interval,
                                matchIdea,
                                includeContext,
                                ideaPurpose,
                              ) =>
                                act(
                                  () =>
                                    api.newsWatch(
                                      instrumentId,
                                      enabled,
                                      interval,
                                      matchIdea,
                                      includeContext,
                                      ideaPurpose,
                                    ),
                                  enabled
                                    ? "Local news and social watch enabled."
                                    : "Future scheduled checks stopped.",
                                )
                              }
                              onEventWatch={(versionId) =>
                                act(
                                  () => api.eventWatch(instrumentId, versionId),
                                  versionId
                                    ? "Event checks enabled for this approved revision at scheduled news checks."
                                    : "Automatic event checks stopped.",
                                )
                              }
                            />
                          )}
                          {!isRecorded && (
                            <MarketResearch
                              headlinesOnly
                              data={data}
                              onSource={openSource}
                            />
                          )}
                          {isRecorded && (
                            <section
                              className="passage-selection"
                              aria-label="Source passage brief"
                            >
                              <div className="row">
                                <span className="section-label">
                                  ACROSS THE SOURCES
                                </span>
                                {!data.selected_passages &&
                                  data.documents.length > 0 &&
                                  modelStatus?.enabled &&
                                  isRecorded && (
                                    <button
                                      disabled={
                                        busy ||
                                        modelStatus.budget.unresolved > 0
                                      }
                                      onClick={() =>
                                        act(
                                          () =>
                                            api.selectPassages(
                                              data.demo.stage,
                                              instrumentId,
                                            ),
                                          "Source passages are ready.",
                                        )
                                      }
                                    >
                                      {busy
                                        ? "Reading sources…"
                                        : "Select key passages"}
                                    </button>
                                  )}
                              </div>
                              {data.selected_passages ? (
                                <>
                                  <p className="fine">
                                    {data.selected_passages.limitation}
                                    {data.selected_passages
                                      .omitted_passage_count > 0 &&
                                      ` ${data.selected_passages.omitted_passage_count} source passages were not selected; review the full sources below.`}
                                  </p>
                                  <ul>
                                    {data.selected_passages.passages.map(
                                      (p) => (
                                        <li key={p.id}>
                                          <blockquote>{p.quote}</blockquote>
                                          <button
                                            className="source-link"
                                            onClick={() =>
                                              openSource(p.document_id)
                                            }
                                          >
                                            {p.source} · {date(p.published_at)}{" "}
                                            ↗
                                          </button>
                                        </li>
                                      ),
                                    )}
                                  </ul>
                                </>
                              ) : (
                                <p className="fine">
                                  {data.documents.length === 0
                                    ? "No permitted source passages available."
                                    : modelStatus?.budget.unresolved > 0
                                      ? modelAvailability(modelStatus).message
                                      : isRecorded
                                        ? "Read original evidence below. Optional AI selection highlights passages without changing your conditions or assessments."
                                        : "This workspace contains structured financial data. Use the calculation trail to inspect inputs and open the original filing. News and management guidance are not connected yet."}
                                </p>
                              )}
                            </section>
                          )}
                          <div className="evidence-grid">
                            {data.claims
                              .filter(
                                (c) =>
                                  !data.documents.some(
                                    (d) =>
                                      d.supersedes_id === c.document_version_id,
                                  ),
                              )
                              .filter(
                                (c) =>
                                  c.kind !== "reported" ||
                                  data.observations.some(
                                    (o) =>
                                      (
                                        c.source_version_ids || [
                                          c.document_version_id,
                                        ]
                                      ).includes(o.document_version_id) &&
                                      o.period === data.demo.period,
                                  ),
                              )
                              .slice(0, 4)
                              .map((c) => (
                                <article
                                  className={`evidence-card ${c.stance}`}
                                  key={c.id}
                                >
                                  <div className="row">
                                    <span className="stance">
                                      {c.stance === "support"
                                        ? "↗ Supports"
                                        : c.stance === "challenge"
                                          ? "↘ Challenges"
                                          : "◌ Open question"}
                                    </span>
                                    <small>{date(c.available_at)}</small>
                                  </div>
                                  <h3>{c.title}</h3>
                                  <p>{c.body}</p>
                                  <footer>
                                    <span>
                                      {c.kind === "guidance"
                                        ? "Management guidance"
                                        : c.kind === "reported"
                                          ? "Reported fact"
                                          : "Unconfirmed report"}
                                    </span>
                                    <button
                                      className="text-button"
                                      onClick={() =>
                                        openSource(c.document_version_id)
                                      }
                                    >
                                      Read source{" "}
                                      <Icon name="source" width="12" />
                                    </button>
                                  </footer>
                                  {c.source_version_ids?.length > 1 && (
                                    <details className="source-provenance">
                                      <summary>
                                        {c.source_version_ids.length} source
                                        versions · {c.origin_keys.length}{" "}
                                        declared origin
                                        {c.origin_keys.length === 1 ? "" : "s"}
                                      </summary>
                                      <p className="fine">
                                        Copied coverage is grouped; it is not
                                        independent confirmation.
                                      </p>
                                      {c.source_version_ids.map((id) => (
                                        <button
                                          key={id}
                                          className="source-link"
                                          onClick={() => openSource(id)}
                                        >
                                          {doc(id)?.source} · {doc(id)?.title}{" "}
                                          ↗
                                        </button>
                                      ))}
                                    </details>
                                  )}
                                </article>
                              ))}
                          </div>
                          <div className="unknown-row">
                            <span>?</span>
                            <div>
                              <strong>What we still don’t know</strong>
                              <p>{brief.unknowns.join(" ")}</p>
                            </div>
                          </div>
                        </>
                      </RetainedView>
                      <RetainedView active={tab === "expectations"}>
                        <Suspense
                          fallback={<p role="status">Loading outlook…</p>}
                        >
                          <OutlookPage
                            key={instrumentId}
                            management={data.management_outlook}
                            includeForecasts={!isRecorded}
                            instrumentId={instrumentId}
                            visible={
                              view === "workspace" && tab === "expectations"
                            }
                            initialRead={
                              panelRead?.tab === "expectations"
                                ? panelRead
                                : null
                            }
                            enabled={modelStatus?.briefing_enabled}
                            onSource={setSource}
                            onView={setTab}
                            onDraft={(q) => {
                              openEditor();
                              setEditor({
                                ...formFor(current, q),
                                question: q,
                              });
                            }}
                          />
                        </Suspense>
                      </RetainedView>
                      {isRecorded && (
                        <RetainedView active={tab === "business"}>
                          <div className="overview-welcome">
                            <details className="company-chart-disclosure">
                              <summary>Price chart · fictional sample</summary>
                              <PriceChart prices={data.prices} />
                            </details>
                            <h3>{data.instrument.name}</h3>
                            <p>{brief.text}</p>
                            <p>
                              This is a fictional research scenario. Explore its
                              reported figures and recorded news before saving
                              your view.
                            </p>
                            <button onClick={() => setTab("evidence")}>
                              Read news &amp; discussion
                            </button>
                          </div>
                        </RetainedView>
                      )}
                      {!isRecorded && (
                        <RetainedView active={tab === "business"}>
                          <>
                            <CompanySnapshot
                              key={`snapshot-${instrumentId}`}
                              visible={
                                view === "workspace" && tab === "business"
                              }
                              onSource={setSource}
                              focusTopic={
                                exploration?.topic ? exploration : null
                              }
                              businessPanel={
                                <BusinessPanel
                                  key={`business-${instrumentId}`}
                                  instrumentId={instrumentId}
                                  focusTopic={
                                    exploration?.topic ? exploration : null
                                  }
                                  visible={
                                    view === "workspace" && tab === "business"
                                  }
                                  disclosures={data.disclosures}
                                  modelStatus={modelStatus}
                                  onRefresh={() =>
                                    act(
                                      () =>
                                        api.refreshDisclosures(instrumentId),
                                      "Original company documents checked.",
                                    )
                                  }
                                  onDraft={(q) => {
                                    openEditor();
                                    setEditor({
                                      ...formFor(current, q),
                                      question: q,
                                    });
                                  }}
                                />
                              }
                              data={data}
                              instrumentId={instrumentId}
                              onView={(next, destination) => {
                                setTab(next);
                                if (destination === "scenario")
                                  requestAnimationFrame(() => {
                                    const panel =
                                      document.querySelector(
                                        ".valuation-panel",
                                      );
                                    panel?.setAttribute("tabindex", "-1");
                                    panel?.focus({ preventScroll: true });
                                    panel?.scrollIntoView({
                                      block: "start",
                                      behavior: "instant",
                                    });
                                  });
                              }}
                              onUpdates={() => setView("updates")}
                              chart={
                                <details
                                  className="company-chart-disclosure"
                                  onToggle={(event) =>
                                    setPriceChartOpen(event.currentTarget.open)
                                  }
                                >
                                  <summary>Price chart · past year</summary>
                                  <HistoricalPrices
                                    key={`prices-${instrumentId}`}
                                    instrumentId={instrumentId}
                                    initialRead={priceRead}
                                    visible={
                                      priceChartOpen &&
                                      view === "workspace" &&
                                      tab === "business"
                                    }
                                    onRead={setPriceRead}
                                    loadStep={loadingRun?.steps.find(
                                      (s) => s.key === "prices",
                                    )}
                                  />
                                </details>
                              }
                            />
                          </>
                        </RetainedView>
                      )}
                      <RetainedView active={tab === "valuation"}>
                        <>
                          {!isRecorded && (
                            <Suspense
                              fallback={<p>Loading competitor comparison…</p>}
                            >
                              <SectorPosition
                                instrumentId={instrumentId}
                                visible={
                                  view === "workspace" && tab === "valuation"
                                }
                              />
                            </Suspense>
                          )}
                          <ValuationPanel
                            initialRead={
                              panelRead?.tab === "valuation" ? panelRead : null
                            }
                            visible={
                              view === "workspace" && tab === "valuation"
                            }
                            key={data.instrument.id}
                            instrument={data.instrument}
                            performance={data.performance}
                            quote={data.market?.quote?.quote}
                          />
                          {!isRecorded && (
                            <Suspense fallback={<p>Loading comparisons…</p>}>
                              <FmpPanel
                                key={`peers-${instrumentId}`}
                                mode="ratios"
                                instrumentId={instrumentId}
                                visible={
                                  view === "workspace" && tab === "valuation"
                                }
                              />
                            </Suspense>
                          )}
                        </>
                      </RetainedView>
                      <RetainedView active={tab === "fundamentals"}>
                        <>
                          {isRecorded ? (
                            renderFinancialReports()
                          ) : (
                            <Suspense fallback={<p>Loading financials…</p>}>
                              <FinancialsPage
                                key={`financials-${instrumentId}`}
                                instrumentId={instrumentId}
                                workspace={data}
                                visible={
                                  view === "workspace" && tab === "fundamentals"
                                }
                                onCompare={() => setTab("valuation")}
                              >
                                {renderFinancialReports()}
                              </FinancialsPage>
                            </Suspense>
                          )}
                        </>
                      </RetainedView>
                    </section>
                  </div>
                </>
              </RetainedView>
              <div
                className="workspace-page"
                hidden={view === "workspace" && !!selectedCompanyId}
              >
                <RetainedView active={["ideas", "updates"].includes(view)}>
                  <div className="collection-view">
                    {view === "ideas" && (
                      <IdeasAndChanges
                        mode="ideas"
                        catalogue={data.catalogue.filter(
                          (c) =>
                            !selectedCompanyId || c.id === selectedCompanyId,
                        )}
                        changes={data.changes}
                        onOpen={onChoose}
                        selectedCompany={data.catalogue.find(
                          (c) => c.id === selectedCompanyId,
                        )}
                        onCreate={selectedCompanyId ? openEditor : undefined}
                      />
                    )}
                    <RetainedView active={view === "updates"}>
                      <UpdateInbox
                        onWeeklyReview={() => setView("review")}
                        unseenReviews={data.review_schedule?.unseen_count || 0}
                        active={view === "updates"}
                        filters={inboxFilters}
                        onFiltersChange={onInboxFiltersChange}
                        catalogue={data.catalogue}
                        onOpen={onChoose}
                        onSource={setSource}
                        onReviewed={refresh}
                      />
                    </RetainedView>
                  </div>
                </RetainedView>
                <RetainedView active={!selectedCompanyId && view === "history"}>
                  <>
                    <Suspense
                      fallback={
                        <LoadingSkeleton label="Loading saved histories…" />
                      }
                    >
                      <AllHistory
                        catalogue={data.catalogue}
                        onOpen={onChoose}
                        visible={view === "history"}
                        hasChecks={!!data.idea_alerts?.length}
                      />
                    </Suspense>
                    <IdeaAlertChecks
                      checks={data.idea_alerts}
                      hideEmpty
                      history
                      busy={busy}
                      onSource={setSource}
                      onOpen={onChoose}
                      onReview={(id, action) =>
                        act(
                          () => api.reviewIdeaAlert(id, action),
                          "Private alert review recorded.",
                        )
                      }
                    />
                  </>
                </RetainedView>
                {!selectedCompanyId && ["workspace", "idea"].includes(view) ? (
                  <Suspense
                    fallback={
                      <LoadingSkeleton label="Loading your companies…" />
                    }
                  >
                    <CompanyOverview
                      catalogue={data.catalogue}
                      initialWorkspace={data}
                      onOpen={onChoose}
                    />
                  </Suspense>
                ) : !selectedCompanyId && view === "history" ? null : view ===
                  "workspace" ? null : view === "review" ? (
                  <Suspense
                    fallback={
                      <LoadingSkeleton label="Reading weekly review…" />
                    }
                  >
                    {" "}
                    <ReviewDigest
                      onOpen={onChoose}
                      onSource={setSource}
                      selectedCompanyId={selectedCompanyId}
                      onCompanyChange={chooseCompany}
                    />
                  </Suspense>
                ) : ["ideas", "updates"].includes(view) ? null : view ===
                  "idea" ? (
                  <section className="focus-page reasoning-page">
                    <span className="section-label">YOUR REASONING</span>
                    <h2>
                      {current?.question ||
                        "Give your research somewhere to live."}
                    </h2>
                    {!current && (
                      <p className="reasoning large">
                        Save what you think, what you are unsure about, and what
                        could change your mind. A draft needs no monitoring
                        rules.
                      </p>
                    )}
                    <button className="primary" onClick={openEditor}>
                      {current ? "Edit my idea" : "Save an idea"}{" "}
                      <Icon name="arrow" />
                    </button>
                    <ProposalPanel
                      proposals={data.proposals}
                      current={current}
                      busy={busy}
                      unavailableReason={
                        modelAvailability(modelStatus, "comparison_enabled")
                          .message || null
                      }
                      onGenerate={() =>
                        act(async () => {
                          const result = await api.suggest({
                            instrument_id: instrumentId,
                            snapshot_id: data.snapshot_id,
                            base_version_id: current?.id || null,
                            question,
                          });
                          if (activeScope.current === scope)
                            setNotice(result.explanation);
                        })
                      }
                      onReview={(chosen) => {
                        try {
                          const candidate = combineSuggestions(chosen);
                          setEditor(
                            formFor(
                              {
                                ...candidate,
                                revision: candidate.expected_revision,
                              },
                              candidate.question,
                            ),
                          );
                          setProposalIds(chosen.map((p) => p.id));
                          setProposalStale(false);
                          setApproved(false);
                          setFormError("");
                          setConflict(null);
                        } catch (e) {
                          setError(e.message);
                        }
                      }}
                      onReject={(id) =>
                        act(
                          () => api.rejectSuggestion(id),
                          "Suggestion rejected. Your saved idea is unchanged.",
                        )
                      }
                      onSource={openSource}
                      onOpen={(id) =>
                        onChoose(instrumentId, "history", `revision:${id}`)
                      }
                    />
                    {current && (
                      <>
                        <div className="divider" />
                        <span className="section-label">
                          REVISION {current.revision} ·{" "}
                          {current.status.toUpperCase()}
                        </span>
                        <ReviewDownload
                          version={current}
                          evaluation={evaluation}
                          comparison={current.evidence_reviews?.find((r) =>
                            evaluation
                              ? r.evaluation_id === evaluation.id
                              : r.evaluation_id == null &&
                                r.snapshot_id === data.snapshot_id,
                          )}
                        />
                        {evaluation ? (
                          resultsPanel(evaluation, current)
                        ) : (
                          <>
                            <p className="muted">
                              {checkingCurrent
                                ? "Checking recorded evidence…"
                                : "No active assessment. Save and explicitly approve monitoring when you are ready."}
                            </p>
                            {eventPanel(current)}
                            <IdeaEvidenceReview
                              evaluation={{
                                id: null,
                                manifest: {
                                  snapshot_id: data.snapshot_id,
                                  document_ids: data.documents.map((d) => d.id),
                                  active_document_id: data.active_document_id,
                                  cutoff: data.demo.as_of,
                                },
                              }}
                              version={current}
                              documents={data.documents}
                              onSource={openSource}
                              draft
                              onCompare={() =>
                                act(
                                  () =>
                                    api.compareEvidence(
                                      current.id,
                                      data.snapshot_id,
                                    ),
                                  "Evidence comparison saved for this revision.",
                                )
                              }
                              busy={busy}
                              error={error}
                              unavailableReason={
                                modelAvailability(
                                  modelStatus,
                                  "comparison_enabled",
                                ).message || null
                              }
                              review={current.evidence_reviews?.find(
                                (r) =>
                                  r.evaluation_id == null &&
                                  r.snapshot_id === data.snapshot_id,
                              )}
                            />
                          </>
                        )}
                      </>
                    )}
                    <details
                      className="idea-history"
                      open={!!initialEvaluation}
                      key={initialEvaluation || "idea-history"}
                    >
                      <summary>History · versions and evidence checks</summary>
                      {renderIdeaHistory()}
                    </details>
                  </section>
                ) : (
                  renderIdeaHistory()
                )}
              </div>
            </>
          )}
        </main>
        <Modal
          open={researchOpen && ideaSidebarAvailable}
          onClose={() => setResearchOpen(false)}
          title="Your research"
          className="research-dialog"
          keepMounted
        >
          {!companyLoading && (
            <div className="my-research-content" key={instrumentId}>
              <p className="notebook-intro">
                Questions help you explore {data.instrument.symbol}. Your idea
                is the point of view you choose to save, in your own words.
              </p>
              <CompanionGuide
                key={`${instrumentId}:${selectedCompanyId}:${view}`}
                recorded={isRecorded}
                onExplore={(item) => {
                  setExploration({ ...item, recorded: isRecorded });
                  setTab(item.section);
                  setResearchOpen(false);
                }}
                onNotebook={() => setResearchOpen(true)}
                onReasoning={openEditor}
              />
              {isRecorded ? (
                <QuestionSelector
                  key={scope}
                  instrumentId={instrumentId}
                  company={data.instrument.name}
                  question={question}
                  currentQuestion={current?.question}
                  library={data.question_library}
                  onSaved={(library) => {
                    if (activeScope.current !== scope) return;
                    setData((previous) => ({
                      ...previous,
                      question_library: library,
                    }));
                    setQuestion(library.selected_question);
                  }}
                />
              ) : (
                <ResearchQuestion
                  key={scope}
                  instrumentId={instrumentId}
                  company={data.instrument.name}
                  question={question}
                  currentQuestion={current?.question}
                  library={data.question_library}
                  onSaved={(library) => {
                    if (activeScope.current !== scope) return;
                    setData((previous) => ({
                      ...previous,
                      question_library: library,
                    }));
                    setQuestion(library.selected_question);
                  }}
                  onQuestion={setQuestion}
                  modelStatus={modelStatus}
                  onDone={() =>
                    api
                      .modelStatus()
                      .then(
                        (value) =>
                          activeScope.current === scope &&
                          setModelStatus(value),
                      )
                      .catch(() => {})
                  }
                  onDraft={(q) => {
                    openEditor();
                    setEditor({
                      ...formFor(current, q),
                      question: q,
                    });
                  }}
                />
              )}

              {companyLoading ? (
                loadError ? (
                  <p className="muted">
                    Saved idea unavailable until research loads.
                  </p>
                ) : (
                  <LoadingSkeleton variant="idea" label="Loading saved idea…" />
                )
              ) : (
                <>
                  <section
                    className="idea-card"
                    aria-labelledby="idea-card-title"
                  >
                    <div className="idea-card-head">
                      <h3 id="idea-card-title">Your idea</h3>
                      <span
                        className={`status ${current?.status === "monitoring" ? "met" : ""}`}
                      >
                        {current?.status || "Not saved"}
                      </span>
                    </div>
                    <p className="idea-card-question">
                      {current?.question ||
                        "Turn a question into a point of view."}
                    </p>
                    <p className="reasoning">
                      {current?.reasoning ||
                        "What would need to stay true for this company to be worth a closer look?"}
                    </p>
                    <div className="idea-card-actions">
                      <button
                        className={current ? "secondary" : "primary"}
                        onClick={openEditor}
                      >
                        {current ? "Edit idea" : "Save my reasoning"}
                        <Icon name={current ? "idea" : "plus"} />
                      </button>
                      <button
                        className="text-button"
                        onClick={() => setView("idea")}
                      >
                        Get help defining this idea ↗
                      </button>
                    </div>
                  </section>
                  <section className="monitor-card" aria-label="Monitoring">
                    {evaluation ? (
                      <>
                        <div className="row">
                          <span className="section-label">
                            {checkingCurrent
                              ? "PREVIOUS ASSESSMENT"
                              : newUpdates
                                ? "WHAT CHANGED"
                                : "LATEST ASSESSMENT"}
                          </span>
                          {newUpdates && <span className="new-pill">NEW</span>}
                        </div>
                        <small className="as-of">
                          Assessed{" "}
                          {date(
                            evaluation.manifest.assessed_at ||
                              evaluation.manifest.cutoff,
                          )}{" "}
                          · revision {current.revision}
                        </small>
                        {checkingCurrent && (
                          <p className="checking" role="status">
                            Checking the new evidence… This assessment uses the
                            earlier cutoff above.
                          </p>
                        )}
                        {latestChange && (
                          <p className="change-context">
                            {latestChange.summary}.{" "}
                            {latestChange.kind === "evidence"
                              ? "Review the source alongside your reasoning; numerical conditions may be unchanged."
                              : ""}
                          </p>
                        )}
                        {resultsPanel(evaluation, current, false, true)}
                      </>
                    ) : (
                      <div className="empty-monitor">
                        <h3>
                          {checkingCurrent
                            ? "Checking the evidence"
                            : "Follow the evidence"}
                        </h3>
                        <p>
                          {current?.status === "draft"
                            ? "Your draft is saved. Add a condition and approve it whenever you are ready."
                            : "Choose the figures that matter to your idea. We’ll show what changes and keep your original reasoning beside it."}
                        </p>
                      </div>
                    )}
                    {data.jobs.some(
                      (j) =>
                        j.status === "failed" && j.version_id === current?.id,
                    ) && (
                      <p role="alert" className="warning">
                        Assessment unavailable. Your saved idea is intact. Edit
                        and save a new revision to check again.
                      </p>
                    )}
                    <details className="secondary-details monitoring-details">
                      <summary>Monitoring details</summary>
                      <p className="fine">
                        {isRecorded
                          ? "Age is assessed at the recorded sample date."
                          : "Reporting age is checked against the current UTC date. This does not fetch new filings."}
                      </p>
                      {!isRecorded && (
                        <p className="fine">
                          {data.filing_watch?.enabled
                            ? "Daily filing checks are enabled while this app runs."
                            : "Daily filing checks are off. Enable them in Financials or use Refresh research."}{" "}
                          Annual figures cannot satisfy quarterly conditions.
                        </p>
                      )}
                    </details>
                  </section>
                </>
              )}
              <div className="research-decision">
                <div>
                  <strong>Where does this leave your research?</strong>
                  <small>
                    {data.research_action?.question === question
                      ? `Saved: ${{ investigate: "investigate further", unresolved: "unresolved", reject: "idea rejected" }[data.research_action.action]}`
                      : "You can leave it open. Monitoring is optional."}
                  </small>
                </div>
                <div>
                  <button
                    onClick={() =>
                      act(
                        () =>
                          api.research({
                            question,
                            action: "investigate",
                            instrument_id: instrumentId,
                          }),
                        "Research decision saved.",
                      )
                    }
                  >
                    Investigate
                  </button>
                  <button
                    onClick={() =>
                      act(
                        () =>
                          api.research({
                            question,
                            action: "unresolved",
                            instrument_id: instrumentId,
                          }),
                        "Question left unresolved.",
                      )
                    }
                  >
                    Unresolved
                  </button>
                  <button
                    onClick={() =>
                      act(
                        () =>
                          api.research({
                            question,
                            action: "reject",
                            instrument_id: instrumentId,
                          }),
                        "Idea rejected. You can revisit the research later.",
                      )
                    }
                  >
                    Reject idea
                  </button>
                </div>
              </div>
            </div>
          )}
        </Modal>
        <Modal
          open={updatesOpen && !companyLoading}
          onClose={() => setUpdatesOpen(false)}
          title="Research updates"
          className="research-updates-dialog"
        >
          <div className="research-updates-content">
            <p className="fine">
              {data.demo.label} · {date(data.demo.as_of)}
            </p>
            <div className="research-updates-actions">
              <button
                disabled={!!loadingRun?.active}
                onClick={() => startLoading()}
              >
                {loadingRun?.active ? "Updating research…" : "Refresh research"}
              </button>
              {layout.progressHidden && (
                <ResearchProgressToggle
                  run={loadingRun}
                  error={loadingError}
                  onExpand={toggleProgress}
                />
              )}
            </div>
            <ResearchLoading
              run={loadingRun}
              error={loadingError}
              onCollapse={toggleProgress}
              hidden={!!layout.progressHidden}
            />
            {modelAvailability(modelStatus).blocked && (
              <div className="research-ai-status">
                <p className="fine">{modelAvailability(modelStatus).message}</p>
                {modelAvailability(modelStatus).detail && (
                  <details>
                    <summary>AI request details</summary>
                    <p className="fine">
                      {modelAvailability(modelStatus).detail}
                    </p>
                  </details>
                )}
              </div>
            )}
          </div>
        </Modal>
        <Modal
          open={sourcesOpen && !companyLoading}
          onClose={() => setSourcesOpen(false)}
          title="Data & sources"
          className="evidence-dialog"
        >
          <p className="fine saved-report-context">
            {data.demo.label} · {date(data.demo.as_of)}
          </p>
          {data.market?.status?.quote_error && (
            <p className="fine" role="status">
              Finnhub quote check unavailable. {data.market.status.quote_error}{" "}
              Showing saved prices with their original source and timestamp.
            </p>
          )}
          {data.market?.status?.lease_until &&
            new Date(data.market.status.lease_until) < new Date() && (
              <p className="fine" role="status">
                The previous price check was interrupted. Displayed data may be
                older.
              </p>
            )}
          <p>
            Check what was collected, when it was checked and where information
            is missing. News and discussion stay in their own reading view.
          </p>
          {!isRecorded && (
            <SourceConnections data={data} loadingRun={loadingRun} />
          )}

          <div className="sources-list">
            {/* Problems stay individually visible; healthy checks are grouped
                so a gap is never buried in a long list of identical rows. */}
            {data.source_checks
              .filter((c) => c.state !== "fresh")
              .map((c) => (
                <article key={c.source_id}>
                  <div className="row">
                    <h3>{c.name}</h3>
                    <span className="status not_met">
                      {c.state === "denied"
                        ? "Access denied"
                        : c.state === "unknown"
                          ? "Not checked"
                          : "Unavailable"}
                    </span>
                  </div>
                  <p>
                    {c.state === "unknown"
                      ? "This source has not been checked yet. Refresh when the connection is configured."
                      : "The supplier could not be checked. This is a coverage gap, not confirmation that nothing changed."}
                  </p>
                </article>
              ))}
            {data.source_checks.some((c) => c.state === "fresh") && (
              <details className="source-checks-ok">
                <summary>
                  <span className="status met">
                    {isRecorded ? "Recorded check complete" : "Check complete"}
                  </span>
                  {data.source_checks.filter((c) => c.state === "fresh").length}{" "}
                  sources checked
                </summary>
                <p className="fine">
                  A successful check can produce no new article.
                </p>
                <ul>
                  {data.source_checks
                    .filter((c) => c.state === "fresh")
                    .map((c) => (
                      <li key={c.source_id}>
                        <span>{c.name}</span>
                        <small>through {date(c.covered_through)}</small>
                      </li>
                    ))}
                </ul>
              </details>
            )}
            <h3>Source library</h3>
            {data.documents.map((d) => (
              <button
                className="source-link"
                key={d.id}
                onClick={() => setSource(d)}
              >
                <span>
                  {d.title}
                  <small>
                    {d.source} · {date(d.published_at)}
                  </small>
                </span>
                <Icon name="source" />
              </button>
            ))}
          </div>
        </Modal>
      </div>
      <Modal
        open={!companyLoading && !!source}
        title="Source evidence"
        onClose={() => setSource(null)}
      >
        {source && (
          <div className="source-modal">
            <span className="demo-tag">
              {source.kind === "recorded"
                ? "AUTHORED FICTIONAL SOURCE"
                : source.kind === "news"
                  ? "NEWS · PROVIDER SNIPPET"
                  : source.kind === "social"
                    ? "SOCIAL · PUBLIC DISCUSSION"
                    : "CALCULATED FROM SEC FACTS"}
            </span>
            <h3>{source.title}</h3>
            <p className="muted">
              {source.source} ·{" "}
              {source.timestamp_basis === "feed_updated"
                ? "feed updated"
                : "published"}{" "}
              {date(source.published_at)}
              <br />
              First available here {date(source.available_at)}
            </p>
            {source.timestamp_basis === "feed_updated" && (
              <p className="fine">
                The feed supplies an update time. Original publication time and
                reply-to context are unavailable.
              </p>
            )}
            {source.kind !== "sec-calculation" ? (
              <>
                <blockquote>
                  {source.body || "Only a headline was supplied."}
                </blockquote>
                {["news", "social"].includes(source.kind) && (
                  <a
                    className="source-link"
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {source.kind === "social"
                      ? "Read original post ↗"
                      : "Read original article ↗"}
                  </a>
                )}
                {source.kind === "social" &&
                  /^https:\/\/(?:news\.ycombinator\.com\/item\?id=\d+|(?:www\.)?reddit\.com\/r\/\w+\/comments\/\w+\/[^/]+\/\w+\/?)$/.test(
                    source.url || "",
                  ) && (
                    <SocialConversation
                      key={source.id}
                      sourceId={source.id}
                      onRemoved={() => {
                        setSource(null);
                        refresh().catch((e) => setError(e.message));
                      }}
                    />
                  )}
              </>
            ) : (
              <FilingDetails
                filing={data.filing_calculations.find(
                  (f) => f.document_version_id === source.id,
                )}
              />
            )}
            <p className="fine">
              {source.kind === "recorded"
                ? "This is the exact stored source version. Interpretations shown in the workspace are authored for the demo; quotation matching alone does not verify a conclusion."
                : source.kind === "news"
                  ? "This is the stored provider headline and snippet, not the full article. AI interpretation can omit context; read the original reporting."
                  : source.kind === "social"
                    ? "This is a selected public discussion text, not a verified event or a representative investor sample. Each sentiment reading identifies any saved parent context it used. Inspecting a parent here does not change an earlier label. Collection includes bounded posts and replies when accessible, not complete threads."
                    : "This is the stored calculation and its original filing inputs. It is not a verbatim filing excerpt. Later filings cannot rewrite this version."}
            </p>
          </div>
        )}
      </Modal>
      <CompanyDialog
        open={addingCompany}
        onClose={() => setAddingCompany(false)}
        visible={visibleCompanies}
        hidden={hiddenCatalogue}
        onRemove={removeCompany}
        onRestore={(id) => {
          onRestoreCompany(id);
          setRemovedCompany(null);
        }}
        onAdded={(id) => {
          if (activeScope.current !== scope) return;
          onRestoreCompany(id);
          setAddingCompany(false);
          onChoose(id);
        }}
      />
      <Modal
        open={!companyLoading && !!editor}
        className="idea-dialog"
        title={
          proposalIds.length
            ? "Review selected suggestions"
            : current
              ? "Edit your idea"
              : "Save your reasoning"
        }
        onClose={() => !busy && setEditor(null)}
      >
        {editor && (
          <form
            className="idea-form"
            onChange={(e) => {
              if (e.target.type !== "checkbox") setApproved(false);
            }}
            onSubmit={(e) => {
              e.preventDefault();
              save("draft");
            }}
          >
            {proposalIds.length > 0 && (
              <div className="warning">
                Review the complete resulting idea below. Fill every missing
                threshold and date, and edit any wording before saving. Nothing
                has changed yet.{" "}
                {proposalStale &&
                  "The idea or evidence changed while reviewing. Close this draft and request fresh suggestions; it cannot be silently applied to the new revision."}
              </div>
            )}
            <section className="idea-writing">
              <p className="idea-intro">
                Start with your question and your point of view. Add monitoring
                rules when you’re ready.
              </p>
              <label className="field">
                Research question
                <input
                  value={editor.question}
                  maxLength={200}
                  required
                  onChange={(e) => {
                    setApproved(false);
                    setEditor({ ...editor, question: e.target.value });
                  }}
                />
              </label>
              <div className="field">
                <label htmlFor="idea-reasoning">My reasoning</label>
                <textarea
                  id="idea-reasoning"
                  value={editor.reasoning}
                  maxLength={3000}
                  rows={3}
                  placeholder="I think… because… I’m unsure about… I would reconsider if…"
                  aria-describedby="reasoning-starter"
                  onChange={(e) => {
                    setApproved(false);
                    setEditor({ ...editor, reasoning: e.target.value });
                  }}
                />
                <p id="reasoning-starter" className="reasoning-prompt">
                  Use your own words. One reason and one uncertainty are enough
                  to start. You can save a draft without a monitoring rule,
                  including why you decided not to invest.
                </p>
              </div>
            </section>
            <details
              className="idea-monitoring"
              open={
                editor.conditions.length > 0 || editor.events.length > 0
                  ? true
                  : undefined
              }
            >
              <summary>
                <span>
                  <strong>Add monitoring rules</strong>
                  <small>
                    Optional · Track numbers or developments that would change
                    your mind
                  </small>
                </span>
                <Icon name="plus" width="18" />
              </summary>
              <div className="idea-monitoring-body">
                <h3>Financial conditions</h3>
                <p className="fine">
                  Choose what must hold and what would signal a risk. You set
                  the thresholds.
                </p>
                {editor.conditions.map((c, i) => (
                  <div className="condition-editor" key={c.id}>
                    <label className="condition-role">
                      Purpose of condition {i + 1}
                      <Select
                        aria-label={`Purpose of condition ${i + 1}`}
                        value={c.role || "required"}
                        onChange={(e) => {
                          setApproved(false);
                          setEditor({
                            ...editor,
                            conditions: editor.conditions.map((r, j) =>
                              j === i ? { ...r, role: e.target.value } : r,
                            ),
                          });
                        }}
                      >
                        <option value="required">
                          Requirement — must hold
                        </option>
                        <option value="risk">Risk — flag when reached</option>
                      </Select>
                      <small>
                        {c.role === "risk"
                          ? "Reaching this threshold flags a risk to review. Not reaching it does not mean the investment is safe. Changing purpose keeps your comparison and number unchanged."
                          : "The figure must satisfy your comparison. Otherwise, this requirement needs review."}
                      </small>
                    </label>
                    <div className="condition-field">
                      <label htmlFor={`metric-${c.id}`}>Metric</label>
                      <Select
                        id={`metric-${c.id}`}
                        value={c.metric}
                        onChange={(e) =>
                          setEditor({
                            ...editor,
                            conditions: editor.conditions.map((r, j) =>
                              j === i ? { ...r, metric: e.target.value } : r,
                            ),
                          })
                        }
                      >
                        {Object.entries(metrics).map(([k, v]) => (
                          <option key={k} value={k}>
                            {v}
                          </option>
                        ))}
                      </Select>
                    </div>
                    <div className="condition-field">
                      <label htmlFor={`operator-${c.id}`}>Condition</label>
                      <Select
                        id={`operator-${c.id}`}
                        value={c.operator}
                        onChange={(e) =>
                          setEditor({
                            ...editor,
                            conditions: editor.conditions.map((r, j) =>
                              j === i ? { ...r, operator: e.target.value } : r,
                            ),
                          })
                        }
                      >
                        <option value=">=">At least</option>
                        <option value="<=">At most</option>
                      </Select>
                    </div>
                    <div className="condition-field">
                      <label htmlFor={`value-${c.id}`}>Percent</label>
                      <input
                        id={`value-${c.id}`}
                        type="number"
                        step="any"
                        min="-100"
                        max="1000"
                        placeholder="Your threshold"
                        value={c.value}
                        onChange={(e) =>
                          setEditor({
                            ...editor,
                            conditions: editor.conditions.map((r, j) =>
                              j === i ? { ...r, value: e.target.value } : r,
                            ),
                          })
                        }
                      />
                    </div>
                    <button
                      type="button"
                      className="icon-button"
                      aria-label={`Remove condition ${i + 1}`}
                      onClick={() => {
                        setApproved(false);
                        setEditor({
                          ...editor,
                          conditions: editor.conditions.filter(
                            (_, j) => j !== i,
                          ),
                        });
                      }}
                    >
                      ×
                    </button>
                    <small className="threshold-reference">
                      {latest(c.metric).value != null &&
                      latest(c.metric).period_type ===
                        (c.period_type || "quarter")
                        ? `Latest reported: ${displayNumber(latest(c.metric).value)}% · ${latest(c.metric).period}. This is context, not a suggested threshold.`
                        : "No comparable figure is available for this reporting scope."}
                    </small>
                    <label className="condition-period">
                      Reporting period
                      <Select
                        aria-label={`Reporting period ${i + 1}`}
                        value={c.period_type || "quarter"}
                        onChange={(e) =>
                          setEditor({
                            ...editor,
                            conditions: editor.conditions.map((r, j) =>
                              j === i
                                ? { ...r, period_type: e.target.value }
                                : r,
                            ),
                          })
                        }
                      >
                        <option value="quarter">Quarterly</option>
                        <option value="annual">Annual</option>
                      </Select>
                    </label>
                    <ReportExpectationEditor
                      condition={c}
                      index={i + 1}
                      onChange={(field, value) => {
                        setApproved(false);
                        setEditor({
                          ...editor,
                          conditions: editor.conditions.map((r, j) =>
                            j === i
                              ? {
                                  ...r,
                                  ...(field === "clear"
                                    ? {
                                        expected_period_end: "",
                                        expected_report_by: "",
                                      }
                                    : { [field]: value }),
                                }
                              : r,
                          ),
                        });
                      }}
                    />
                    <div className="reporting-age-editor">
                      <label htmlFor={`age-${c.id}`}>
                        Maximum age of reporting period
                      </label>
                      <input
                        id={`age-${c.id}`}
                        aria-label={`Days since period end ${i + 1}`}
                        type="number"
                        min="1"
                        max="3650"
                        step="1"
                        placeholder="No age limit"
                        value={c.max_report_age_days ?? ""}
                        onChange={(e) => {
                          setApproved(false);
                          setEditor({
                            ...editor,
                            conditions: editor.conditions.map((r, j) =>
                              j === i
                                ? { ...r, max_report_age_days: e.target.value }
                                : r,
                            ),
                          });
                        }}
                      />
                      <small>
                        Optional days since the period ended. Older figures
                        become unknown; their values and sources stay available.
                        Leave blank for no age limit.
                      </small>
                      <ReportingAge
                        condition={c}
                        fundamentals={data.fundamentals}
                        cutoff={data.demo.as_of}
                        recorded={isRecorded}
                      />
                    </div>
                  </div>
                ))}
                {editor.conditions.length < 4 && (
                  <button
                    type="button"
                    className="text-button"
                    onClick={() => {
                      setApproved(false);
                      setEditor({
                        ...editor,
                        conditions: [
                          ...editor.conditions,
                          newCondition(data.demo.period_type),
                        ],
                      });
                    }}
                  >
                    <Icon name="plus" width="15" /> Add condition
                  </button>
                )}
                <EventEditor
                  events={editor.events}
                  onChange={(events) => {
                    setApproved(false);
                    setEditor({ ...editor, events });
                  }}
                />
                <details className="explanation">
                  <summary>How monitoring works</summary>
                  <p>
                    For a requirement “revenue growth at least 15%,” 18% meets
                    it and 12% does not. For a risk “growth at most 15%,” 12%
                    and exactly 15% flag that risk; 18% does not. Any unmet
                    requirement or flagged risk needs review. Otherwise,
                    missing, expired or conflicting figures leave the assessment
                    incomplete. News cannot satisfy a numeric condition.
                  </p>
                  <p>
                    Each assessment checks the selected reporting scope. An
                    annual filing cannot satisfy a quarterly condition. A source
                    outage leaves a visible coverage gap. These thresholds are
                    your research criteria, not forecasts.
                  </p>
                </details>
                {(editor.conditions.length > 0 || editor.events.length > 0) && (
                  <label className="approval">
                    <Checkbox
                      checked={approved}
                      onChange={(e) => setApproved(e.target.checked)}
                    />{" "}
                    I approve these conditions for this revision.
                  </label>
                )}
              </div>
            </details>
            {formError && (
              <div className="error" role="alert">
                {formError}
              </div>
            )}
            {conflict && (
              <section
                className="conflict-comparison"
                aria-label="Resolve conflicting edits"
              >
                <h3>This idea changed in another tab</h3>
                <p>
                  Your draft is preserved. Compare both versions before choosing
                  which to keep.
                </p>
                <div className="comparison-columns">
                  <div>
                    <span className="section-label">
                      LATEST SAVED · REVISION {conflict.revision}
                    </span>
                    <h4>{conflict.question}</h4>
                    <p>{conflict.reasoning || "No reasoning recorded"}</p>
                    <EventDefinitions events={conflict.events} />
                    {conflict.conditions.map((c) => (
                      <p key={c.condition_id}>
                        {roleLabel(c)} · {metrics[c.metric]} {c.operator}{" "}
                        {c.threshold}% ·{" "}
                        {c.period_type === "annual" ? "Annual" : "Quarterly"} ·{" "}
                        {ageLabel(c)}
                      </p>
                    ))}
                  </div>
                  <div>
                    <span className="section-label">YOUR UNSAVED DRAFT</span>
                    <h4>{editor.question}</h4>
                    <p>{editor.reasoning || "No reasoning recorded"}</p>
                    <EventDefinitions events={editor.events} />
                    {editor.conditions.map((c) => (
                      <p key={c.id}>
                        {roleLabel(c)} · {metrics[c.metric]} {c.operator}{" "}
                        {c.value}% ·{" "}
                        {c.period_type === "annual" ? "Annual" : "Quarterly"} ·{" "}
                        {ageLabel(c)}
                      </p>
                    ))}
                  </div>
                </div>
                <div className="comparison-actions">
                  <button
                    type="button"
                    onClick={() => {
                      setEditor(formFor(conflict, question));
                      setConflict(null);
                      setApproved(false);
                      setFormError(
                        "Loaded the saved version. Review it before saving.",
                      );
                    }}
                  >
                    Use saved version
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setEditor({ ...editor, revision: conflict.revision });
                      setConflict(null);
                      setApproved(false);
                      setFormError(
                        "Your draft will become a new revision. Monitoring requires approval again.",
                      );
                    }}
                  >
                    Keep my draft as a new revision
                  </button>
                </div>
              </section>
            )}
            <footer className="form-actions">
              <button
                type="submit"
                className={approved ? "secondary" : "primary"}
                disabled={
                  busy || !!conflict || proposalStale || !editor.question.trim()
                }
              >
                {proposalIds.length ? "Use suggestions in draft" : "Save draft"}
              </button>
              {(editor.conditions.length > 0 || editor.events.length > 0) && (
                <button
                  type="button"
                  className={approved ? "primary" : "secondary"}
                  disabled={
                    busy ||
                    !!conflict ||
                    proposalStale ||
                    !approved ||
                    (!editor.conditions.length && !editor.events.length) ||
                    editor.conditions.some(
                      (c) =>
                        String(c.value ?? "").trim() === "" ||
                        !Number.isFinite(Number(c.value)),
                    ) ||
                    !editor.reasoning.trim() ||
                    !editor.question.trim()
                  }
                  onClick={() => save("monitoring")}
                >
                  Approve monitoring <Icon name="arrow" />
                </button>
              )}
            </footer>
            {current && (
              <button
                type="button"
                className="archive-button"
                disabled={busy || !!conflict}
                onClick={() => save("archived")}
              >
                Archive idea and stop monitoring
              </button>
            )}
          </form>
        )}
      </Modal>
    </div>
  );
}
