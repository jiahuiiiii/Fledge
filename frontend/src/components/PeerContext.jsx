import { useEffect, useState } from "react";
import { api } from "../api/client";
import { peerGrowthContext } from "../lib/peerGrowthContext";

export default function PeerContext({ instrumentId, visible, onCompare }) {
  const [data, setData] = useState(null);
  useEffect(() => {
    if (!visible) return;
    let active = true;
    api
      .sectorPosition(instrumentId)
      .then((value) => {
        if (active) setData(value);
      })
      .catch(() => {
        if (active) setData(null);
      });
    return () => {
      active = false;
    };
  }, [instrumentId, visible]);
  return (
    <p className="financial-peer-context">
      {peerGrowthContext(data)}{" "}
      <button className="source-link" onClick={onCompare}>
        Compare <span aria-hidden="true">→</span>
      </button>
    </p>
  );
}
