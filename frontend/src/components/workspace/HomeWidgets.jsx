import { lazy } from "react";
import PersonalHome from "../PersonalHome";
import PortfolioRead from "../PortfolioRead";
import { useWorkspace } from "./WorkspaceContext";

// The home page's blocks as widgets: each takes what it needs from context.
const CompanyOverview = lazy(() => import("../CompanyOverview"));

export function HomeWelcome() {
  const { onAddCompany, onOpenCompany, practice } = useWorkspace();
  return (
    <PersonalHome
      onAddCompany={onAddCompany}
      onOpenCompany={onOpenCompany}
      practice={practice}
    />
  );
}

export function HomePortfolio() {
  const { onOpenCompany } = useWorkspace();
  return <PortfolioRead onOpenCompany={onOpenCompany} />;
}

export function HomeCompanies() {
  const { catalogue, onOpen } = useWorkspace();
  return <CompanyOverview catalogue={catalogue} onOpen={onOpen} />;
}
