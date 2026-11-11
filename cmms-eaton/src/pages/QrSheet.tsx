import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import QRCode from "qrcode";
import { Icon } from "../components/icons";
import { Button, PageHeader } from "../components/ui";
import { useStore } from "../store/StoreProvider";

export function QrSheet() {
  const { snapshot, linesById } = useStore();
  const [lineId, setLineId] = useState("");
  const [codes, setCodes] = useState<Record<string, string>>({});
  const assets = useMemo(
    () => snapshot.assets.filter((a) => a.active && a.parentId === null && (!lineId || a.lineId === lineId)).sort((a, b) => a.assetNo.localeCompare(b.assetNo)),
    [snapshot.assets, lineId],
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const out: Record<string, string> = {};
      for (const a of assets) {
        out[a.id] = await QRCode.toDataURL(`${location.origin}${location.pathname}#/assets/${a.id}`, { margin: 1, width: 280 });
      }
      if (!cancelled) setCodes(out);
    })();
    return () => {
      cancelled = true;
    };
  }, [assets]);

  return (
    <div>
      <div className="no-print">
        <Link to="/assets" className="flex small">
          <Icon name="arrow-left" size={14} /> Assets
        </Link>
        <PageHeader
          title="QR sticker sheet"
          subtitle="Print, cut and stick on each machine. Scanning opens the asset page to report a breakdown or see history."
          actions={
            <>
              <select value={lineId} onChange={(e) => setLineId(e.target.value)} aria-label="Line">
                <option value="">All lines</option>
                {snapshot.lines.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.code} · {l.name}
                  </option>
                ))}
              </select>
              <Button variant="primary" icon="printer" onClick={() => window.print()}>
                Print
              </Button>
            </>
          }
        />
      </div>
      <div className="qr-grid">
        {assets.map((a) => (
          <div className="qr-card" key={a.id}>
            {codes[a.id] ? <img src={codes[a.id]} alt={`QR ${a.assetNo}`} /> : <div style={{ height: 140 }} />}
            <div className="no">{a.assetNo}</div>
            <div className="small">{a.name}</div>
            <div className="small" style={{ color: "#555" }}>
              {a.lineId ? linesById.get(a.lineId)?.code : ""} {a.location}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
