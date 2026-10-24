import jsQR from "jsqr";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Header, Page } from "../components";
import { useApp } from "../state";
import { machineTarget } from "./Machines";

/** Reads a machine QR sticker. Stickers hold https://<server>/m/<machine number>. */
export function machineFromQr(text: string): string | null {
  const m = text.match(/\/m\/([^/?#]+)/);
  if (m) return decodeURIComponent(m[1]);
  return /^[A-Za-z0-9._-]{2,40}$/.test(text.trim()) ? text.trim() : null;
}

export default function Scan() {
  const { t } = useApp();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const video = useRef<HTMLVideoElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let stream: MediaStream | null = null;
    let frame = 0;
    let stopped = false;
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d", { willReadFrequently: true });

    const tick = () => {
      if (stopped) return;
      const v = video.current;
      if (v && v.readyState === v.HAVE_ENOUGH_DATA && ctx) {
        canvas.width = v.videoWidth;
        canvas.height = v.videoHeight;
        ctx.drawImage(v, 0, 0);
        const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const code = jsQR(img.data, img.width, img.height, { inversionAttempts: "dontInvert" });
        const machine = code ? machineFromQr(code.data) : null;
        if (machine) {
          stopped = true;
          navigator.vibrate?.(80);
          navigate(machineTarget(params.get("next"), machine), { replace: true });
          return;
        }
      }
      frame = requestAnimationFrame(tick);
    };

    navigator.mediaDevices
      ?.getUserMedia({ video: { facingMode: "environment" } })
      .then((s) => {
        stream = s;
        if (video.current) {
          video.current.srcObject = s;
          void video.current.play();
          frame = requestAnimationFrame(tick);
        }
      })
      .catch(() => setFailed(true));
    if (!navigator.mediaDevices) setFailed(true);
    return () => {
      stopped = true;
      cancelAnimationFrame(frame);
      stream?.getTracks().forEach((tr) => tr.stop());
    };
  }, [navigate, params]);

  return (
    <>
      <Header title={t("scan_qr")} />
      <Page>
        {failed ? (
          <>
            <p className="note note-warn">{t("camera_denied")}</p>
            <button className="btn btn-primary btn-block" onClick={() => navigate(`/machines?next=${params.get("next") ?? "view"}`)}>
              {t("search_machine")}
            </button>
          </>
        ) : (
          <>
            <div className="scanner">
              <video ref={video} playsInline muted />
              <div className="scanner-frame" aria-hidden="true" />
            </div>
            <p className="center muted">{t("scan_hint")}</p>
          </>
        )}
      </Page>
    </>
  );
}
