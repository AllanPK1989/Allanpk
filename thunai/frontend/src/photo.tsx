// Photo-based diagnosis on the phone: shrink before upload, show what Thunai read (SPEC 12.6).
import type { PhotoRead } from "./api";
import { Icon } from "./components";
import { useApp } from "./state";

const MAX_EDGE = 2576; // the model's largest useful size; bigger photos only cost more data
const SMALL_ENOUGH = 2_000_000; // bytes

/** A smaller JPEG for plant Wi-Fi. Drawing on a canvas also drops the camera's location data. */
export async function shrinkPhoto(file: File): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
    if (Math.max(bitmap.width, bitmap.height) <= MAX_EDGE && file.size <= SMALL_ENOUGH) {
      bitmap.close();
      return file; // already small; the server re-encodes before anything is sent to the AI
    }
    const scale = Math.min(1, MAX_EDGE / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext("2d")?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.88));
    return blob && blob.size < file.size ? blob : file;
  } catch {
    return file; // old browsers: send the original; the server re-encodes it anyway
  }
}

export function PhotoCard({ read }: { read: PhotoRead }) {
  const { t, lang } = useApp();
  const o = read.observation;
  const pick = (en?: string, ta?: string) => (lang === "ta" ? ta || en : en || ta) || "";
  if (!read.enabled || o.disabled) {
    return <p className="note note-info">{t("photo_off")}</p>;
  }
  if (!o.usable) {
    return (
      <div className="note note-warn photo-card">
        <strong>{t("photo_unusable")}</strong>
        <p>{pick(o.unusable_reason_en, o.unusable_reason_ta) || o.error}</p>
      </div>
    );
  }
  return (
    <div className="photo-card" role="status">
      <div className="photo-card-head">
        <Icon name="camera" size={20} /> <strong>{t("photo_sees")}</strong>
      </div>
      <p>{pick(o.shows_en, o.shows_ta)}</p>
      {!!o.readings?.length && (
        <>
          <p className="muted small">{t("photo_readings")}</p>
          <ul className="readings">
            {o.readings.map((r, i) => (
              <li key={i}>
                {r.label}: {r.legible ? <strong>{`${r.value} ${r.unit}`.trim()}</strong> : <em>{t("could_not_read")}</em>}
              </li>
            ))}
          </ul>
        </>
      )}
      {o.screen_text && (
        <p>
          <span className="muted">{t("photo_screen")}: </span>
          <span className="mono">{o.screen_text}</span>
        </p>
      )}
      {pick(o.damage_en, o.damage_ta) && (
        <p>
          <span className="muted">{t("photo_damage")}: </span>
          {pick(o.damage_en, o.damage_ta)}
        </p>
      )}
    </div>
  );
}
