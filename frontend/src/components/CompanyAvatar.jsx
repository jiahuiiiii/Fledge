import { useState } from "react";
import broadcomLogo from "../assets/company-logos/AVGO.png";
import nvidiaLogo from "../assets/company-logos/NVDA.png";
import fabrinetLogo from "../assets/company-logos/FN.png";

// Verified public FMP images are bundled for the current owner workspace.
// Other SEC-registered symbols use the same public image route when displayed.
const bundledLogos = { AVGO: broadcomLogo, NVDA: nvidiaLogo, FN: fabrinetLogo };
function logoFor(company) {
  const symbol = company?.symbol;
  if (company?.mode !== "sec" || !/^[A-Z]{1,5}$/.test(symbol || ""))
    return null;
  return (
    bundledLogos[symbol] ||
    `https://financialmodelingprep.com/image-stock/${symbol}.png`
  );
}

export default function CompanyAvatar({ company, small = false }) {
  const src = logoFor(company);
  const [loaded, setLoaded] = useState(null);
  const [failed, setFailed] = useState(null);
  const hasLogo = !!src && loaded === src && failed !== src;
  return (
    <span
      className={`company-avatar${small ? " small" : ""}${hasLogo ? " has-logo" : ""}`}
      aria-hidden="true"
    >
      {company?.name?.[0] || company?.symbol?.[0] || "?"}
      {src && failed !== src && (
        <img
          src={src}
          alt=""
          loading={small ? "lazy" : "eager"}
          decoding="async"
          referrerPolicy="no-referrer"
          onLoad={() => setLoaded(src)}
          onError={() => setFailed(src)}
        />
      )}
    </span>
  );
}
