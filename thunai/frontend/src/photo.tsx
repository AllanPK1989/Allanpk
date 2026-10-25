// Photos on the phone: shrink before upload. In the PWA they are attachments to the log; Thunai in
// Teams reads photos with Copilot (SPEC 13.1).

const MAX_EDGE = 2576; // sharp enough to read a gauge; bigger photos only cost more data
const SMALL_ENOUGH = 2_000_000; // bytes

/** A smaller JPEG for plant Wi-Fi. Drawing on a canvas also drops the camera's location data. */
export async function shrinkPhoto(file: File): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
    if (Math.max(bitmap.width, bitmap.height) <= MAX_EDGE && file.size <= SMALL_ENOUGH) {
      bitmap.close();
      return file; // already small
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
    return file; // old browsers: send the original
  }
}
