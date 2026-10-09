import { useState } from "react";
import broadcomLogo from "../assets/company-logos/AVGO.png";
import nvidiaLogo from "../assets/company-logos/NVDA.png";
import fabrinetLogo from "../assets/company-logos/FN.png";
import marvellLogo from "../assets/company-logos/MRVL.png";
import "./CompanyIdentity.css";

// Verified public FMP images are bundled for the current owner workspace.
// Other SEC-registered symbols use the same public image route when displayed.
const bundledLogos = {
  AVGO: broadcomLogo,
  NVDA: nvidiaLogo,
  FN: fabrinetLogo,
  MRVL: marvellLogo,
};
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
  const seed = [...(company?.symbol || company?.name || "?")].reduce(
    (hash, letter) => (hash * 31 + letter.charCodeAt(0)) >>> 0,
    0,
  );
  const hue = seed % 360;
  const [loaded, setLoaded] = useState(null);
  const [failed, setFailed] = useState(null);
  const hasLogo = !!src && loaded === src && failed !== src;
  return (
    <span
      className={`company-avatar${small ? " small" : ""}${hasLogo ? " has-logo" : ""}${src === marvellLogo ? " logo-on-dark" : ""}`}
      style={
        !hasLogo
          ? { background: `hsl(${hue} 24% 22%)`, color: `hsl(${hue} 60% 80%)` }
          : undefined
      }
      aria-hidden="true"
    >
      {(company?.symbol || company?.name || "?").slice(0, 2).toUpperCase()}
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
