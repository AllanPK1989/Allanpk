// Printable QR stickers (A4, 3 per row). Each code opens the machine page.
import { useEffect, useState } from "react";
import { api } from "../api";
import type { Machine } from "../api";
import { Header, Icon, Spinner } from "../components";

export default function QrSheet() {
  const [machines, setMachines] = useState<Machine[] | null>(null);
  const [zone, setZone] = useState("");
  const [svgs, setSvgs] = useState<Record<string, string>>({});

  useEffect(() => {
    api.get<Machine[]>("/api/machines?limit=1000").then(setMachines).catch(() => setMachines([]));
  }, []);

  const shown = (machines ?? []).filter((m) => !zone || m.zone === zone);

  useEffect(() => {
    for (const m of shown) {
      if (svgs[m.machine_no]) continue;
      api
        .blob(`/api/machines/${encodeURIComponent(m.machine_no)}/qr.svg`)
        .then((b) => b.text())
        .then((svg) => setSvgs((s) => ({ ...s, [m.machine_no]: svg })))
        .catch(() => {});
    }
  }, [machines, zone]);

  const zones = [...new Set((machines ?? []).map((m) => m.zone).filter(Boolean))].sort();

  return (
    <>
      <div className="no-print">
        <Header title="QR stickers" />
        <div className="page">
          <div className="row-wrap">
            <select className="input" value={zone} onChange={(e) => setZone(e.target.value)}>
              <option value="">All zones</option>
              {zones.map((z) => (
                <option key={z}>{z}</option>
              ))}
            </select>
            <button className="btn btn-primary" onClick={() => window.print()}>
              <Icon name="download" /> Print
            </button>
          </div>
          {!machines && <Spinner />}
        </div>
      </div>
      <div className="qr-sheet">
        {shown.map((m) => (
          <div className="qr-sticker" key={m.id}>
            <div className="qr-img" dangerouslySetInnerHTML={{ __html: svgs[m.machine_no] ?? "" }} />
            <div className="qr-no">{m.machine_no}</div>
            <div className="qr-name">{m.name}</div>
            <div className="qr-foot">Scan for Thunai · {m.zone}</div>
          </div>
        ))}
      </div>
    </>
  );
}
